#!/usr/bin/env python3
# flake8: noqa
"""
Schedule Runner for Newsletter Generator
Handles RRULE-based periodic newsletter generation
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import redis
from rq import Queue

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import task functions
from tasks import generate_newsletter_task

try:
    from db_state import ensure_database_schema
except ImportError:
    from web.db_state import ensure_database_schema  # pragma: no cover

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

try:
    from schedule_scan import calculate_next_run as calculate_schedule_next_run
    from schedule_scan import disable_schedule as disable_schedule_entry
    from schedule_scan import get_pending_schedules as get_pending_schedule_entries
    from schedule_scan import parse_iso_datetime as parse_schedule_iso_datetime
    from schedule_scan import update_schedule_next_run as update_schedule_entry_next_run
except ImportError:
    from web.schedule_scan import (
        calculate_next_run as calculate_schedule_next_run,  # pragma: no cover
    )
    from web.schedule_scan import disable_schedule as disable_schedule_entry
    from web.schedule_scan import get_pending_schedules as get_pending_schedule_entries
    from web.schedule_scan import parse_iso_datetime as parse_schedule_iso_datetime
    from web.schedule_scan import (
        update_schedule_next_run as update_schedule_entry_next_run,
    )

try:
    from schedule_dispatch import (
        ScheduleExecutionContext,
        build_execution_context,
        enqueue_schedule_job,
        record_execution_failure,
        record_no_more_occurrences,
        record_preupdate_failure,
        run_sync_fallback,
    )
except ImportError:
    from web.schedule_dispatch import (  # pragma: no cover
        ScheduleExecutionContext,
        build_execution_context,
        enqueue_schedule_job,
        record_execution_failure,
        record_no_more_occurrences,
        record_preupdate_failure,
        run_sync_fallback,
    )

try:
    from runtime_paths import resolve_database_path
except ImportError:
    from web.runtime_paths import resolve_database_path  # pragma: no cover

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
DEFAULT_DATABASE_PATH = resolve_database_path()


class ScheduleRunner:
    """RRULE 기반 스케줄 실행기"""

    def __init__(self, db_path: str | None = None, redis_url: str | None = None):
        self.db_path = db_path or DEFAULT_DATABASE_PATH
        ensure_database_schema(self.db_path)
        self.redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self.redis_conn: redis.Redis | None = None
        self.queue: Queue | None = None

        # Redis 연결 설정
        try:
            self.redis_conn = redis.from_url(self.redis_url)
            self.queue = Queue("default", connection=self.redis_conn)
        except Exception as e:
            log_exception(logger, "schedule.redis.connection_failed", e)

    def _parse_iso_datetime(self, iso_string: str) -> datetime:
        """Parse ISO datetime string, handling Z suffix properly"""
        return cast(datetime, parse_schedule_iso_datetime(iso_string))

    def get_pending_schedules(self) -> List[Dict]:
        """실행 대기 중인 스케줄 목록을 가져옵니다."""
        now = datetime.now(timezone.utc)
        return cast(
            List[Dict],
            get_pending_schedule_entries(
                self.db_path,
                now=now,
                parse_datetime=self._parse_iso_datetime,
                calculate_next_run_fn=self.calculate_next_run,
            ),
        )

    def calculate_next_run(
        self, rrule_str: str, after: datetime | None = None
    ) -> Optional[datetime]:
        """RRULE을 기반으로 다음 실행 시간을 계산합니다."""
        return cast(Optional[datetime], calculate_schedule_next_run(rrule_str, after))

    def update_schedule_next_run(self, schedule_id: str, next_run: datetime) -> bool:
        """스케줄의 다음 실행 시간을 업데이트합니다."""
        return cast(
            bool,
            update_schedule_entry_next_run(
                self.db_path,
                schedule_id,
                next_run,
            ),
        )

    def disable_schedule(self, schedule_id: str) -> bool:
        """스케줄을 비활성화합니다."""
        return cast(bool, disable_schedule_entry(self.db_path, schedule_id))

    def execute_schedule(self, schedule: Dict) -> bool:
        """스케줄을 실행합니다."""
        context: ScheduleExecutionContext | None = None
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
                        record_preupdate_failure(self.db_path, schedule_id)
                        return False
                else:
                    # 더 이상 실행할 일정이 없으면 비활성화
                    record_no_more_occurrences(self.db_path, schedule_id)
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

            intended_run_at = cast(
                datetime,
                schedule.get("next_run", datetime.now(timezone.utc)),
            )
            context = build_execution_context(
                self.db_path,
                schedule_id=schedule_id,
                params=params,
                intended_run_at=intended_run_at,
                logger=logger,
            )

            if not enqueue_schedule_job(
                self.queue,
                generate_newsletter_task,
                context,
                logger=logger,
            ):
                # Redis가 없거나 연결에 실패한 경우 동기 실행 (fallback)
                run_sync_fallback(
                    generate_newsletter_task,
                    context,
                    logger=logger,
                )

            # 다음 실행 시간은 이미 실행 전에 업데이트됨 (중복 실행 방지)

            return True

        except Exception as e:
            record_execution_failure(
                self.db_path,
                schedule["id"],
                e,
                job_id=context.schedule_job_id if context else None,
            )
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
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DATABASE_PATH,
        help="Database file path",
    )
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
