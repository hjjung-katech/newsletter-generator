#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄 실행 통합 테스트

이 테스트는 실제 스케줄 실행 플로우를 검증합니다.
- 데이터베이스 연동
- 스케줄 생성부터 실행까지의 전체 플로우
- 시간대 동기화 통합 테스트
"""

import pytest
import sqlite3
import tempfile
import os
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
@pytest.mark.mock_api
class TestScheduleIntegration:
    """스케줄 실행 통합 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        # 데이터베이스 스키마 생성
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 스케줄 테이블
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
        
        # 히스토리 테이블 (실행 결과 추적용)
        cursor.execute('''
            CREATE TABLE history (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                keywords TEXT,
                execution_time REAL,
                error_message TEXT
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
    
    @pytest.fixture
    def mock_newsletter_generation(self):
        """뉴스레터 생성 Mock"""
        def mock_task(params, job_id, send_email=False):
            return {
                'status': 'completed',
                'job_id': job_id,
                'execution_time': 1.5,
                'articles_count': 5
            }
        
        with patch('web.schedule_runner.generate_newsletter_task', side_effect=mock_task) as mock:
            yield mock
    
    @pytest.fixture
    def schedule_runner_with_db(self, temp_db):
        """데이터베이스가 연결된 스케줄 러너"""
        from web.schedule_runner import ScheduleRunner
        
        # Redis 없이 테스트 모드
        runner = ScheduleRunner(db_path=temp_db, redis_url=None)
        runner.redis_conn = None
        runner.queue = None
        
        return runner
    
    def create_test_schedule(self, db_path, schedule_id, next_run_str, is_test=1, enabled=1):
        """테스트 스케줄 생성 헬퍼"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        params = {
            "keywords": ["AI반도체", "테스트실행"],
            "template_style": "compact",
            "period": 14,
            "send_email": False
        }
        
        expires_at = None
        if is_test:
            # 테스트 스케줄은 1시간 후 만료
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        cursor.execute('''
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            schedule_id,
            json.dumps(params),
            "FREQ=DAILY;BYHOUR=15;BYMINUTE=50",
            next_run_str,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            enabled,
            is_test,
            expires_at
        ))
        
        conn.commit()
        conn.close()
        
        return params
    
    def test_schedule_creation_to_execution_flow(self, temp_db, schedule_runner_with_db, mock_newsletter_generation):
        """스케줄 생성부터 실행까지 전체 플로우 테스트"""
        # 1. 실행 준비된 스케줄 생성
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        ready_time = fixed_now - timedelta(minutes=2)  # 2분 전 스케줄
        
        schedule_params = self.create_test_schedule(
            temp_db, 
            "test_flow_schedule",
            ready_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            is_test=1
        )
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 2. 실행 대기 스케줄 조회
            pending_schedules = schedule_runner_with_db.get_pending_schedules()
            
            assert len(pending_schedules) == 1, f"Expected 1 pending schedule, got {len(pending_schedules)}"
            
            schedule = pending_schedules[0]
            assert schedule['id'] == "test_flow_schedule"
            assert schedule['is_test'] is True
            assert schedule['params']['keywords'] == ["AI반도체", "테스트실행"]
            
            # 3. 스케줄 실행
            success = schedule_runner_with_db.execute_schedule(schedule)
            
            assert success, "Schedule execution should succeed"
            
            # 4. Mock 함수 호출 확인
            mock_newsletter_generation.assert_called_once()
            call_args = mock_newsletter_generation.call_args[0]
            
            assert call_args[0] == schedule_params, "Parameters should match"
            assert "schedule_test_flow_schedule" in call_args[1], "Job ID should include schedule ID"
            assert call_args[2] is False, "send_email should be False for test"
    
    def test_multiple_schedules_execution_order(self, temp_db, schedule_runner_with_db, mock_newsletter_generation):
        """여러 스케줄의 실행 순서 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 다른 시간대의 실행 준비된 스케줄들 생성
        schedules = [
            ("schedule_1", fixed_now - timedelta(minutes=5)),  # 5분 전
            ("schedule_2", fixed_now - timedelta(minutes=10)), # 10분 전  
            ("schedule_3", fixed_now - timedelta(minutes=2)),  # 2분 전
        ]
        
        for schedule_id, next_run_time in schedules:
            self.create_test_schedule(
                temp_db,
                schedule_id,
                next_run_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                is_test=1
            )
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 실행 대기 스케줄 조회
            pending_schedules = schedule_runner_with_db.get_pending_schedules()
            
            assert len(pending_schedules) == 3, f"Expected 3 schedules, got {len(pending_schedules)}"
            
            # 실행 순서 확인 (next_run 오름차순)
            schedule_ids = [s['id'] for s in pending_schedules]
            expected_order = ["schedule_2", "schedule_1", "schedule_3"]  # 시간 순
            
            assert schedule_ids == expected_order, f"Expected {expected_order}, got {schedule_ids}"
    
    def test_expired_schedule_cleanup(self, temp_db, schedule_runner_with_db):
        """만료된 스케줄 정리 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 만료된 스케줄과 유효한 스케줄 생성
        expired_time = fixed_now - timedelta(hours=2)  # 2시간 전에 만료
        valid_time = fixed_now + timedelta(minutes=30)  # 30분 후 만료
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # 만료된 테스트 스케줄
        cursor.execute('''
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            "expired_schedule",
            json.dumps({"keywords": ["test"]}),
            "FREQ=DAILY",
            fixed_now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            fixed_now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            expired_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        ))
        
        # 유효한 테스트 스케줄  
        cursor.execute('''
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            "valid_schedule",
            json.dumps({"keywords": ["test"]}),
            "FREQ=DAILY",
            fixed_now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            fixed_now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            valid_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        ))
        
        conn.commit()
        conn.close()
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 스케줄 조회 (만료 처리 포함)
            schedule_runner_with_db.get_pending_schedules()
            
            # 데이터베이스 상태 확인
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, enabled FROM schedules WHERE id = 'expired_schedule'")
            expired_result = cursor.fetchone()
            
            cursor.execute("SELECT id, enabled FROM schedules WHERE id = 'valid_schedule'")
            valid_result = cursor.fetchone()
            
            conn.close()
            
            # 만료된 스케줄은 비활성화, 유효한 스케줄은 활성 유지
            assert expired_result[1] == 0, "Expired schedule should be disabled"
            assert valid_result[1] == 1, "Valid schedule should remain enabled"
    
    def test_schedule_next_run_update_after_execution(self, temp_db, schedule_runner_with_db, mock_newsletter_generation):
        """실행 후 다음 실행 시간 업데이트 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        ready_time = fixed_now - timedelta(minutes=2)
        
        # 일일 스케줄 생성
        self.create_test_schedule(
            temp_db,
            "daily_schedule",
            ready_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            is_test=0  # 정규 스케줄로 설정
        )
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 실행 전 next_run 확인
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT next_run FROM schedules WHERE id = 'daily_schedule'")
            old_next_run = cursor.fetchone()[0]
            conn.close()
            
            # 스케줄 실행
            pending = schedule_runner_with_db.get_pending_schedules()
            assert len(pending) == 1
            
            success = schedule_runner_with_db.execute_schedule(pending[0])
            assert success, "Schedule execution should succeed"
            
            # 실행 후 next_run 확인
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT next_run FROM schedules WHERE id = 'daily_schedule'")
            new_next_run = cursor.fetchone()[0]
            conn.close()
            
            # next_run이 업데이트되었는지 확인
            assert new_next_run != old_next_run, "next_run should be updated after execution"
            
            # 새로운 시간이 미래인지 확인
            new_next_run_dt = datetime.fromisoformat(new_next_run.replace('Z', '+00:00'))
            assert new_next_run_dt > fixed_now, "New next_run should be in the future"
    
    def test_test_vs_regular_schedule_windows(self, temp_db, schedule_runner_with_db):
        """테스트/정규 스케줄의 실행 창 차이 테스트"""
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        
        # 15분 전 스케줄들 생성 (정규: 실행, 테스트: 만료)
        past_time = fixed_now - timedelta(minutes=15)
        
        self.create_test_schedule(temp_db, "regular_15min", past_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), is_test=0)
        self.create_test_schedule(temp_db, "test_15min", past_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), is_test=1)
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            pending = schedule_runner_with_db.get_pending_schedules()
            
            # 정규 스케줄만 실행 대기열에 있어야 함 (30분 창 내)
            # 테스트 스케줄은 만료되어 업데이트됨 (10분 창 초과)
            pending_ids = [s['id'] for s in pending]
            
            assert "regular_15min" in pending_ids, "Regular schedule should be ready (within 30min window)"
            assert "test_15min" not in pending_ids, "Test schedule should be expired (beyond 10min window)"
    
    def test_concurrent_schedule_execution_safety(self, temp_db, mock_newsletter_generation):
        """동시 실행 안전성 테스트"""
        # 두 개의 독립적인 러너 생성 (동시 실행 시뮬레이션)
        from web.schedule_runner import ScheduleRunner
        
        runner1 = ScheduleRunner(db_path=temp_db, redis_url=None)
        runner1.redis_conn = None 
        runner1.queue = None
        
        runner2 = ScheduleRunner(db_path=temp_db, redis_url=None)
        runner2.redis_conn = None
        runner2.queue = None
        
        # 실행 준비된 스케줄 생성
        fixed_now = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
        ready_time = fixed_now - timedelta(minutes=2)
        
        self.create_test_schedule(temp_db, "concurrent_test", ready_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
        
        with patch('web.schedule_runner.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # 첫 번째 러너가 스케줄 조회
            pending1 = runner1.get_pending_schedules()
            assert len(pending1) == 1
            
            # 첫 번째 러너가 실행 (next_run 업데이트)
            success1 = runner1.execute_schedule(pending1[0])
            assert success1
            
            # 두 번째 러너가 같은 시간에 조회
            pending2 = runner2.get_pending_schedules()
            
            # 첫 번째 러너가 이미 실행했으므로 두 번째는 빈 결과
            assert len(pending2) == 0, "Schedule should not be executed twice"
            
            # Mock이 한 번만 호출되었는지 확인
            assert mock_newsletter_generation.call_count == 1, "Newsletter generation should be called only once"


@pytest.mark.integration 
@pytest.mark.real_api
class TestScheduleRealTimeExecution:
    """실제 시간 기반 스케줄 실행 테스트 (선택적)"""
    
    @pytest.mark.slow
    def test_real_time_schedule_trigger(self):
        """실제 시간 기반 스케줄 트리거 테스트"""
        # 이 테스트는 CI에서 기본적으로 스킵됨 (RUN_REAL_API_TESTS=1 필요)
        
        # 현재 시간 + 10초 후 실행되는 스케줄 생성
        import time
        
        now = datetime.now(timezone.utc)
        target_time = now + timedelta(seconds=10)
        
        # 실제 환경에서는 더 복잡한 설정이 필요하므로
        # 여기서는 기본 로직만 테스트
        assert target_time > now, "Target time should be in future"
        
        # 실제 실행은 수동 테스트로 분리
        pytest.skip("Real-time execution test requires manual verification")


if __name__ == "__main__":
    # 통합 테스트만 실행
    pytest.main([__file__, "-v", "-m", "integration"])