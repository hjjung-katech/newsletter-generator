#!/usr/bin/env python3
"""
Railway 배포 End-to-End 테스트

이 테스트는 Railway 배포 환경에서 전체 workflow를 검증합니다.
"""

import pytest
import httpx
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any


class TestRailwayE2E:
    """Railway 배포 E2E 테스트"""

    @pytest.fixture
    def base_url(self) -> str:
        """테스트 대상 URL (Railway 배포 URL 또는 로컬)"""
        import os

        return os.getenv("TEST_BASE_URL", "http://localhost:5000")

    @pytest.fixture
    def test_email(self) -> str:
        """테스트용 이메일 주소"""
        return "test@example.com"

    @pytest.fixture
    def client(self, base_url: str):
        """HTTP 클라이언트"""
        return httpx.Client(base_url=base_url, timeout=30.0)

    def test_health_check(self, client: httpx.Client):
        """헬스체크 테스트"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        # Redis 연결은 환경에 따라 다를 수 있음
        assert "redis_connected" in data
        assert data["database"] == "sqlite"

    def test_newsletter_generation_workflow(
        self, client: httpx.Client, test_email: str
    ):
        """뉴스레터 생성 전체 워크플로우 테스트"""
        # 1. 뉴스레터 생성 요청
        payload = {
            "keywords": ["AI", "technology"],
            "email": test_email,
            "template_style": "compact",
            "email_compatible": True,
            "period": 7,
        }

        response = client.post("/api/generate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "processing"
        assert "job_id" in data

        job_id = data["job_id"]

        # 2. 작업 상태 폴링 (최대 5분)
        max_wait = 300  # 5분
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/status/{job_id}")
            assert response.status_code == 200

            status_data = response.json()
            status = status_data.get("status")

            if status == "completed":
                assert "result" in status_data
                assert status_data["result"] is not None
                break
            elif status == "failed":
                pytest.fail(f"Job failed: {status_data.get('error', 'Unknown error')}")

            time.sleep(10)  # 10초마다 체크
        else:
            pytest.fail(f"Job {job_id} did not complete within {max_wait} seconds")

    def test_schedule_creation_and_management(
        self, client: httpx.Client, test_email: str
    ):
        """스케줄 생성 및 관리 테스트"""
        # 1. 스케줄 생성
        schedule_payload = {
            "keywords": ["tech", "startup"],
            "email": test_email,
            "rrule": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "template_style": "compact",
            "email_compatible": True,
        }

        response = client.post("/api/schedule", json=schedule_payload)
        assert response.status_code == 201

        data = response.json()
        assert data["status"] == "scheduled"
        assert "schedule_id" in data
        assert "next_run" in data

        schedule_id = data["schedule_id"]

        # 2. 스케줄 목록 조회
        response = client.get("/api/schedules")
        assert response.status_code == 200

        schedules = response.json()
        assert isinstance(schedules, list)

        # 생성한 스케줄이 목록에 있는지 확인
        created_schedule = None
        for schedule in schedules:
            if schedule["id"] == schedule_id:
                created_schedule = schedule
                break

        assert created_schedule is not None
        assert created_schedule["enabled"] is True
        assert created_schedule["rrule"] == schedule_payload["rrule"]

        # 3. 스케줄 즉시 실행 (테스트 환경에서만)
        if "localhost" in client.base_url or "test" in client.base_url:
            response = client.post(f"/api/schedule/{schedule_id}/run")
            # 성공적으로 큐에 추가되거나 직접 실행되어야 함
            assert response.status_code == 200

            run_data = response.json()
            assert run_data["status"] in ["queued", "completed"]

        # 4. 스케줄 삭제
        response = client.delete(f"/api/schedule/{schedule_id}")
        assert response.status_code == 200

        delete_data = response.json()
        assert delete_data["status"] == "cancelled"

        # 5. 삭제 후 목록에서 제거되었는지 확인
        response = client.get("/api/schedules")
        assert response.status_code == 200

        schedules_after_delete = response.json()
        active_schedules = [
            s for s in schedules_after_delete if s["id"] == schedule_id and s["enabled"]
        ]
        assert len(active_schedules) == 0

    def test_invalid_rrule_handling(self, client: httpx.Client, test_email: str):
        """잘못된 RRULE 처리 테스트"""
        invalid_payload = {
            "keywords": ["test"],
            "email": test_email,
            "rrule": "INVALID_RRULE",
        }

        response = client.post("/api/schedule", json=invalid_payload)
        assert response.status_code == 400

        error_data = response.json()
        assert "error" in error_data
        assert "Invalid RRULE" in error_data["error"]

    def test_missing_required_fields(self, client: httpx.Client):
        """필수 필드 누락 테스트"""
        # 이메일 누락
        response = client.post(
            "/api/schedule", json={"keywords": ["test"], "rrule": "FREQ=DAILY"}
        )
        assert response.status_code == 400

        # RRULE 누락
        response = client.post(
            "/api/schedule", json={"keywords": ["test"], "email": "test@example.com"}
        )
        assert response.status_code == 400

        # 키워드와 도메인 둘 다 누락
        response = client.post(
            "/api/schedule", json={"email": "test@example.com", "rrule": "FREQ=DAILY"}
        )
        assert response.status_code == 400

    def test_history_functionality(self, client: httpx.Client):
        """히스토리 기능 테스트"""
        response = client.get("/api/history")
        assert response.status_code == 200

        history = response.json()
        assert isinstance(history, list)
        # 히스토리는 비어있을 수도 있고, 이전 테스트의 결과가 있을 수도 있음

        for item in history:
            assert "id" in item
            assert "created_at" in item
            assert "status" in item

    def test_concurrent_requests(self, client: httpx.Client, test_email: str):
        """동시 요청 처리 테스트"""
        import threading
        import queue

        results = queue.Queue()

        def make_request():
            try:
                payload = {
                    "keywords": ["concurrent", "test"],
                    "email": test_email,
                    "template_style": "compact",
                }
                response = client.post("/api/generate", json=payload)
                results.put(("success", response.status_code))
            except Exception as e:
                results.put(("error", str(e)))

        # 3개의 동시 요청
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=60)

        # 결과 검증
        success_count = 0
        error_count = 0

        while not results.empty():
            result_type, value = results.get()
            if result_type == "success":
                assert value == 200
                success_count += 1
            else:
                error_count += 1

        # 최소한 일부 요청은 성공해야 함
        assert success_count > 0

        # 에러가 있더라도 치명적이지 않아야 함
        if error_count > 0:
            print(f"Warning: {error_count} requests failed out of 3")


@pytest.mark.asyncio
class TestRailwayAsyncE2E:
    """비동기 E2E 테스트"""

    @pytest.fixture
    def base_url(self) -> str:
        import os

        return os.getenv("TEST_BASE_URL", "http://localhost:5000")

    async def test_async_newsletter_generation(self, base_url: str):
        """비동기 뉴스레터 생성 테스트"""
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            payload = {"keywords": ["async", "test"], "email": "async@example.com"}

            response = await client.post("/api/generate", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "processing"

            # 간단한 상태 체크 (실제 완료까지 기다리지 않음)
            job_id = data["job_id"]
            status_response = await client.get(f"/api/status/{job_id}")
            assert status_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
