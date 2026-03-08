#!/usr/bin/env python3
# flake8: noqa
"""
Schedule Runner for Newsletter Generator
Handles RRULE-based periodic newsletter generation
"""

import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, cast

import redis
from dateutil import tz  # type: ignore[import-untyped]
from dateutil.rrule import rrulestr  # type: ignore[import-untyped]
from rq import Queue

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import task functions
from tasks import generate_newsletter_task

try:
    from db_state import (
        build_schedule_idempotency_key,
        derive_job_id,
        ensure_database_schema,
        ensure_history_row,
        is_feature_enabled,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        build_schedule_idempotency_key,
        derive_job_id,
        ensure_database_schema,
        ensure_history_row,
        is_feature_enabled,
    )

# Import time utilities
try:
    from web.time_utils import to_iso_utc  # PyInstaller
except ImportError:
    from time_utils import to_iso_utc  # Development

try:
    from ops_logging import log_debug, log_error, log_exception, log_info, log_warning
except ImportError:
    from web.ops_logging import (  # pragma: no cover
        log_debug,
        log_error,
        log_exception,
        log_info,
        log_warning,
    )

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Keep a stable datetime parser even when tests patch module-level `datetime`.
REAL_DATETIME = datetime


class ScheduleRunner:
    """RRULE 기반 스케줄 실행기"""

    def __init__(self, db_path: str = "storage.db", redis_url: str | None = None):
        self.db_path = db_path
        ensure_database_schema(self.db_path)
        self.redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )

        # Redis 연결 설정
        try:
            self.redis_conn = redis.from_url(self.redis_url)
            self.queue = Queue("default", connection=self.redis_conn)
        except Exception as e:
            log_exception(logger, "schedule.redis.connection_failed", e)
            self.redis_conn = None
            self.queue = None

    def _parse_iso_datetime(self, iso_string: str) -> datetime:
        """Parse ISO datetime string, handling Z suffix properly"""
        if iso_string.endswith("Z"):
            # Remove Z and add UTC timezone
            return REAL_DATETIME.fromisoformat(iso_string[:-1]).replace(
                tzinfo=timezone.utc
            )
        else:
            return REAL_DATETIME.fromisoformat(iso_string)

    def get_pending_schedules(self) -> List[Dict]:
        """실행 대기 중인 스케줄 목록을 가져옵니다."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)
            log_debug(
                logger,
                "schedule.scan.started",
                db_path=self.db_path,
                db_exists=os.path.exists(self.db_path),
                now=now,
            )

            # Import time utilities and convert current time
            try:
                from web.time_utils import to_iso_utc  # PyInstaller
            except ImportError:
                from time_utils import to_iso_utc  # Development
            now_iso = to_iso_utc(now)

            # 만료된 테스트 스케줄 정리
            cursor.execute(
                "UPDATE schedules SET enabled = 0 WHERE is_test = 1 AND expires_at IS NOT NULL AND expires_at <= ?",
                (now_iso,),
            )
            expired_count = cursor.rowcount
            if expired_count > 0:
                log_info(
                    logger,
                    "schedule.expired_tests.disabled",
                    count=expired_count,
                )

            # 모든 활성 스케줄 조회
            cursor.execute(
                "SELECT id, params, rrule, next_run, created_at, is_test FROM schedules WHERE enabled = 1"
            )
            all_schedules = cursor.fetchall()
            log_debug(
                logger, "schedule.scan.loaded_active", active_count=len(all_schedules)
            )

            # 스케줄 실행 대기열과 만료된 스케줄 분리 처리
            ready_for_execution = []
            updated_count = 0

            # 정규 스케줄: 30분 윈도우, 테스트 스케줄: 10분 윈도우
            regular_window = timedelta(minutes=30)
            test_window = timedelta(minutes=10)

            for schedule in all_schedules:
                (
                    schedule_id,
                    params,
                    rrule_str,
                    next_run_str,
                    created_at,
                    is_test,
                ) = schedule

                try:
                    # 스케줄의 다음 실행 시간 파싱
                    next_run = self._parse_iso_datetime(next_run_str)
                    time_diff = now - next_run

                    # 실행 창 설정 (테스트 vs 정규)
                    execution_window = test_window if is_test else regular_window

                    log_debug(
                        logger,
                        "schedule.scan.evaluating",
                        schedule_id=schedule_id,
                        next_run=next_run_str,
                        time_diff_seconds=round(time_diff.total_seconds(), 1),
                        window_seconds=execution_window.total_seconds(),
                    )

                    # 실행 창 내에 있는 스케줄 (즉시 실행 대상)
                    if timedelta(0) <= time_diff <= execution_window:
                        log_debug(
                            logger,
                            "schedule.scan.ready",
                            schedule_id=schedule_id,
                            window_minutes=round(
                                execution_window.total_seconds() / 60, 1
                            ),
                        )
                        ready_for_execution.append(schedule)

                    # 실행 창을 넘어선 과거 스케줄 (다음 주기로 업데이트)
                    elif time_diff > execution_window:
                        log_info(
                            logger,
                            "schedule.scan.expired",
                            schedule_id=schedule_id,
                            missed_window_minutes=round(
                                time_diff.total_seconds() / 60, 1
                            ),
                        )

                        # 다음 실행 시간 계산
                        next_run_calculated = self.calculate_next_run(rrule_str, now)

                        if next_run_calculated:
                            cursor.execute(
                                "UPDATE schedules SET next_run = ? WHERE id = ?",
                                (to_iso_utc(next_run_calculated), schedule_id),
                            )
                            updated_count += 1
                            log_info(
                                logger,
                                "schedule.scan.expired_rescheduled",
                                schedule_id=schedule_id,
                                previous_next_run=next_run_str,
                                next_run=to_iso_utc(next_run_calculated),
                            )
                        else:
                            cursor.execute(
                                "UPDATE schedules SET enabled = 0 WHERE id = ?",
                                (schedule_id,),
                            )
                            log_info(
                                logger,
                                "schedule.scan.disabled_no_more_occurrences",
                                schedule_id=schedule_id,
                            )

                    # 미래 스케줄 (아직 실행 시간이 아님)
                    else:
                        log_debug(
                            logger,
                            "schedule.scan.future",
                            schedule_id=schedule_id,
                            run_in_minutes=round(
                                abs(time_diff.total_seconds()) / 60, 1
                            ),
                        )

                except Exception as parse_error:
                    log_exception(
                        logger,
                        "schedule.scan.parse_failed",
                        parse_error,
                        schedule_id=schedule_id,
                    )
                    continue

            if expired_count > 0 or updated_count > 0:
                conn.commit()
            if updated_count > 0:
                log_info(
                    logger,
                    "schedule.scan.expired_updates_committed",
                    updated_count=updated_count,
                )

            # 실행 준비 완료된 스케줄들을 반환 형식으로 변환
            log_debug(
                logger,
                "schedule.scan.ready_summary",
                ready_count=len(ready_for_execution),
            )

            # Ensure deterministic execution order (oldest next_run first).
            ready_for_execution.sort(
                key=lambda schedule_data: self._parse_iso_datetime(schedule_data[3])
            )

            schedules = []
            for schedule_data in ready_for_execution:
                (
                    schedule_id,
                    params,
                    rrule_str,
                    next_run_str,
                    created_at,
                    is_test,
                ) = schedule_data
                is_test_bool = bool(is_test)

                log_debug(
                    logger,
                    "schedule.queue.ready_entry",
                    schedule_id=schedule_id,
                    schedule_type="test" if is_test_bool else "regular",
                    next_run=next_run_str,
                )

                schedules.append(
                    {
                        "id": schedule_id,
                        "params": json.loads(params),
                        "rrule": rrule_str,
                        "next_run": self._parse_iso_datetime(next_run_str),
                        "created_at": self._parse_iso_datetime(created_at),
                        "is_test": is_test_bool,
                    }
                )

            conn.close()
            return schedules

        except Exception as e:
            log_exception(logger, "schedule.scan.failed", e, db_path=self.db_path)
            return []

    def calculate_next_run(
        self, rrule_str: str, after: datetime | None = None
    ) -> Optional[datetime]:
        """RRULE을 기반으로 다음 실행 시간을 계산합니다."""
        try:
            if after is None:
                after = REAL_DATETIME.now(timezone.utc)

            # after가 timezone-aware인 경우 naive로 변환
            if after.tzinfo is not None:
                after_naive = after.replace(tzinfo=None)
            else:
                after_naive = after

            # RRULE 파싱
            rrule = rrulestr(rrule_str, dtstart=after_naive)

            # 다음 실행 시간 찾기 (naive datetime 반환)
            next_occurrence_naive = rrule.after(after_naive)

            # UTC timezone을 추가하여 aware datetime으로 변환
            if next_occurrence_naive is not None:
                next_occurrence = cast(datetime, next_occurrence_naive).replace(
                    tzinfo=timezone.utc
                )
                return next_occurrence
            else:
                return None

        except Exception as e:
            log_exception(
                logger,
                "schedule.next_run.calculate_failed",
                e,
                rrule=rrule_str,
            )
            return None

    def update_schedule_next_run(self, schedule_id: str, next_run: datetime) -> bool:
        """스케줄의 다음 실행 시간을 업데이트합니다."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE schedules
                SET next_run = ?
                WHERE id = ?
            """,
                (to_iso_utc(next_run), schedule_id),
            )

            conn.commit()
            conn.close()

            log_info(
                logger,
                "schedule.next_run.updated",
                schedule_id=schedule_id,
                next_run=next_run,
            )
            return True

        except Exception as e:
            log_exception(
                logger, "schedule.next_run.update_failed", e, schedule_id=schedule_id
            )
            return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """스케줄을 비활성화합니다."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE schedules
                SET enabled = 0
                WHERE id = ?
            """,
                (schedule_id,),
            )

            conn.commit()
            conn.close()

            log_info(logger, "schedule.disabled", schedule_id=schedule_id)
            return True

        except Exception as e:
            log_exception(logger, "schedule.disable_failed", e, schedule_id=schedule_id)
            return False

    def execute_schedule(self, schedule: Dict) -> bool:
        """스케줄을 실행합니다."""
        try:
            schedule_id = schedule["id"]
            params = schedule["params"]
            rrule_str = schedule["rrule"]

            # 스케줄 실행 후 다음 실행 시간 계산 및 업데이트 (중복 실행 방지)
            try:
                now = datetime.now(timezone.utc)
                next_run = self.calculate_next_run(rrule_str, now)

                if next_run:
                    # 다음 실행 시간을 먼저 업데이트하여 중복 실행 방지
                    if self.update_schedule_next_run(schedule_id, next_run):
                        log_info(
                            logger,
                            "schedule.execute.preupdated_next_run",
                            schedule_id=schedule_id,
                            next_run=next_run,
                        )
                    else:
                        log_error(
                            logger,
                            "schedule.execute.preupdate_failed",
                            schedule_id=schedule_id,
                        )
                        return False
                else:
                    # 더 이상 실행할 일정이 없으면 비활성화
                    log_info(
                        logger,
                        "schedule.execute.no_more_occurrences",
                        schedule_id=schedule_id,
                    )
                    self.disable_schedule(schedule_id)
                    return True
            except Exception as update_error:
                log_exception(
                    logger,
                    "schedule.execute.next_run_failed",
                    update_error,
                    schedule_id=schedule_id,
                )
                # 업데이트 실패시 실행하지 않음 (중복 방지)
                return False

            log_info(
                logger,
                "schedule.execute.started",
                schedule_id=schedule_id,
                keywords=params.get("keywords"),
                email=params.get("email"),
            )

            intended_run_at = schedule.get("next_run", datetime.now(timezone.utc))
            idempotency_enabled = is_feature_enabled(
                "WEB_IDEMPOTENCY_ENABLED", default=True
            )
            if idempotency_enabled:
                idempotency_key = build_schedule_idempotency_key(
                    schedule_id=schedule_id,
                    intended_run_at=intended_run_at,
                )
            else:
                idempotency_key = f"schedule:{schedule_id}:{uuid.uuid4()}"

            job_suffix = derive_job_id(idempotency_key, prefix="sched").split("_", 1)[1]
            schedule_job_id = f"schedule_{schedule_id}_{job_suffix}"
            ensure_history_row(
                db_path=self.db_path,
                job_id=schedule_job_id,
                params=params,
                status="pending",
                idempotency_key=idempotency_key,
            )

            # 뉴스레터 생성 작업을 큐에 추가
            redis_success = False
            if self.queue:
                try:
                    # RQ를 사용한 백그라운드 작업 시도
                    job = self.queue.enqueue(
                        generate_newsletter_task,
                        params,
                        schedule_job_id,
                        params.get("send_email", False),  # send_email 매개변수 추가
                        idempotency_key,
                        self.db_path,
                        job_id=schedule_job_id,
                        job_timeout="10m",
                        result_ttl=86400,  # 24시간 동안 결과 보관
                    )
                    log_info(
                        logger,
                        "schedule.execute.enqueued",
                        schedule_id=schedule_id,
                        job_id=job.id,
                    )
                    redis_success = True
                except Exception as redis_error:
                    # Redis 연결 실패 시 fallback으로 동기 실행
                    log_exception(
                        logger,
                        "schedule.execute.redis_failed",
                        redis_error,
                        schedule_id=schedule_id,
                    )
                    log_info(
                        logger,
                        "schedule.execute.fallback_sync",
                        schedule_id=schedule_id,
                    )

            if not redis_success:
                # Redis가 없거나 연결에 실패한 경우 동기 실행 (fallback)
                log_info(
                    logger, "schedule.execute.sync_started", schedule_id=schedule_id
                )
                result = generate_newsletter_task(
                    params,
                    schedule_job_id,
                    params.get("send_email", False),
                    idempotency_key,
                    self.db_path,
                )
                log_info(
                    logger,
                    "schedule.execute.sync_completed",
                    schedule_id=schedule_id,
                    status=result.get("status", "unknown") if result else "no_result",
                )

            # 다음 실행 시간은 이미 실행 전에 업데이트됨 (중복 실행 방지)

            return True

        except Exception as e:
            log_exception(
                logger,
                "schedule.execute.failed",
                e,
                schedule_id=schedule["id"],
            )
            return False

    def run_once(self) -> int:
        """한 번의 스케줄 체크 및 실행을 수행합니다."""
        log_info(logger, "schedule.run_once.started")

        schedules = self.get_pending_schedules()
        executed_count = 0

        log_debug(logger, "schedule.run_once.loaded", count=len(schedules))

        for i, schedule in enumerate(schedules):
            schedule_id = schedule.get("id", "unknown")
            log_debug(
                logger,
                "schedule.run_once.processing",
                schedule_id=schedule_id,
                index=i + 1,
                total=len(schedules),
            )
            try:
                if self.execute_schedule(schedule):
                    executed_count += 1
                    log_info(
                        logger,
                        "schedule.run_once.executed",
                        schedule_id=schedule_id,
                    )
                else:
                    log_warning(
                        logger,
                        "schedule.run_once.execution_failed",
                        schedule_id=schedule_id,
                    )
            except Exception as e:
                log_exception(
                    logger,
                    "schedule.run_once.execution_exception",
                    e,
                    schedule_id=schedule_id,
                )

        log_info(logger, "schedule.run_once.completed", executed_count=executed_count)
        return executed_count

    def run_continuous(self, check_interval: int = 60) -> None:
        """연속적으로 스케줄을 체크하고 실행합니다."""
        log_info(
            logger,
            "schedule.runner.started",
            check_interval_seconds=check_interval,
        )

        import time

        while True:
            try:
                self.run_once()
                time.sleep(check_interval)

            except KeyboardInterrupt:
                log_info(logger, "schedule.runner.stopped")
                break
            except Exception as e:
                log_exception(logger, "schedule.runner.loop_failed", e)
                time.sleep(check_interval)


def main() -> None:
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="Newsletter Schedule Runner")
    parser.add_argument("--db-path", default="storage.db", help="Database file path")
    parser.add_argument("--redis-url", help="Redis URL (default: from REDIS_URL env)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--interval", type=int, default=60, help="Check interval in seconds"
    )

    args = parser.parse_args()

    runner = ScheduleRunner(db_path=args.db_path, redis_url=args.redis_url)

    if args.once:
        count = runner.run_once()
        log_info(logger, "schedule.runner.once_completed", executed_count=count)
    else:
        runner.run_continuous(args.interval)


if __name__ == "__main__":
    main()
