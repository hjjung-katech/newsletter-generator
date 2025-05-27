#!/usr/bin/env python3
"""
LLM 시스템 기본 테스트
"""
import sys
import os
import pytest

# 모듈 경로 추가 (루트 디렉토리 기준)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from newsletter.llm_factory import (
    get_available_providers,
    get_provider_info,
    get_llm_for_task,
)
from newsletter import config


class TestLLMSystem:
    """LLM 시스템 기본 테스트 클래스"""

    def test_api_keys_configuration(self):
        """API 키 설정 상태를 테스트합니다."""
        print("\n=== API 키 상태 테스트 ===")

        # Gemini는 필수이므로 반드시 설정되어야 함
        assert config.GEMINI_API_KEY is not None, "GEMINI_API_KEY는 필수입니다"
        print(f"✅ GEMINI_API_KEY: 설정됨")

        # 다른 API 키들은 선택사항이지만 상태 확인
        openai_status = "설정됨" if config.OPENAI_API_KEY else "미설정"
        anthropic_status = "설정됨" if config.ANTHROPIC_API_KEY else "미설정"

        print(f"🔧 OPENAI_API_KEY: {openai_status}")
        print(f"🔧 ANTHROPIC_API_KEY: {anthropic_status}")

    def test_provider_availability(self):
        """LLM 제공자 사용 가능 여부를 테스트합니다."""
        print("\n=== 제공자 사용 가능 여부 테스트 ===")

        available_providers = get_available_providers()

        # 최소한 하나의 제공자는 사용 가능해야 함
        assert len(available_providers) > 0, "사용 가능한 LLM 제공자가 없습니다"

        # Gemini는 반드시 사용 가능해야 함
        assert "gemini" in available_providers, "Gemini 제공자가 사용 불가능합니다"

        print(f"✅ 사용 가능한 제공자: {available_providers}")

        # 제공자별 상세 정보 확인
        provider_info = get_provider_info()
        for provider, info in provider_info.items():
            status = "✅" if info["available"] else "❌"
            print(f"{status} {provider.upper()}: 사용 가능 = {info['available']}")

    def test_llm_config_validation(self):
        """LLM 설정 구조를 검증합니다."""
        print("\n=== LLM 설정 구조 테스트 ===")

        # 기본 설정 확인
        assert "default_provider" in config.LLM_CONFIG, "기본 제공자 설정이 없습니다"
        default_provider = config.LLM_CONFIG["default_provider"]
        print(f"✅ 기본 제공자: {default_provider}")

        # 모델 설정 확인
        assert "models" in config.LLM_CONFIG, "모델 설정이 없습니다"
        models = config.LLM_CONFIG["models"]

        # 필수 작업들이 설정되어 있는지 확인
        required_tasks = [
            "keyword_generation",
            "theme_extraction",
            "news_summarization",
            "html_generation",
        ]

        for task in required_tasks:
            assert task in models, f"필수 작업 '{task}' 설정이 없습니다"
            task_config = models[task]
            assert "provider" in task_config, f"작업 '{task}'에 제공자 설정이 없습니다"
            assert "model" in task_config, f"작업 '{task}'에 모델 설정이 없습니다"
            print(f"✅ {task}: {task_config['provider']} / {task_config['model']}")

    def test_llm_instance_creation(self):
        """LLM 인스턴스 생성을 테스트합니다."""
        print("\n=== LLM 인스턴스 생성 테스트 ===")

        # 여러 작업에 대해 LLM 생성 테스트
        test_tasks = ["theme_extraction", "news_summarization", "html_generation"]

        for task in test_tasks:
            try:
                llm = get_llm_for_task(task)
                assert llm is not None, f"작업 '{task}'에 대한 LLM 생성 실패"
                print(f"✅ {task}: {type(llm).__name__} 생성 성공")
            except Exception as e:
                pytest.fail(f"작업 '{task}'에 대한 LLM 생성 중 오류: {e}")

    def test_fallback_mechanism(self):
        """Fallback 메커니즘을 테스트합니다."""
        print("\n=== Fallback 메커니즘 테스트 ===")

        # 존재하지 않는 작업에 대한 기본 LLM 생성 테스트
        try:
            llm = get_llm_for_task("nonexistent_task")
            assert llm is not None, "Fallback LLM 생성 실패"
            print(f"✅ Fallback 테스트: {type(llm).__name__} 생성 성공")
        except Exception as e:
            pytest.fail(f"Fallback 메커니즘 테스트 중 오류: {e}")


def test_suite_runner():
    """테스트 스위트를 직접 실행하는 함수"""
    print("=== LLM 시스템 테스트 스위트 ===")
    print(f"현재 디렉토리: {os.getcwd()}")

    test_instance = TestLLMSystem()

    try:
        test_instance.test_api_keys_configuration()
        test_instance.test_provider_availability()
        test_instance.test_llm_config_validation()
        test_instance.test_llm_instance_creation()
        test_instance.test_fallback_mechanism()

        print("\n🎉 모든 기본 테스트 통과!")
        return True

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 직접 실행 시 테스트 수행
    test_suite_runner()
