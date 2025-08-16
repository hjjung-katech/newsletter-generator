#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄링 테스트 전용 pytest 설정 및 픽스처

기존 conftest.py를 확장하여 스케줄링 관련 테스트를 위한
전용 픽스처와 설정을 제공합니다.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_schedule_db():
    """스케줄링 테스트용 임시 데이터베이스"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # 스케줄 테이블 생성
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
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
    """
    )

    cursor.execute(
        """
        CREATE TABLE history (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            keywords TEXT,
            execution_time REAL,
            error_message TEXT
        )
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # 정리
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def schedule_runner_mock():
    """Mock된 스케줄 러너"""
    from web.schedule_runner import ScheduleRunner

    runner = ScheduleRunner(db_path=":memory:", redis_url=None)
    runner.redis_conn = None
    runner.queue = None

    return runner


@pytest.fixture
def fixed_time():
    """고정된 테스트 시간"""
    return datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_newsletter_task():
    """뉴스레터 생성 태스크 Mock"""

    def mock_task(params, job_id, send_email=False):
        return {
            "status": "completed",
            "job_id": job_id,
            "execution_time": 1.2,
            "articles_found": 5,
            "articles_processed": 3,
        }

    with patch(
        "web.schedule_runner.generate_newsletter_task", side_effect=mock_task
    ) as mock:
        yield mock


@pytest.fixture
def sample_schedule_data():
    """샘플 스케줄 데이터"""
    return {
        "id": "sample_schedule_001",
        "params": {
            "keywords": ["AI", "반도체", "테스트"],
            "template_style": "compact",
            "period": 14,
            "email_compatible": False,
            "send_email": False,
        },
        "rrule": "FREQ=DAILY;BYHOUR=15;BYMINUTE=30",
        "next_run": "2025-08-13T15:30:00.000000Z",
        "created_at": "2025-08-13T14:00:00.000000Z",
        "enabled": 1,
        "is_test": 0,
        "expires_at": None,
    }


@pytest.fixture
def test_schedule_scenarios():
    """다양한 테스트 시나리오를 위한 스케줄 데이터"""
    base_time = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)

    return {
        "ready_regular": {
            "id": "ready_regular_001",
            "next_run": (base_time - timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 0,
            "enabled": 1,
        },
        "ready_test": {
            "id": "ready_test_001",
            "next_run": (base_time - timedelta(minutes=3)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 1,
            "enabled": 1,
        },
        "future_regular": {
            "id": "future_regular_001",
            "next_run": (base_time + timedelta(hours=2)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 0,
            "enabled": 1,
        },
        "expired_regular": {
            "id": "expired_regular_001",
            "next_run": (base_time - timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 0,
            "enabled": 1,
        },
        "expired_test": {
            "id": "expired_test_001",
            "next_run": (base_time - timedelta(minutes=20)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 1,
            "enabled": 1,
        },
        "disabled": {
            "id": "disabled_001",
            "next_run": (base_time - timedelta(minutes=2)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "is_test": 0,
            "enabled": 0,
        },
    }


@pytest.fixture
def populate_test_schedules(temp_schedule_db, test_schedule_scenarios):
    """테스트 DB에 다양한 시나리오의 스케줄 데이터 삽입"""

    conn = sqlite3.connect(temp_schedule_db)
    cursor = conn.cursor()

    base_params = {
        "keywords": ["테스트", "스케줄"],
        "template_style": "compact",
        "period": 14,
        "send_email": False,
    }

    for scenario_name, scenario_data in test_schedule_scenarios.items():
        # 만료 시간 설정 (테스트 스케줄만)
        expires_at = None
        if scenario_data["is_test"]:
            base_time = datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)
            expires_at = (base_time + timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )

        cursor.execute(
            """
            INSERT INTO schedules (id, params, rrule, next_run, created_at, enabled, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                scenario_data["id"],
                json.dumps(base_params),
                "FREQ=DAILY;BYHOUR=15;BYMINUTE=30",
                scenario_data["next_run"],
                "2025-08-13T14:00:00.000000Z",
                scenario_data["enabled"],
                scenario_data["is_test"],
                expires_at,
            ),
        )

    conn.commit()
    conn.close()

    return test_schedule_scenarios


@pytest.fixture
def mock_time_utils():
    """시간 유틸리티 함수들 Mock"""

    def mock_to_iso_utc(dt):
        if hasattr(dt, "isoformat"):
            return dt.isoformat().replace("+00:00", "Z")
        return dt

    def mock_get_utc_now():
        return datetime(2025, 8, 13, 15, 50, 0, tzinfo=timezone.utc)

    def mock_get_kst_now():
        return datetime(2025, 8, 14, 0, 50, 0, tzinfo=timezone(timedelta(hours=9)))

    mocks = {
        "to_iso_utc": mock_to_iso_utc,
        "get_utc_now": mock_get_utc_now,
        "get_kst_now": mock_get_kst_now,
    }

    return mocks


@pytest.fixture
def schedule_execution_monitor():
    """스케줄 실행 모니터링 도구"""

    class ExecutionMonitor:
        def __init__(self):
            self.executions = []
            self.errors = []

        def record_execution(self, schedule_id, status, details=None):
            self.executions.append(
                {
                    "schedule_id": schedule_id,
                    "status": status,
                    "timestamp": datetime.now(timezone.utc),
                    "details": details or {},
                }
            )

        def record_error(self, schedule_id, error_msg):
            self.errors.append(
                {
                    "schedule_id": schedule_id,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

        def get_execution_count(self, schedule_id=None):
            if schedule_id:
                return len(
                    [e for e in self.executions if e["schedule_id"] == schedule_id]
                )
            return len(self.executions)

        def get_error_count(self, schedule_id=None):
            if schedule_id:
                return len([e for e in self.errors if e["schedule_id"] == schedule_id])
            return len(self.errors)

        def reset(self):
            self.executions = []
            self.errors = []

    return ExecutionMonitor()


@pytest.fixture(scope="session")
def web_server_info():
    """웹 서버 정보"""
    return {"base_url": "http://localhost:8000", "timeout": 10, "retry_count": 3}


@pytest.fixture
def api_request_helper(web_server_info):
    """API 요청 헬퍼"""
    import requests

    class APIHelper:
        def __init__(self, base_url, timeout=10):
            self.base_url = base_url
            self.timeout = timeout

        def get(self, endpoint, **kwargs):
            return requests.get(
                f"{self.base_url}{endpoint}", timeout=self.timeout, **kwargs
            )

        def post(self, endpoint, json_data=None, **kwargs):
            return requests.post(
                f"{self.base_url}{endpoint}",
                json=json_data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
                **kwargs,
            )

        def delete(self, endpoint, **kwargs):
            return requests.delete(
                f"{self.base_url}{endpoint}", timeout=self.timeout, **kwargs
            )

        def is_server_running(self):
            try:
                response = self.get("/")
                return response.status_code == 200
            except:
                return False

    return APIHelper(web_server_info["base_url"], web_server_info["timeout"])


# pytest 마커 추가 설정
def pytest_configure(config):
    """스케줄링 관련 마커 추가"""
    config.addinivalue_line(
        "markers", "schedule_unit: Unit tests for scheduling functionality"
    )
    config.addinivalue_line(
        "markers", "schedule_integration: Integration tests for scheduling"
    )
    config.addinivalue_line(
        "markers", "schedule_e2e: E2E tests for scheduling workflow"
    )
    config.addinivalue_line(
        "markers", "time_sync: Tests for time synchronization logic"
    )
    config.addinivalue_line(
        "markers", "compatibility: Tests for backward compatibility"
    )


def pytest_collection_modifyitems(config, items):
    """스케줄 테스트 항목 조건부 스킵"""

    # 웹 서버 필요한 E2E 테스트 확인
    web_server_required = any("schedule_e2e" in item.keywords for item in items)

    if web_server_required:
        try:
            import requests

            response = requests.get("http://localhost:8000/", timeout=3)
            web_server_available = response.status_code == 200
        except:
            web_server_available = False

        if not web_server_available:
            for item in items:
                if "schedule_e2e" in item.keywords:
                    item.add_marker(
                        pytest.mark.skip(
                            reason="Web server not running at localhost:8000"
                        )
                    )


# 테스트별 환경 설정
@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 실행 전 환경 설정"""

    # 테스트 모드 활성화
    original_env = os.environ.copy()
    os.environ["NEWSLETTER_TEST_MODE"] = "true"
    os.environ["MOCK_API_RESPONSES"] = "true"

    yield

    # 환경 복원
    os.environ.clear()
    os.environ.update(original_env)
