#!/usr/bin/env python3
"""
웹 애플리케이션 데이터베이스 초기화 스크립트

이 스크립트는 storage.db가 없거나 손상된 경우 새로운 데이터베이스를 생성합니다.
개발 환경 설정이나 프로덕션 배포 시 사용할 수 있습니다.
"""

import os
import sqlite3
import sys
from datetime import datetime


def create_database(db_path="storage.db"):
    """
    SQLite 데이터베이스와 필요한 테이블들을 생성합니다.

    Args:
        db_path: 데이터베이스 파일 경로
    """
    print(f"🔧 데이터베이스 초기화 중: {db_path}")

    # 기존 파일이 있다면 백업 생성
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"📦 기존 데이터베이스를 백업했습니다: {backup_path}")

    # 새 데이터베이스 생성
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("📝 테이블 생성 중...")

    # History table - 뉴스레터 생성 히스토리
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            result JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """
    )
    print("  ✅ history 테이블 생성됨")

    # Schedules table - 정기 발송 예약
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            rrule TEXT NOT NULL,
            next_run TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
    """
    )
    print("  ✅ schedules 테이블 생성됨")

    # 인덱스 생성
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled)"
    )
    print("  ✅ 인덱스 생성됨")

    conn.commit()
    conn.close()

    print(f"🎉 데이터베이스 초기화 완료: {db_path}")
    return True


def verify_database(db_path="storage.db"):
    """
    데이터베이스가 올바르게 생성되었는지 확인합니다.

    Args:
        db_path: 데이터베이스 파일 경로

    Returns:
        bool: 검증 성공 여부
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = ["history", "schedules"]
        missing_tables = [table for table in required_tables if table not in tables]

        if missing_tables:
            print(f"❌ 누락된 테이블: {missing_tables}")
            conn.close()
            return False

        # 각 테이블의 컬럼 확인
        for table in required_tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"  📊 {table} 테이블 컬럼: {columns}")

        conn.close()
        print("✅ 데이터베이스 검증 성공")
        return True

    except Exception as e:
        print(f"❌ 데이터베이스 검증 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="웹 애플리케이션 데이터베이스 초기화")
    parser.add_argument(
        "--db-path", default="storage.db", help="데이터베이스 파일 경로"
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="검증만 수행 (생성하지 않음)"
    )
    parser.add_argument(
        "--force", action="store_true", help="기존 데이터베이스 강제 재생성"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("🗄️  Newsletter Generator 데이터베이스 초기화 도구")
    print("=" * 50)

    if args.verify_only:
        if os.path.exists(args.db_path):
            verify_database(args.db_path)
        else:
            print(f"❌ 데이터베이스 파일이 존재하지 않습니다: {args.db_path}")
            sys.exit(1)
        return

    # 데이터베이스 존재 확인
    if os.path.exists(args.db_path) and not args.force:
        print(f"📁 데이터베이스 파일이 이미 존재합니다: {args.db_path}")
        choice = (
            input("기존 데이터베이스를 재생성하시겠습니까? (y/N): ").strip().lower()
        )
        if choice not in ["y", "yes"]:
            print("❌ 초기화를 취소했습니다.")
            sys.exit(0)

    # 데이터베이스 생성
    try:
        create_database(args.db_path)

        # 검증
        if verify_database(args.db_path):
            print("\n🎊 데이터베이스 초기화가 성공적으로 완료되었습니다!")
        else:
            print("\n❌ 데이터베이스 초기화 후 검증에 실패했습니다.")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 데이터베이스 초기화 중 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
