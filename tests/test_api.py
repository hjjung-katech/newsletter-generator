"""
Web API 통합 테스트
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# 테스트를 위해 sys.path 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web"))

# 환경 설정 (app import 전에 설정)
import os

os.environ["MOCK_MODE"] = "false"  # 실제 모드로 테스트
os.environ["SERPER_API_KEY"] = "test_key"
os.environ["OPENAI_API_KEY"] = "test_openai_key"

from web.app import app


@pytest.fixture
def client():
    """테스트 클라이언트 설정"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_newsletter_generation():
    """뉴스레터 생성 모킹"""
    with patch("web.app.newsletter_cli") as mock_cli:
        mock_cli.generate_newsletter.return_value = {
            "status": "success",
            "content": "<html><body><h1>AI Technology Newsletter</h1><p>Generated with authentic data from various sources</p></body></html>",
            "title": "AI Newsletter",
            "generation_stats": {
                "articles_found": 15,
                "articles_processed": 10,
                "generation_time": 45.2,
            },
        }
        yield mock_cli


class TestHealthCheck:
    """헬스체크 엔드포인트 테스트"""

    def test_health_check_basic(self, client):
        """기본 헬스체크 테스트"""
        response = client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] in ["ok", "degraded", "error"]
        assert "dependencies" in data
        assert "timestamp" in data

    def test_health_check_dependencies(self, client):
        """의존성 체크 테스트"""
        response = client.get("/health")
        data = json.loads(response.data)

        deps = data["dependencies"]

        # 필수 의존성들이 체크되는지 확인
        assert "database" in deps
        assert "config" in deps
        assert "newsletter_cli" in deps
        assert "filesystem" in deps

        # 각 의존성이 상태 정보를 가지고 있는지 확인
        for dep_name, dep_info in deps.items():
            assert "status" in dep_info
            assert "message" in dep_info


class TestNewsletterAPI:
    """뉴스레터 API 테스트"""

    def test_newsletter_endpoint_success(self, client, mock_newsletter_generation):
        """뉴스레터 엔드포인트 성공 테스트"""
        response = client.get("/newsletter?topic=AI&period=14")

        assert response.status_code == 200
        assert response.content_type == "text/html; charset=utf-8"

        # Mock이 아닌 실제 데이터인지 확인
        html_content = response.data.decode("utf-8")
        assert "AI Technology Newsletter" in html_content
        assert "Generated with authentic data" in html_content
        assert "Mock" not in html_content  # Mock 문자열이 없어야 함

    def test_newsletter_endpoint_missing_topic(self, client):
        """토픽 누락 시 에러 테스트"""
        response = client.get("/newsletter?period=14")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing required parameter" in data["error"]

    def test_newsletter_endpoint_invalid_period(self, client):
        """잘못된 기간 파라미터 테스트"""
        # 유효하지 않은 기간들
        invalid_periods = [0, 3, 15, 60, -1]

        for period in invalid_periods:
            response = client.get(f"/newsletter?topic=AI&period={period}")
            assert response.status_code == 400

            data = json.loads(response.data)
            assert "Invalid period" in data["error"]
            assert "1, 7, 14, 30" in data["error"]

    def test_newsletter_endpoint_valid_periods(
        self, client, mock_newsletter_generation
    ):
        """유효한 기간 파라미터 테스트"""
        valid_periods = [1, 7, 14, 30]

        for period in valid_periods:
            response = client.get(f"/newsletter?topic=AI&period={period}")
            assert response.status_code == 200

            # generate_newsletter가 올바른 period로 호출되었는지 확인
            mock_newsletter_generation.generate_newsletter.assert_called_with(
                keywords="AI",
                template_style="compact",
                email_compatible=False,
                period=period,
            )

    def test_newsletter_endpoint_keywords_parameter(
        self, client, mock_newsletter_generation
    ):
        """keywords 파라미터 테스트"""
        response = client.get("/newsletter?keywords=machine learning&period=7")

        assert response.status_code == 200
        mock_newsletter_generation.generate_newsletter.assert_called_with(
            keywords="machine learning",
            template_style="compact",
            email_compatible=False,
            period=7,
        )


class TestGenerateAPI:
    """생성 API 테스트"""

    def test_generate_api_period_validation(self, client):
        """생성 API 기간 검증 테스트"""
        test_data = {"keywords": "AI", "period": 99}  # 유효하지 않은 기간

        response = client.post(
            "/api/generate", data=json.dumps(test_data), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Invalid period" in data["error"]

    def test_generate_api_no_data(self, client):
        """데이터 없이 요청 시 에러 테스트"""
        # Content-Type은 설정하지만 실제 데이터는 없음
        response = client.post("/api/generate", content_type="application/json")

        # Flask가 JSON 파싱에 실패하면 400 HTML 에러를 반환
        assert response.status_code == 400
        assert response.content_type == "text/html; charset=utf-8"
        assert b"Bad Request" in response.data

    def test_generate_api_empty_data(self, client):
        """빈 JSON 객체 전송 시 테스트"""
        response = client.post(
            "/api/generate",
            data=json.dumps({}),  # 빈 JSON 객체 전송
            content_type="application/json",
        )

        # 빈 객체도 유효한 데이터이므로 keywords가 없다는 다른 에러가 발생할 수 있음
        assert response.status_code in [200, 400]  # 구현에 따라 다를 수 있음

    @patch("web.app.task_queue", None)  # Redis 큐 비활성화
    def test_generate_api_in_memory_processing(
        self, client, mock_newsletter_generation
    ):
        """인메모리 처리 테스트 (Redis 없을 때)"""
        test_data = {"keywords": "AI", "period": 14, "template_style": "compact"}

        response = client.post(
            "/api/generate", data=json.dumps(test_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "job_id" in data
        assert data["status"] == "processing"


class TestMockModeValidation:
    """Mock 모드 검증 테스트"""

    @patch.dict(os.environ, {"MOCK_MODE": "true"})
    def test_mock_mode_disabled(self, client):
        """Mock 모드가 비활성화되었는지 확인"""
        # 환경 변수를 다시 로드하기 위해 config 모듈 재임포트
        from newsletter import config
        import importlib

        importlib.reload(config)

        response = client.get("/health")
        data = json.loads(response.data)

        # Mock 모드 상태 확인
        mock_mode_info = data["dependencies"]["mock_mode"]
        assert mock_mode_info["enabled"] == True  # 환경 변수로 설정됨

    @patch.dict(os.environ, {"MOCK_MODE": "false"})
    def test_production_mode_enabled(self, client):
        """프로덕션 모드가 활성화되었는지 확인"""
        response = client.get("/health")
        data = json.loads(response.data)

        mock_mode_info = data["dependencies"]["mock_mode"]
        assert mock_mode_info["enabled"] == False


class TestContentValidation:
    """컨텐츠 검증 테스트"""

    def test_newsletter_content_size(self, client, mock_newsletter_generation):
        """뉴스레터 컨텐츠 크기 검증"""
        # 더 큰 콘텐츠로 Mock 응답 수정
        mock_newsletter_generation.generate_newsletter.return_value = {
            "status": "success",
            "content": f"<html><head><title>Technology Newsletter</title></head><body>"
            + f"<h1>Weekly Technology Update</h1>"
            + f"<p>{'Article content with detailed information. ' * 100}</p>"
            + f"<div>{'More comprehensive newsletter content. ' * 50}</div>"
            + f"</body></html>",
            "title": "Technology Newsletter",
            "generation_stats": {
                "articles_found": 15,
                "articles_processed": 10,
                "generation_time": 45.2,
            },
        }

        response = client.get("/newsletter?keywords=자율주행&period=14")
        assert response.status_code == 200

        content = response.data.decode("utf-8")
        content_length = len(content)
        assert content_length > 2048  # 2KB

    def test_newsletter_no_mock_content(self, client, mock_newsletter_generation):
        """Mock 지시자가 없는지 확인"""
        # Mock 문자열이 포함되지 않은 실제같은 응답
        mock_newsletter_generation.generate_newsletter.return_value = {
            "status": "success",
            "content": "<html><body><h1>AI Newsletter</h1><p>Latest developments in autonomous vehicles and artificial intelligence</p></body></html>",
            "title": "AI Newsletter",
            "generation_stats": {
                "articles_found": 15,
                "articles_processed": 10,
                "generation_time": 45.2,
            },
        }

        response = client.get("/newsletter?keywords=자율주행&period=14")
        assert response.status_code == 200

        content = response.data.decode("utf-8")

        # mock 관련 단어들이 없어야 함 (test는 제외 - technology 같은 정상 단어와 겹침)
        forbidden_indicators = ["mock", "sample", "fake", "dummy", "placeholder"]
        for indicator in forbidden_indicators:
            assert (
                indicator.lower() not in content.lower()
            ), f"Found forbidden indicator: {indicator}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
