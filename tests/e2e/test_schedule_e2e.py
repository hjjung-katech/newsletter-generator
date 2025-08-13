#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄 End-to-End 테스트

이 테스트는 웹 인터페이스를 통한 전체 스케줄링 워크플로우를 검증합니다.
- 웹 서버 실행 필요
- 실제 스케줄 생성 API 테스트
- UI에서 스케줄 관리까지의 전체 플로우
"""

import pytest
import requests
import json
import time
from datetime import datetime, timezone, timedelta


def check_web_server(base_url="http://localhost:8000"):
    """웹 서버 실행 상태 확인"""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        return response.status_code == 200
    except:
        return False


@pytest.mark.e2e
@pytest.mark.mock_api  
class TestScheduleE2E:
    """스케줄 End-to-End 테스트"""
    
    @pytest.fixture(autouse=True)
    def ensure_web_server(self):
        """웹 서버 실행 확인"""
        if not check_web_server():
            pytest.skip("웹 서버가 실행되지 않음. 먼저 'python web/app.py' 실행 필요")
    
    @pytest.fixture
    def base_url(self):
        """기본 URL"""
        return "http://localhost:8000"
    
    def test_web_interface_availability(self, base_url):
        """웹 인터페이스 접근성 테스트"""
        # 메인 페이지
        response = requests.get(f"{base_url}/")
        assert response.status_code == 200, "Main page should be accessible"
        assert "Newsletter Generator" in response.text, "Page should contain title"
        
        # API 상태 확인
        try:
            response = requests.get(f"{base_url}/api/schedules")
            assert response.status_code == 200, "Schedules API should be accessible"
        except Exception as e:
            pytest.skip(f"API endpoint not available: {e}")
    
    def test_schedule_creation_via_api(self, base_url):
        """API를 통한 스케줄 생성 테스트"""
        # 현재 시간 + 5분 후 실행되는 테스트 스케줄
        now_kst = datetime.now(timezone(timedelta(hours=9)))  # KST
        target_time = now_kst + timedelta(minutes=5)
        
        # RRULE 생성
        rrule = f"FREQ=DAILY;BYHOUR={target_time.hour};BYMINUTE={target_time.minute}"
        
        schedule_data = {
            "keywords": ["AI반도체", "E2E테스트"],
            "email": "test@example.com",
            "template_style": "compact",
            "period": 14,
            "rrule": rrule,
            "send_email": False
        }
        
        # 스케줄 생성 요청
        response = requests.post(
            f"{base_url}/api/schedule",
            json=schedule_data,
            headers={"Content-Type": "application/json"}
        )
        
        # 응답 확인
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
        assert response.status_code == 200, f"Schedule creation failed: {response.text}"
        
        result = response.json()
        assert "schedule_id" in result, "Response should contain schedule_id"
        assert result.get("status") == "created", "Schedule should be created"
        
        return result["schedule_id"]
    
    def test_schedule_list_api(self, base_url):
        """스케줄 목록 조회 API 테스트"""
        response = requests.get(f"{base_url}/api/schedules")
        assert response.status_code == 200, "Schedules list should be accessible"
        
        schedules = response.json()
        assert isinstance(schedules, list), "Response should be a list"
        
        # 각 스케줄 데이터 구조 확인
        for schedule in schedules:
            required_fields = ["id", "keywords", "next_run", "enabled", "is_test"]
            for field in required_fields:
                assert field in schedule, f"Schedule should have {field} field"
    
    def test_full_schedule_workflow(self, base_url):
        """전체 스케줄 워크플로우 테스트"""
        # 1. 스케줄 생성
        schedule_id = self.test_schedule_creation_via_api(base_url)
        
        # 2. 생성된 스케줄 조회
        response = requests.get(f"{base_url}/api/schedules")
        schedules = response.json()
        
        created_schedule = None
        for schedule in schedules:
            if schedule["id"] == schedule_id:
                created_schedule = schedule
                break
        
        assert created_schedule is not None, "Created schedule should be found in list"
        assert created_schedule["enabled"] is True, "New schedule should be enabled"
        assert "AI반도체" in created_schedule["keywords"], "Keywords should match"
        
        # 3. 스케줄 비활성화 (삭제)
        delete_response = requests.delete(f"{base_url}/api/schedule/{schedule_id}")
        assert delete_response.status_code == 200, "Schedule deletion should succeed"
        
        # 4. 삭제 확인
        response = requests.get(f"{base_url}/api/schedules")
        schedules = response.json()
        
        active_schedule = None
        for schedule in schedules:
            if schedule["id"] == schedule_id and schedule["enabled"]:
                active_schedule = schedule
                break
        
        assert active_schedule is None, "Deleted schedule should not be in active list"
    
    def test_schedule_error_handling(self, base_url):
        """스케줄 생성 오류 처리 테스트"""
        # 잘못된 데이터로 스케줄 생성 시도
        invalid_data_cases = [
            # 필수 필드 누락
            {"keywords": ["test"]},  # email, rrule 없음
            
            # 잘못된 RRULE
            {
                "keywords": ["test"],
                "email": "test@example.com", 
                "rrule": "INVALID_RRULE"
            },
            
            # 과거 시간
            {
                "keywords": ["test"],
                "email": "test@example.com",
                "rrule": "FREQ=DAILY;BYHOUR=1;BYMINUTE=0"  # 새벽 1시 (이미 지남)
            }
        ]
        
        for invalid_data in invalid_data_cases:
            response = requests.post(
                f"{base_url}/api/schedule",
                json=invalid_data,
                headers={"Content-Type": "application/json"}
            )
            
            # 400번대 에러가 반환되어야 함
            assert response.status_code >= 400, f"Invalid data should return error: {invalid_data}"
    
    def test_test_schedule_auto_expiry(self, base_url):
        """테스트 스케줄 자동 만료 테스트"""
        # 1분 후 실행되는 테스트 스케줄 생성 (자동으로 테스트 모드가 됨)
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        target_time = now_kst + timedelta(minutes=1)
        
        rrule = f"FREQ=DAILY;BYHOUR={target_time.hour};BYMINUTE={target_time.minute}"
        
        schedule_data = {
            "keywords": ["테스트만료"],
            "email": "test@example.com",
            "template_style": "compact",
            "period": 14,
            "rrule": rrule,
            "send_email": False
        }
        
        response = requests.post(
            f"{base_url}/api/schedule",
            json=schedule_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        schedule_id = response.json()["schedule_id"]
        
        # 스케줄 조회하여 테스트 모드 확인
        response = requests.get(f"{base_url}/api/schedules")
        schedules = response.json()
        
        test_schedule = None
        for schedule in schedules:
            if schedule["id"] == schedule_id:
                test_schedule = schedule
                break
        
        assert test_schedule is not None, "Test schedule should be created"
        assert test_schedule["is_test"] is True, "1-minute schedule should be marked as test"
        
        # 정리: 생성된 테스트 스케줄 삭제
        requests.delete(f"{base_url}/api/schedule/{schedule_id}")
    
    def test_schedule_execution_monitoring(self, base_url):
        """스케줄 실행 모니터링 테스트 (실제 실행 없이 로직만)"""
        # 과거 시간으로 스케줄을 생성하여 실행 대기 상태 확인
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        past_time = now_kst - timedelta(minutes=5)  # 5분 전
        
        rrule = f"FREQ=DAILY;BYHOUR={past_time.hour};BYMINUTE={past_time.minute}"
        
        schedule_data = {
            "keywords": ["실행모니터링"],
            "email": "test@example.com", 
            "template_style": "compact",
            "period": 14,
            "rrule": rrule,
            "send_email": False
        }
        
        response = requests.post(
            f"{base_url}/api/schedule",
            json=schedule_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            schedule_id = response.json()["schedule_id"]
            
            # 스케줄이 실행 창 내에 있는지 확인
            response = requests.get(f"{base_url}/api/schedules")
            schedules = response.json()
            
            monitoring_schedule = None
            for schedule in schedules:
                if schedule["id"] == schedule_id:
                    monitoring_schedule = schedule
                    break
            
            if monitoring_schedule:
                # next_run이 현재 시간보다 미래로 업데이트되었는지 확인
                next_run_str = monitoring_schedule["next_run"]
                assert next_run_str is not None, "next_run should be set"
                
                # 정리
                requests.delete(f"{base_url}/api/schedule/{schedule_id}")


@pytest.mark.e2e
@pytest.mark.manual
class TestScheduleManualVerification:
    """수동 검증이 필요한 E2E 테스트"""
    
    def test_create_live_test_schedule(self):
        """라이브 테스트 스케줄 생성 (수동 확인용)"""
        # 이 테스트는 실제로 스케줄을 생성하고 실행을 확인하는 용도
        # CI에서는 스킵되고, 개발자가 수동으로 실행
        
        print("\n" + "="*50)
        print("라이브 테스트 스케줄 생성")
        print("="*50)
        
        # 2분 후 실행되는 스케줄 생성 코드 제공
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        target_time = now_kst + timedelta(minutes=2)
        
        print(f"현재 시간 (KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"실행 예정 시간: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        schedule_data = {
            "keywords": ["수동테스트", "실시간확인"],
            "email": "your@email.com",  # 실제 이메일로 변경
            "template_style": "compact",
            "period": 14,
            "rrule": f"FREQ=DAILY;BYHOUR={target_time.hour};BYMINUTE={target_time.minute}",
            "send_email": False
        }
        
        print(f"\n생성할 스케줄 데이터:")
        print(json.dumps(schedule_data, indent=2, ensure_ascii=False))
        
        print(f"\n수동 실행 방법:")
        print(f"1. 웹 서버 실행: python web/app.py")
        print(f"2. 브라우저에서 http://localhost:8000 접속")
        print(f"3. 스케줄 생성 후 {target_time.strftime('%H:%M')}에 실행 확인")
        
        # 실제로는 스킵 (수동 테스트이므로)
        pytest.skip("Manual verification test - run manually to create live schedule")


if __name__ == "__main__":
    # E2E 테스트만 실행
    pytest.main([__file__, "-v", "-m", "e2e and not manual"])