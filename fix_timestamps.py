#!/usr/bin/env python3
"""
데이터베이스 시간 레코드 보정 스크립트

잘못 저장된 KST 타임스탬프를 UTC로 변환합니다.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone

from dateutil.parser import parse


def is_kst_timestamp(timestamp_str):
    """
    KST 형식으로 저장된 잘못된 타임스탬프인지 확인
    형식: 2025-08-12T08:13:53.686941 (타임존 정보 없이 KST 시간)
    """
    try:
        # T가 포함된 ISO 형식이면서 Z나 타임존 정보가 없는 경우
        if (
            "T" in timestamp_str
            and not timestamp_str.endswith("Z")
            and "+" not in timestamp_str
            and "-" not in timestamp_str[-6:]
        ):
            # 시간이 대략적으로 KST 범위에 있는지 확인 (9시간 차이)
            dt = parse(timestamp_str)
            current_utc = datetime.now(timezone.utc)

            # 미래 시간이거나 너무 많이 앞선 경우 KST로 저장된 것으로 간주
            if dt > current_utc:
                return True

        return False
    except Exception:
        return False


def convert_kst_to_utc(timestamp_str):
    """
    KST 타임스탬프를 UTC로 변환
    """
    try:
        # KST로 저장된 시간을 파싱 (timezone 정보 없음)
        dt = parse(timestamp_str)

        # KST로 가정하고 timezone 정보 추가 (UTC+9)
        kst_tz = timezone(datetime.timedelta(hours=9))
        dt_kst = dt.replace(tzinfo=kst_tz)

        # UTC로 변환
        dt_utc = dt_kst.astimezone(timezone.utc)

        # Z 형식으로 반환
        return dt_utc.isoformat().replace("+00:00", "Z")
    except Exception as e:
        print(f"Error converting timestamp {timestamp_str}: {e}")
        return timestamp_str  # 변환 실패시 원본 반환


def fix_database_timestamps(db_path="storage.db"):
    """
    데이터베이스의 잘못된 타임스탬프를 수정
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    print(f"🔧 Fixing timestamps in database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. History 테이블의 잘못된 타임스탬프 찾기
        cursor.execute("SELECT id, created_at FROM history WHERE created_at LIKE '%T%'")
        history_records = cursor.fetchall()

        print(f"📊 Found {len(history_records)} history records with T format")

        fixed_count = 0
        for job_id, created_at in history_records:
            if is_kst_timestamp(created_at):
                corrected_time = convert_kst_to_utc(created_at)
                print(f"  🔄 {job_id[:8]}... : {created_at} → {corrected_time}")

                cursor.execute(
                    "UPDATE history SET created_at = ? WHERE id = ?",
                    (corrected_time, job_id),
                )
                fixed_count += 1

        print(f"✅ Fixed {fixed_count} history records")

        # 2. Schedules 테이블의 다음 실행 시간도 확인
        cursor.execute(
            "SELECT id, next_run, created_at FROM schedules WHERE next_run LIKE '%T%' OR created_at LIKE '%T%'"
        )
        schedule_records = cursor.fetchall()

        print(f"📊 Found {len(schedule_records)} schedule records to check")

        schedule_fixed = 0
        for schedule_id, next_run, created_at in schedule_records:
            updates = {}

            if next_run and is_kst_timestamp(next_run):
                updates["next_run"] = convert_kst_to_utc(next_run)

            if created_at and is_kst_timestamp(created_at):
                updates["created_at"] = convert_kst_to_utc(created_at)

            if updates:
                print(f"  🔄 Schedule {schedule_id[:8]}...")
                for field, new_value in updates.items():
                    cursor.execute(
                        f"UPDATE schedules SET {field} = ? WHERE id = ?",
                        (new_value, schedule_id),
                    )
                schedule_fixed += 1

        print(f"✅ Fixed {schedule_fixed} schedule records")

        # 커밋
        conn.commit()

        print(f"🎉 Database timestamp fix completed!")
        print(f"   - History records fixed: {fixed_count}")
        print(f"   - Schedule records fixed: {schedule_fixed}")

        return True

    except Exception as e:
        print(f"❌ Error fixing timestamps: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_timestamps(db_path="storage.db"):
    """
    타임스탬프 수정 결과 검증
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"\n🔍 Verifying timestamp fixes...")

    # 현재 시간
    now_utc = datetime.now(timezone.utc)
    print(f"Current UTC time: {now_utc}")

    # History 테이블 확인
    cursor.execute(
        "SELECT id, created_at FROM history ORDER BY created_at DESC LIMIT 5"
    )
    recent_history = cursor.fetchall()

    print(f"\n📊 Recent history records:")
    for job_id, created_at in recent_history:
        try:
            dt = parse(created_at)
            if dt.tzinfo is None:
                status = "❓ No timezone"
            elif dt > now_utc:
                status = "⚠️  Future time"
            else:
                status = "✅ Valid"
        except:
            status = "❌ Parse error"

        print(f"  {job_id[:8]}... : {created_at} {status}")

    conn.close()


if __name__ == "__main__":
    db_path = "dist/storage.db" if os.path.exists("dist/storage.db") else "storage.db"

    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        sys.exit(1)

    print("=" * 60)
    print("Newsletter Database Timestamp Fixer")
    print("=" * 60)

    # 수정 실행
    success = fix_database_timestamps(db_path)

    if success:
        # 검증
        verify_timestamps(db_path)
    else:
        print("❌ Fix failed!")
        sys.exit(1)
