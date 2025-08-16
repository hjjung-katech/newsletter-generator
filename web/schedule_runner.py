#!/usr/bin/env python3
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
from typing import Dict, List, Optional

import redis
from dateutil import tz
from dateutil.rrule import rrulestr
from rq import Queue

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import task functions
from tasks import generate_newsletter_task

# Import time utilities
try:
    from web.time_utils import to_iso_utc  # PyInstaller
except ImportError:
    from time_utils import to_iso_utc  # Development

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScheduleRunner:
    """RRULE 기반 스케줄 실행기"""

    def __init__(self, db_path: str = "storage.db", redis_url: str = None):
        self.db_path = db_path
        self.redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )

        # Redis 연결 설정
        try:
            self.redis_conn = redis.from_url(self.redis_url)
            self.queue = Queue("default", connection=self.redis_conn)
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_conn = None
            self.queue = None

    def _parse_iso_datetime(self, iso_string: str) -> datetime:
        """Parse ISO datetime string, handling Z suffix properly"""
        if iso_string.endswith("Z"):
            # Remove Z and add UTC timezone
            return datetime.fromisoformat(iso_string[:-1]).replace(tzinfo=timezone.utc)
        else:
            return datetime.fromisoformat(iso_string)

    def get_pending_schedules(self) -> List[Dict]:
        """실행 대기 중인 스케줄 목록을 가져옵니다."""
        try:
            logger.info(f"[DEBUG] Using database path: {self.db_path}")
            logger.info(f"[DEBUG] Database file exists: {os.path.exists(self.db_path)}")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)
            logger.info(f"[DEBUG] Current time (UTC): {now}")

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
                logger.info(f"[DEBUG] Disabled {expired_count} expired test schedules")

            # 모든 활성 스케줄 조회
            cursor.execute(
                "SELECT id, params, rrule, next_run, created_at, is_test FROM schedules WHERE enabled = 1"
            )
            all_schedules = cursor.fetchall()
            logger.info(f"[DEBUG] Found {len(all_schedules)} total active schedules")

            # 스케줄 실행 대기열과 만료된 스케줄 분리 처리
            ready_for_execution = []
            expired_schedules = []
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

                    logger.info(
                        f"[DEBUG] Schedule {schedule_id}: next_run={next_run_str}, time_diff={time_diff.total_seconds():.1f}s, window={execution_window.total_seconds()}s"
                    )

                    # 실행 창 내에 있는 스케줄 (즉시 실행 대상)
                    if timedelta(0) <= time_diff <= execution_window:
                        logger.info(
                            f"[DEBUG] Schedule {schedule_id} is READY for execution (within {execution_window.total_seconds()/60:.1f}min window)"
                        )
                        ready_for_execution.append(schedule)

                    # 실행 창을 넘어선 과거 스케줄 (다음 주기로 업데이트)
                    elif time_diff > execution_window:
                        logger.info(
                            f"[DEBUG] Schedule {schedule_id} is EXPIRED (missed {time_diff.total_seconds()/60:.1f}min window), calculating next occurrence"
                        )

                        # 다음 실행 시간 계산
                        next_run_calculated = self.calculate_next_run(rrule_str, now)

                        if next_run_calculated:
                            cursor.execute(
                                "UPDATE schedules SET next_run = ? WHERE id = ?",
                                (to_iso_utc(next_run_calculated), schedule_id),
                            )
                            updated_count += 1
                            logger.info(
                                f"[DEBUG] Updated EXPIRED schedule {schedule_id} from {next_run_str} to {to_iso_utc(next_run_calculated)}"
                            )
                        else:
                            cursor.execute(
                                "UPDATE schedules SET enabled = 0 WHERE id = ?",
                                (schedule_id,),
                            )
                            logger.info(
                                f"[DEBUG] Disabled schedule {schedule_id} - no more occurrences"
                            )

                    # 미래 스케줄 (아직 실행 시간이 아님)
                    else:
                        logger.info(
                            f"[DEBUG] Schedule {schedule_id} is FUTURE (will run in {abs(time_diff.total_seconds())/60:.1f}min)"
                        )

                except Exception as parse_error:
                    logger.error(
                        f"[DEBUG] Failed to parse schedule {schedule_id}: {parse_error}"
                    )
                    continue

            if updated_count > 0:
                conn.commit()
                logger.info(
                    f"[DEBUG] Updated {updated_count} expired schedules to next occurrence"
                )

            # 실행 준비 완료된 스케줄들을 반환 형식으로 변환
            logger.info(
                f"[DEBUG] Found {len(ready_for_execution)} schedules ready for immediate execution"
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

                logger.info(
                    f"[DEBUG] Adding {'TEST' if is_test_bool else 'REGULAR'} schedule {schedule_id} to execution queue (next_run={next_run_str})"
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
            logger.error(f"Failed to get pending schedules: {e}")
            return []

    def calculate_next_run(
        self, rrule_str: str, after: datetime = None
    ) -> Optional[datetime]:
        """RRULE을 기반으로 다음 실행 시간을 계산합니다."""
        try:
            if after is None:
                after = datetime.now(timezone.utc)

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
            if next_occurrence_naive:
                next_occurrence = next_occurrence_naive.replace(tzinfo=timezone.utc)
                return next_occurrence
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to calculate next run for RRULE '{rrule_str}': {e}")
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

            logger.info(f"Updated schedule {schedule_id} next run to {next_run}")
            return True

        except Exception as e:
            logger.error(f"Failed to update schedule {schedule_id}: {e}")
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

            logger.info(f"Disabled schedule {schedule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable schedule {schedule_id}: {e}")
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
                        logger.info(
                            f"[EXECUTE] Pre-updated next run for schedule {schedule_id} to {next_run} (preventing duplicates)"
                        )
                    else:
                        logger.error(
                            f"[EXECUTE] Failed to pre-update next run for schedule {schedule_id}"
                        )
                        return False
                else:
                    # 더 이상 실행할 일정이 없으면 비활성화
                    logger.info(
                        f"[EXECUTE] No more occurrences for schedule {schedule_id}, disabling"
                    )
                    self.disable_schedule(schedule_id)
                    return True
            except Exception as update_error:
                logger.error(
                    f"[EXECUTE] Failed to calculate next run for schedule {schedule_id}: {update_error}"
                )
                # 업데이트 실패시 실행하지 않음 (중복 방지)
                return False

            logger.info(
                f"[EXECUTE] Starting execution for schedule {schedule_id} - {params.get('keywords', 'No keywords')}"
            )

            # 뉴스레터 생성 작업을 큐에 추가
            redis_success = False
            if self.queue:
                try:
                    # RQ를 사용한 백그라운드 작업 시도
                    job = self.queue.enqueue(
                        generate_newsletter_task,
                        params,
                        f"schedule_{schedule_id}",  # job_id 매개변수 추가
                        params.get("send_email", False),  # send_email 매개변수 추가
                        job_timeout="10m",
                        result_ttl=86400,  # 24시간 동안 결과 보관
                    )
                    logger.info(
                        f"Enqueued newsletter generation job {job.id} for schedule {schedule_id}"
                    )
                    redis_success = True
                except Exception as redis_error:
                    # Redis 연결 실패 시 fallback으로 동기 실행
                    logger.warning(
                        f"Redis connection failed for schedule {schedule_id}: {redis_error}"
                    )
                    logger.info(
                        f"Falling back to synchronous execution for schedule {schedule_id}"
                    )

            if not redis_success:
                # Redis가 없거나 연결에 실패한 경우 동기 실행 (fallback)
                logger.info(f"Executing schedule {schedule_id} synchronously")
                fallback_job_id = f"schedule_{schedule_id}_{uuid.uuid4().hex[:8]}"
                result = generate_newsletter_task(
                    params, fallback_job_id, params.get("send_email", False)
                )
                logger.info(
                    f"Synchronous execution completed for schedule {schedule_id}: {result.get('status', 'unknown') if result else 'no result'}"
                )

            # 다음 실행 시간은 이미 실행 전에 업데이트됨 (중복 실행 방지)

            return True

        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule['id']}: {e}")
            # 스택트레이스 포함한 상세 에러 로깅
            import traceback

            logger.error(
                f"Full traceback for schedule {schedule['id']}: {traceback.format_exc()}"
            )
            return False

    def run_once(self) -> int:
        """한 번의 스케줄 체크 및 실행을 수행합니다."""
        logger.info("Running schedule check...")

        schedules = self.get_pending_schedules()
        executed_count = 0

        logger.info(f"[DEBUG] Found {len(schedules)} pending schedules to execute")

        for i, schedule in enumerate(schedules):
            schedule_id = schedule.get("id", "unknown")
            logger.info(
                f"[DEBUG] Processing schedule {i+1}/{len(schedules)}: {schedule_id}"
            )
            try:
                if self.execute_schedule(schedule):
                    executed_count += 1
                    logger.info(f"[DEBUG] Schedule {schedule_id} executed successfully")
                else:
                    logger.warning(f"[DEBUG] Schedule {schedule_id} execution failed")
            except Exception as e:
                logger.error(f"[DEBUG] Exception executing schedule {schedule_id}: {e}")

        logger.info(f"Executed {executed_count} schedules")
        return executed_count

    def run_continuous(self, check_interval: int = 60):
        """연속적으로 스케줄을 체크하고 실행합니다."""
        logger.info(
            f"Starting continuous schedule runner (check interval: {check_interval}s)"
        )

        import time

        while True:
            try:
                self.run_once()
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Schedule runner stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in schedule runner: {e}")
                time.sleep(check_interval)


def main():
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
        logger.info(f"Executed {count} schedules")
    else:
        runner.run_continuous(args.interval)


if __name__ == "__main__":
    main()
