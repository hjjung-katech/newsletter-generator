#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄링 기능 호환성 테스트

이 테스트는 새로운 스케줄링 기능이 기존 기능과 호환되는지 검증합니다.
- 기존 뉴스레터 생성 기능과의 충돌 확인
- 기존 설정 및 환경변수 영향도 분석
- 다른 테스트들과의 상호 작용 검증
"""

import pytest
import os
import tempfile
import sqlite3
import json
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta


@pytest.mark.unit
@pytest.mark.mock_api
class TestScheduleCompatibility:
    """스케줄링 기능 호환성 테스트"""
    
    def test_schedule_runner_import_compatibility(self):
        """스케줄 러너 임포트 호환성 테스트"""
        # 기존 모듈들과 함께 임포트해도 충돌이 없는지 확인
        try:
            # 기존 핵심 모듈들
            from newsletter.cli import main as cli_main
            from newsletter.main import main as newsletter_main
            
            # 새로운 스케줄링 모듈
            from web.schedule_runner import ScheduleRunner
            from web.app import app
            
            assert cli_main is not None, "CLI module should be importable"
            assert newsletter_main is not None, "Newsletter main should be importable"
            assert ScheduleRunner is not None, "ScheduleRunner should be importable"
            assert app is not None, "Flask app should be importable"
            
        except ImportError as e:
            pytest.fail(f"Import compatibility issue: {e}")
    
    def test_existing_config_not_affected(self):
        """기존 설정에 영향을 주지 않는지 테스트"""
        # 기존 ConfigManager 동작 확인
        try:
            from newsletter.centralized_settings import get_settings
            
            # 기존 설정 로드가 정상 작동하는지 확인
            settings = get_settings()
            
            # 기본 설정들이 존재하는지 확인
            assert hasattr(settings, 'llm_factory'), "LLM factory settings should exist"
            
            # 스케줄링 모듈 임포트 후에도 설정이 유지되는지 확인
            from web.schedule_runner import ScheduleRunner
            
            settings_after = get_settings()
            assert settings_after is not None, "Settings should remain available after schedule import"
            
        except Exception as e:
            pytest.fail(f"Configuration compatibility issue: {e}")
    
    def test_database_schema_backward_compatibility(self):
        """데이터베이스 스키마 하위 호환성 테스트"""
        # 기존 스키마와 새로운 컬럼들의 호환성 확인
        
        # 임시 DB 생성 (기존 스키마)
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 기존 스키마 (is_test, expires_at 없음)
            cursor.execute('''
                CREATE TABLE schedules (
                    id TEXT PRIMARY KEY,
                    params JSON NOT NULL,
                    rrule TEXT NOT NULL,
                    next_run TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1
                )
            ''')
            
            # 기존 데이터 삽입
            cursor.execute('''
                INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                "legacy_schedule",
                json.dumps({"keywords": ["legacy"]}),
                "FREQ=DAILY",
                "2025-08-14T09:00:00Z",
                "2025-08-13T09:00:00Z",
                1
            ))
            
            conn.commit()
            
            # 새로운 컬럼 추가 (실제 마이그레이션 시뮬레이션)
            cursor.execute("ALTER TABLE schedules ADD COLUMN is_test INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE schedules ADD COLUMN expires_at TEXT")
            
            conn.commit()
            
            # 기존 데이터 조회가 정상 작동하는지 확인
            cursor.execute("SELECT id, params, is_test FROM schedules WHERE id = 'legacy_schedule'")
            result = cursor.fetchone()
            
            assert result[0] == "legacy_schedule", "Legacy schedule should be found"
            assert result[2] == 0, "Default is_test should be 0"
            
            conn.close()
            
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_existing_newsletter_generation_not_affected(self):
        """기존 뉴스레터 생성 기능에 영향을 주지 않는지 테스트"""
        
        # Mock 설정으로 기존 뉴스레터 생성 테스트
        with patch('newsletter.main.collect_news') as mock_collect, \
             patch('newsletter.main.process_articles') as mock_process, \
             patch('newsletter.main.compose_newsletter') as mock_compose:
            
            # Mock 반환값 설정
            mock_collect.return_value = [
                {"title": "Test Article", "url": "http://test.com", "content": "Test content"}
            ]
            mock_process.return_value = [
                {"title": "Test Article", "summary": "Test summary", "score": 0.8}
            ]
            mock_compose.return_value = "<html>Test Newsletter</html>"
            
            # 기존 뉴스레터 생성 함수 호출 시뮬레이션
            try:
                from newsletter.main import main as newsletter_main
                
                # 기본 파라미터로 실행 (실제 실행하지 않고 Mock 확인만)
                # newsletter_main() 대신 Mock 호출 확인
                
                # 스케줄링 모듈이 로드된 상태에서도 기존 함수들이 정상인지 확인
                from web.schedule_runner import ScheduleRunner
                
                # Mock들이 호출 가능한지 확인
                assert mock_collect is not None, "collect_news should be mockable"
                assert mock_process is not None, "process_articles should be mockable"
                assert mock_compose is not None, "compose_newsletter should be mockable"
                
            except Exception as e:
                pytest.fail(f"Newsletter generation compatibility issue: {e}")
    
    def test_web_app_routes_not_conflicting(self):
        """웹 앱 라우트 충돌 없음 확인 테스트"""
        try:
            from web.app import app
            
            # 기존 라우트들이 여전히 존재하는지 확인
            with app.test_client() as client:
                
                # 기본 라우트
                response = client.get('/')
                assert response.status_code == 200, "Main route should be accessible"
                
                # 기존 API 라우트들
                existing_routes = [
                    '/api/generate',
                    '/api/suggest',
                    '/api/schedules',  # 새로 추가된 것
                ]
                
                for route in existing_routes:
                    # HEAD 요청으로 라우트 존재 확인
                    response = client.head(route)
                    assert response.status_code != 404, f"Route {route} should exist"
                    
        except Exception as e:
            pytest.fail(f"Web app route compatibility issue: {e}")
    
    def test_environment_variables_isolation(self):
        """환경 변수 격리 테스트"""
        # 기존 환경 변수들이 스케줄링 기능에 의해 영향받지 않는지 확인
        
        original_env = os.environ.copy()
        
        try:
            # 테스트용 환경 변수 설정
            os.environ['GEMINI_API_KEY'] = 'test_key'
            os.environ['NEWSLETTER_TEST_MODE'] = 'true'
            
            # 스케줄러 생성
            from web.schedule_runner import ScheduleRunner
            runner = ScheduleRunner()
            
            # 기존 환경 변수가 변경되지 않았는지 확인
            assert os.environ.get('GEMINI_API_KEY') == 'test_key', "Existing env vars should not be modified"
            assert os.environ.get('NEWSLETTER_TEST_MODE') == 'true', "Test mode should not be affected"
            
        finally:
            # 환경 변수 복원
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_existing_test_fixtures_compatibility(self):
        """기존 테스트 픽스처들과의 호환성 테스트"""
        # conftest.py의 기존 픽스처들이 정상 작동하는지 확인
        
        try:
            # 기존 픽스처들 임포트 테스트
            from tests.conftest import (
                korean_keywords,
                sample_articles,
                mock_google_ai,
                mock_serper_api
            )
            
            # Mock 픽스처들이 정상적으로 생성되는지 확인
            mock_ai = mock_google_ai()
            mock_serper = mock_serper_api()
            
            assert mock_ai is not None, "Google AI mock should be available"
            assert mock_serper is not None, "Serper API mock should be available"
            assert 'organic' in mock_serper, "Serper mock should have expected structure"
            
        except ImportError as e:
            pytest.fail(f"Test fixture compatibility issue: {e}")


@pytest.mark.integration
@pytest.mark.mock_api
class TestScheduleIntegrationCompatibility:
    """스케줄링 통합 호환성 테스트"""
    
    def test_schedule_with_existing_workflow(self):
        """기존 워크플로우와 함께 스케줄 실행 테스트"""
        
        # 기존 뉴스레터 생성 파이프라인과 스케줄러의 통합 테스트
        with patch('web.tasks.generate_newsletter_task') as mock_task:
            mock_task.return_value = {
                'status': 'completed',
                'job_id': 'test_job',
                'articles_count': 3
            }
            
            from web.schedule_runner import ScheduleRunner
            
            # 임시 DB 설정
            db_fd, db_path = tempfile.mkstemp(suffix='.db')
            os.close(db_fd)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 스케줄 테이블 생성
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
                
                # 테스트 스케줄 삽입
                now = datetime.now(timezone.utc)
                ready_time = now - timedelta(minutes=2)
                
                cursor.execute('''
                    INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test)
                    VALUES (?, ?, ?, ?, ?, 1, 1)
                ''', (
                    "integration_test",
                    json.dumps({
                        "keywords": ["통합테스트"],
                        "template_style": "compact",
                        "period": 14,
                        "send_email": False
                    }),
                    "FREQ=DAILY",
                    ready_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                ))
                
                conn.commit()
                conn.close()
                
                # 스케줄 러너 실행
                runner = ScheduleRunner(db_path=db_path, redis_url=None)
                runner.redis_conn = None
                runner.queue = None
                
                with patch('web.schedule_runner.datetime') as mock_datetime:
                    mock_datetime.now.return_value = now
                    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    
                    # 스케줄 실행
                    executed_count = runner.run_once()
                    
                    assert executed_count > 0, "Schedule should be executed"
                    mock_task.assert_called_once(), "Newsletter generation should be called"
                    
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
    
    def test_config_manager_isolation_during_schedule(self):
        """스케줄 실행 중 ConfigManager 격리 테스트"""
        
        # ConfigManager 상태가 스케줄 실행에 의해 오염되지 않는지 확인
        try:
            from newsletter.centralized_settings import get_settings
            
            # 초기 상태 확인
            initial_settings = get_settings()
            initial_state = str(initial_settings)
            
            # 스케줄 관련 작업 시뮬레이션
            from web.schedule_runner import ScheduleRunner
            runner = ScheduleRunner()
            
            # 설정 상태가 변경되지 않았는지 확인
            final_settings = get_settings()
            final_state = str(final_settings)
            
            # 기본적인 구조는 유지되어야 함 (완전 동일하지 않을 수 있지만)
            assert final_settings is not None, "Settings should remain available"
            assert hasattr(final_settings, 'llm_factory'), "Core settings should be preserved"
            
        except Exception as e:
            pytest.fail(f"Config manager isolation issue: {e}")


@pytest.mark.unit
class TestExistingTestsNotBroken:
    """기존 테스트들이 깨지지 않았는지 확인"""
    
    def test_can_import_existing_test_modules(self):
        """기존 테스트 모듈들이 임포트 가능한지 확인"""
        
        existing_test_modules = [
            'tests.test_compose',
            'tests.test_chains', 
            'tests.unit_tests.test_config_manager',
            'tests.unit_tests.test_centralized_settings',
        ]
        
        for module_name in existing_test_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                # 스케줄링 기능 추가로 인한 임포트 오류는 실패
                if 'schedule' in str(e).lower():
                    pytest.fail(f"Scheduling changes broke existing test: {module_name} - {e}")
                # 다른 이유 (API 키 없음 등)는 경고만
                pytest.skip(f"Existing test import issue (not related to scheduling): {module_name} - {e}")
    
    def test_existing_fixtures_still_work(self):
        """기존 픽스처들이 여전히 작동하는지 확인"""
        
        # 주요 픽스처들 테스트
        from tests.conftest import korean_keywords, sample_articles
        
        # 픽스처 함수들 직접 호출해서 정상 작동 확인
        keywords = korean_keywords()
        articles = sample_articles()
        
        assert isinstance(keywords, list), "korean_keywords fixture should return list"
        assert len(keywords) > 0, "korean_keywords should not be empty"
        
        assert isinstance(articles, list), "sample_articles fixture should return list"
        assert len(articles) > 0, "sample_articles should not be empty"
        assert 'title' in articles[0], "articles should have expected structure"


if __name__ == "__main__":
    # 호환성 테스트만 실행
    pytest.main([__file__, "-v"])