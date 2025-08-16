#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""스케줄 End-to-End 테스트"""

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests


def check_web_server(base_url="http://localhost:8000"):
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


@pytest.mark.e2e
class TestScheduleE2E:
    @pytest.fixture(autouse=True)
    def ensure_web_server(self):
        if not check_web_server():
            pytest.skip("웹 서버가 실행되지 않음. 먼저 'python web/app.py' 실행 필요")

    @pytest.fixture
    def base_url(self):
        return "http://localhost:8000"

    def test_schedule_creation_and_deletion(self, base_url):
        # 스케줄 생성
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        target_time = now_kst + timedelta(minutes=5)
        rrule = f"FREQ=DAILY;BYHOUR={target_time.hour};BYMINUTE={target_time.minute}"
        schedule_data = {
            "keywords": ["API 테스트", "E2E"],
            "email": "test@example.com",
            "rrule": rrule,
        }
        response = requests.post(f"{base_url}/api/schedule", json=schedule_data)
        assert response.status_code == 201
        result = response.json()
        assert "schedule_id" in result
        schedule_id = result["schedule_id"]

        # 스케줄 조회
        response = requests.get(f"{base_url}/api/schedules")
        assert response.status_code == 200
        schedules = response.json()
        assert any(s["id"] == schedule_id for s in schedules)

        # 스케줄 삭제
        response = requests.delete(f"{base_url}/api/schedule/{schedule_id}")
        assert response.status_code == 200

        # 삭제 확인
        response = requests.get(f"{base_url}/api/schedules")
        assert response.status_code == 200
        schedules = response.json()
        assert not any(s["id"] == schedule_id and s["enabled"] for s in schedules)
