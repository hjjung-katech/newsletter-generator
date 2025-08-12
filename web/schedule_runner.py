#!/usr/bin/env python3
"""
Schedule Runner for Newsletter Generator
Handles RRULE-based periodic newsletter generation
"""

import os
import sys
import sqlite3
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import redis
from rq import Queue
from dateutil.rrule import rrulestr
from dateutil import tz

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import task functions
from tasks import generate_newsletter_task

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
        if iso_string.endswith('Z'):
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

            now = datetime.now()
            logger.info(f"[DEBUG] Current time: {now}")
            
            # 모든 활성 스케줄 조회
            cursor.execute(
                "SELECT id, params, rrule, next_run, created_at FROM schedules WHERE enabled = 1"
            )
            all_schedules = cursor.fetchall()
            logger.info(f"[DEBUG] Found {len(all_schedules)} total active schedules")
            
            try:
                from web.time_utils import to_iso_utc  # PyInstaller
            except ImportError:
                from time_utils import to_iso_utc      # Development
            now_iso = to_iso_utc(now)
            
            for schedule in all_schedules:
                logger.info(f"[DEBUG] Schedule {schedule[0]}: next_run={schedule[3]}, due={'yes' if schedule[3] <= now_iso else 'no'}")
            
            # 실행 대기 중인 스케줄 조회 (UTC ISO 문자연 비교)
            logger.info(f"[DEBUG] Querying with now_iso: {now_iso}")
            cursor.execute(
                """
                SELECT id, params, rrule, next_run, created_at
                FROM schedules 
                WHERE enabled = 1 AND next_run <= ?
                ORDER BY next_run ASC
            """,
                (now_iso,),
            )
            
            pending_rows = cursor.fetchall()
            logger.info(f"[DEBUG] SQL query returned {len(pending_rows)} rows")

            schedules = []
            for row in pending_rows:
                schedules.append(
                    {
                        "id": row[0],
                        "params": json.loads(row[1]),
                        "rrule": row[2],
                        "next_run": self._parse_iso_datetime(row[3]),
                        "created_at": self._parse_iso_datetime(row[4]),
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
                after = datetime.now()

            # RRULE 파싱
            rrule = rrulestr(rrule_str, dtstart=after)

            # 다음 실행 시간 찾기
            next_occurrence = rrule.after(after)

            return next_occurrence

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

            logger.info(f"Executing schedule {schedule_id}")

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
                    logger.warning(f"Redis connection failed for schedule {schedule_id}: {redis_error}")
                    logger.info(f"Falling back to synchronous execution for schedule {schedule_id}")
                    
            if not redis_success:
                # Redis가 없거나 연결에 실패한 경우 동기 실행 (fallback)
                logger.info(f"Executing schedule {schedule_id} synchronously")
                fallback_job_id = f"schedule_{schedule_id}_{uuid.uuid4().hex[:8]}"
                result = generate_newsletter_task(
                    params, 
                    fallback_job_id, 
                    params.get("send_email", False)
                )
                logger.info(
                    f"Synchronous execution completed for schedule {schedule_id}: {result.get('status', 'unknown') if result else 'no result'}"
                )

            # 다음 실행 시간 계산 및 업데이트
            next_run = self.calculate_next_run(rrule_str, datetime.now())

            if next_run:
                # 미래 실행 시간이 있으면 업데이트
                self.update_schedule_next_run(schedule_id, next_run)
            else:
                # 더 이상 실행할 일정이 없으면 비활성화
                logger.info(
                    f"No more occurrences for schedule {schedule_id}, disabling"
                )
                self.disable_schedule(schedule_id)

            return True

        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule['id']}: {e}")
            # 스택트레이스 포함한 상세 에러 로깅
            import traceback
            logger.error(f"Full traceback for schedule {schedule['id']}: {traceback.format_exc()}")
            return False

    def run_once(self) -> int:
        """한 번의 스케줄 체크 및 실행을 수행합니다."""
        logger.info("Running schedule check...")

        schedules = self.get_pending_schedules()
        executed_count = 0
        
        logger.info(f"[DEBUG] Found {len(schedules)} pending schedules to execute")

        for i, schedule in enumerate(schedules):
            schedule_id = schedule.get("id", "unknown")
            logger.info(f"[DEBUG] Processing schedule {i+1}/{len(schedules)}: {schedule_id}")
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
        print(f"Executed {count} schedules")
    else:
        runner.run_continuous(args.interval)


if __name__ == "__main__":
    main()
