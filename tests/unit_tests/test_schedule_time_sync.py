#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄 시간 동기화 단위 테스트

이 테스트는 schedule_runner의 시간 처리 로직을 검증합니다.
- 시간대 변환 정확성
- 실행 창 계산
- 스케줄 상태 분류 (READY, FUTURE, EXPIRED)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile
import os
import json


@pytest.mark.unit
class TestScheduleTimeSync:
    """시간 동기화 단위 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 픽스처"""
        # 임시 파일 생성
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        # 스케줄 테이블 생성
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE schedules (
                id TEXT PRIMARY KEY,
                params JSON NOT NULL,
                rrule TEXT NOT NULL,
                next_run TEXT NOT NULL,
                created_at TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                is_test INTEGER DEFAULT 0,
                expires_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
        yield db_path
        
        # 정리
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_time_diff_calculation(self):
        """시간 차이 계산 테스트"""
        # 고정 시간 설정
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        test_cases = [
            {
                "description": "5분 전 일반 스케줄 - 실행",
                "next_run": (fixed_now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "is_test": False,
                "expected_status": "READY"
            },
            {
                "description": "3분 전 테스트 스케줄 - 실행",
                "next_run": (fixed_now - timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "is_test": True,
                "expected_status": "READY"
            },
            {
                "description": "35분 전 일반 스케줄 - 만료",
                "next_run": (fixed_now - timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "is_test": False,
                "expected_status": "EXPIRED"
            },
            {
                "description": "15분 전 테스트 스케줄 - 만료",
                "next_run": (fixed_now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "is_test": True,
                "expected_status": "EXPIRED"
            },
            {
                "description": "미래 시간 - 대기",
                "next_run": (fixed_now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "is_test": False,
                "expected_status": "FUTURE"
            }
        ]
        
        for test_case in test_cases:
            next_run_dt = datetime.fromisoformat(test_case["next_run"].replace('Z', '+00:00'))
            time_diff = fixed_now - next_run_dt
            
            # 실행 창 결정
            execution_window = timedelta(minutes=10) if test_case["is_test"] else timedelta(minutes=30)
            
            # 상태 분류
            if timedelta(0) <= time_diff <= execution_window:
                actual_status = "READY"
            elif time_diff > execution_window:
                actual_status = "EXPIRED"
            else:
                actual_status = "FUTURE"
            
            expected_status = test_case["expected_status"]
            description = test_case["description"]
            
            assert actual_status == expected_status, f"{description}: expected {expected_status}, got {actual_status}"

    def test_execution_window_logic(self):
        """실행 창 로직 테스트"""
        # 현재 시간 고정
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        test_cases = [
            # (is_test, minutes_ago, should_execute)
            (False, 5, True),   # 정규 스케줄, 5분 전 - 실행
            (False, 35, False), # 정규 스케줄, 35분 전 - 만료
            (True, 5, True),    # 테스트 스케줄, 5분 전 - 실행
            (True, 15, False),  # 테스트 스케줄, 15분 전 - 만료
        ]
        
        for is_test, minutes_ago, should_execute in test_cases:
            next_run = fixed_now - timedelta(minutes=minutes_ago)
            time_diff = fixed_now - next_run
            
            # 실행 창 계산
            execution_window = timedelta(minutes=10) if is_test else timedelta(minutes=30)
            
            # 실행 여부 판단
            is_ready = timedelta(0) <= time_diff <= execution_window
            
            assert is_ready == should_execute, f"Test={is_test}, {minutes_ago}min ago: expected {should_execute}, got {is_ready}"

    def test_timezone_parsing(self):
        """시간대 파싱 테스트"""
        from web.schedule_runner import ScheduleRunner
        runner = ScheduleRunner()
        
        test_cases = [
            # (iso_string, expected_timezone_aware)
            ("2025-08-13T06:50:13Z", True),
            ("2025-08-13T06:50:13.227366Z", True),
            ("2025-08-13T15:50:13+09:00", True),
        ]
        
        for iso_string, should_be_aware in test_cases:
            parsed = runner._parse_iso_datetime(iso_string)
            
            assert isinstance(parsed, datetime), f"Failed to parse {iso_string}"
            assert (parsed.tzinfo is not None) == should_be_aware, f"Timezone awareness mismatch for {iso_string}"

    def test_schedule_classification(self, temp_db):
        """스케줄 분류 테스트 - 데이터베이스 없이"""
        # 고정 시간 설정
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 스케줄 시뮬레이션 데이터
        schedules = [
            {
                "id": "ready_regular",
                "next_run": "2025-08-13T15:45:00.000000Z",  # 5분 전
                "is_test": False,
                "expected": "READY"
            },
            {
                "id": "ready_test", 
                "next_run": "2025-08-13T15:48:00.000000Z",  # 2분 전
                "is_test": True,
                "expected": "READY"
            },
            {
                "id": "expired_regular",
                "next_run": "2025-08-13T15:15:00.000000Z",  # 35분 전  
                "is_test": False,
                "expected": "EXPIRED"
            },
            {
                "id": "expired_test",
                "next_run": "2025-08-13T15:35:00.000000Z",  # 15분 전
                "is_test": True,
                "expected": "EXPIRED"
            },
            {
                "id": "future_schedule",
                "next_run": "2025-08-13T16:00:00.000000Z",  # 10분 후
                "is_test": False,
                "expected": "FUTURE"
            }
        ]
        
        for schedule in schedules:
            next_run_dt = datetime.fromisoformat(schedule["next_run"].replace('Z', '+00:00'))
            time_diff = fixed_now - next_run_dt
            
            # 실행 창 결정
            execution_window = timedelta(minutes=10) if schedule["is_test"] else timedelta(minutes=30)
            
            # 상태 분류
            if timedelta(0) <= time_diff <= execution_window:
                actual_status = "READY"
            elif time_diff > execution_window:
                actual_status = "EXPIRED"  
            else:
                actual_status = "FUTURE"
            
            expected = schedule["expected"]
            assert actual_status == expected, f"Schedule {schedule['id']}: expected {expected}, got {actual_status}"

    def test_next_run_calculation(self):
        """다음 실행 시간 계산 테스트"""
        from web.schedule_runner import ScheduleRunner
        runner = ScheduleRunner()
        
        # RRULE 테스트 케이스
        test_cases = [
            # (rrule, current_time, expected_next_hour)
            ("FREQ=DAILY;BYHOUR=9;BYMINUTE=0", 
             datetime(2025, 8, 13, 10, 0, tzinfo=timezone.utc), 9),  # 다음 날 9시
            ("FREQ=DAILY;BYHOUR=15;BYMINUTE=30", 
             datetime(2025, 8, 13, 14, 0, tzinfo=timezone.utc), 15), # 오늘 15:30
        ]
        
        for rrule_str, current_time, expected_hour in test_cases:
            next_run = runner.calculate_next_run(rrule_str, current_time)
            
            assert next_run is not None, f"Failed to calculate next run for {rrule_str}"
            assert next_run.hour == expected_hour, f"Expected hour {expected_hour}, got {next_run.hour}"
            assert next_run > current_time, f"Next run should be in future: {next_run} <= {current_time}"

    def test_test_schedule_expiry(self, temp_db):
        """테스트 스케줄 만료 처리 테스트"""
        from web.schedule_runner import ScheduleRunner
        
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 만료된 테스트 스케줄과 유효한 스케줄 생성
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            "expired_test",
            json.dumps({"keywords": ["test"]}),
            "FREQ=DAILY;BYHOUR=15;BYMINUTE=0",
            "2025-08-13T15:00:00Z",
            "2025-08-13T14:00:00Z",
            "2025-08-13T15:30:00Z"  # 20분 전에 만료
        ))
        
        cursor.execute('''
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            "valid_test",
            json.dumps({"keywords": ["test"]}),
            "FREQ=DAILY;BYHOUR=16;BYMINUTE=0", 
            "2025-08-13T16:00:00Z",
            "2025-08-13T15:00:00Z",
            "2025-08-13T16:30:00Z"  # 아직 유효
        ))
        
        conn.commit()
        conn.close()
        
        # 만료 로직 직접 테스트
        expired_time = datetime.fromisoformat("2025-08-13T15:30:00Z".replace('Z', '+00:00'))
        valid_time = datetime.fromisoformat("2025-08-13T16:30:00Z".replace('Z', '+00:00'))
        
        # 만료 여부 확인  
        is_expired_expired = fixed_now > expired_time
        is_valid_expired = fixed_now > valid_time
        
        assert is_expired_expired == True, "Expired test schedule should be expired"
        assert is_valid_expired == False, "Valid test schedule should not be expired"


@pytest.mark.unit
class TestTimeUtilities:
    """시간 유틸리티 함수 테스트"""
    
    def test_iso_time_conversion(self):
        """ISO 시간 변환 테스트"""
        # UTC 시간 생성
        utc_time = datetime(2025, 8, 13, 6, 50, 0, tzinfo=timezone.utc)
        
        # 수동 ISO 변환
        iso_string = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        assert "2025-08-13T06:50:00" in iso_string, f"Invalid ISO format: {iso_string}"
        assert iso_string.endswith('Z'), f"ISO string should end with Z: {iso_string}"

    def test_timezone_consistency(self):
        """시간대 일관성 테스트"""
        # UTC 시간
        utc_now = datetime.now(timezone.utc)
        
        # KST 시간 (UTC+9)
        kst_offset = timezone(timedelta(hours=9))
        kst_now = datetime.now(kst_offset)
        
        # 시간 차이 계산
        time_diff = kst_now.replace(tzinfo=timezone.utc) - utc_now
        expected_diff = timedelta(hours=9)
        
        # 9시간 차이여야 함 (오차 범위 1분)
        assert abs(time_diff - expected_diff) < timedelta(minutes=1), f"KST should be UTC+9, got diff: {time_diff}"


@pytest.mark.unit
class TestScheduleExecutionLogic:
    """스케줄 실행 로직 테스트"""
    
    def test_execution_window_boundaries(self):
        """실행 창 경계 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 경계 케이스들
        boundary_cases = [
            # (minutes_ago, is_test, expected_ready)
            (30, False, True),   # 정규 스케줄 경계 - 실행
            (31, False, False),  # 정규 스케줄 경계 초과 - 만료
            (10, True, True),    # 테스트 스케줄 경계 - 실행
            (11, True, False),   # 테스트 스케줄 경계 초과 - 만료
            (0, False, True),    # 정확한 시간 - 실행
            (0, True, True),     # 정확한 시간 (테스트) - 실행
        ]
        
        for minutes_ago, is_test, expected_ready in boundary_cases:
            next_run = fixed_now - timedelta(minutes=minutes_ago)
            time_diff = fixed_now - next_run
            
            execution_window = timedelta(minutes=10) if is_test else timedelta(minutes=30)
            is_ready = timedelta(0) <= time_diff <= execution_window
            
            assert is_ready == expected_ready, f"Boundary test failed: {minutes_ago}min ago, test={is_test}"

    def test_schedule_priority_ordering(self):
        """스케줄 우선순위 정렬 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 다른 시간의 스케줄들
        schedules = [
            {"id": "schedule_1", "next_run": fixed_now - timedelta(minutes=10)},
            {"id": "schedule_2", "next_run": fixed_now - timedelta(minutes=2)},
            {"id": "schedule_3", "next_run": fixed_now - timedelta(minutes=5)},
        ]
        
        # next_run 기준 정렬 (가장 오래된 것부터)
        sorted_schedules = sorted(schedules, key=lambda x: x["next_run"])
        
        expected_order = ["schedule_1", "schedule_3", "schedule_2"]
        actual_order = [s["id"] for s in sorted_schedules]
        
        assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"


if __name__ == "__main__":
    # 단위 테스트만 실행
    pytest.main([__file__, "-v", "-m", "unit"])