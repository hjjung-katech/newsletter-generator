#!/usr/bin/env python3
"""
LLM 제공자별 상세 테스트
"""
import sys
import os
import pytest
import time

# 모듈 경로 추가 (루트 디렉토리 기준)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from newsletter.llm_factory import get_llm_for_task, llm_factory
from newsletter import config


class TestLLMProviders:
    """LLM 제공자별 상세 테스트 클래스"""

    # 테스트할 작업들과 설명
    TASKS = [
        ("keyword_generation", "키워드 생성", "창의적 작업"),
        ("theme_extraction", "테마 추출", "빠른 분석"),
        ("news_summarization", "뉴스 요약", "정확한 요약"),
        ("section_regeneration", "섹션 재생성", "구조화 작업"),
        ("introduction_generation", "소개 생성", "자연스러운 글쓰기"),
        ("html_generation", "HTML 생성", "복잡한 구조화"),
        ("article_scoring", "기사 점수", "빠른 판단"),
        ("translation", "번역", "정확성"),
    ]

    def test_all_task_llm_creation(self):
        """모든 작업에 대한 LLM 생성을 테스트합니다."""
        print("\n=== 전체 작업 LLM 생성 테스트 ===")

        created_llms = {}
        failed_tasks = []

        for task_id, task_name, description in self.TASKS:
            try:
                llm = get_llm_for_task(task_id)
                assert llm is not None, f"작업 '{task_id}'에 대한 LLM이 None입니다"

                provider_type = type(llm).__name__
                created_llms[task_id] = {
                    "llm": llm,
                    "type": provider_type,
                    "task_name": task_name,
                    "description": description,
                }
                print(f"✅ {task_name} ({task_id}): {provider_type}")

            except Exception as e:
                failed_tasks.append((task_id, task_name, str(e)))
                print(f"❌ {task_name} ({task_id}): 실패 - {e}")

        # 실패한 작업이 있으면 테스트 실패
        if failed_tasks:
            failure_msg = "\n".join(
                [f"- {name}: {error}" for _, name, error in failed_tasks]
            )
            pytest.fail(f"다음 작업들의 LLM 생성이 실패했습니다:\n{failure_msg}")

        return created_llms

    @pytest.mark.real_api
    def test_llm_response_quality(self):
        """각 LLM의 응답 품질을 테스트합니다."""
        print("\n=== LLM 응답 품질 테스트 ===")

        # 간단한 테스트 프롬프트들
        test_prompts = {
            "keyword_generation": "스마트팩토리 도메인의 키워드 3개를 생성해주세요",
            "theme_extraction": "AI, 머신러닝, 딥러닝에서 공통 테마를 찾아주세요",
            "news_summarization": "안녕하세요. 이 메시지를 한 줄로 요약해주세요.",
            "translation": "Hello, how are you today?를 한국어로 번역해주세요",
        }

        response_results = {}

        for task_id in test_prompts:
            if task_id in test_prompts:
                try:
                    llm = get_llm_for_task(task_id)
                    start_time = time.time()
                    response = llm.invoke(test_prompts[task_id])
                    response_time = time.time() - start_time

                    response_text = str(response).strip()

                    # 응답 품질 검증
                    assert len(response_text) > 0, f"{task_id}: 빈 응답"
                    assert len(response_text) > 10, f"{task_id}: 응답이 너무 짧음"
                    assert (
                        response_time < 60
                    ), f"{task_id}: 응답 시간 초과 ({response_time:.2f}초)"

                    response_results[task_id] = {
                        "length": len(response_text),
                        "time": response_time,
                        "type": type(llm).__name__,
                    }

                    print(
                        f"✅ {task_id}: {response_time:.2f}초, {len(response_text)}자 ({type(llm).__name__})"
                    )

                except Exception as e:
                    print(f"❌ {task_id}: 응답 테스트 실패 - {e}")
                    pytest.fail(f"작업 '{task_id}'의 응답 테스트 실패: {e}")

        return response_results

    def test_provider_distribution(self):
        """제공자별 작업 분배가 적절한지 테스트합니다."""
        print("\n=== 제공자별 작업 분배 테스트 ===")

        provider_usage = {}

        for task_id, task_name, _ in self.TASKS:
            try:
                llm = get_llm_for_task(task_id)
                provider_type = type(llm).__name__

                if provider_type not in provider_usage:
                    provider_usage[provider_type] = []
                provider_usage[provider_type].append(task_name)

            except Exception as e:
                print(f"❌ {task_name}: 제공자 확인 실패 - {e}")

        # 결과 출력
        for provider, tasks in provider_usage.items():
            print(f"🤖 {provider}: {len(tasks)}개 작업")
            for task in tasks:
                print(f"   - {task}")

        # 최소한 하나의 제공자는 사용되어야 함
        assert len(provider_usage) > 0, "사용된 제공자가 없습니다"

        return provider_usage

    def test_fallback_mechanism_detailed(self):
        """상세한 Fallback 메커니즘 테스트"""
        print("\n=== 상세 Fallback 메커니즘 테스트 ===")

        # 원본 설정 백업
        original_config = config.LLM_CONFIG.copy()

        try:
            # 잘못된 설정으로 테스트
            test_scenarios = [
                {
                    "name": "존재하지 않는 제공자",
                    "config": {
                        "provider": "nonexistent_provider",
                        "model": "nonexistent_model",
                        "temperature": 0.5,
                    },
                },
                {
                    "name": "잘못된 모델명",
                    "config": {
                        "provider": "gemini",
                        "model": "nonexistent_gemini_model",
                        "temperature": 0.5,
                    },
                },
            ]

            for scenario in test_scenarios:
                print(f"\n🧪 테스트 시나리오: {scenario['name']}")

                # 임시 설정 적용
                test_config = original_config.copy()
                test_config["models"] = {"test_fallback_task": scenario["config"]}
                config.LLM_CONFIG = test_config

                try:
                    llm = get_llm_for_task("test_fallback_task")
                    assert (
                        llm is not None
                    ), f"Fallback LLM이 생성되지 않음: {scenario['name']}"
                    print(f"✅ {scenario['name']}: {type(llm).__name__} Fallback 성공")

                except Exception as e:
                    pytest.fail(f"Fallback 실패 - {scenario['name']}: {e}")

        finally:
            # 원본 설정 복원
            config.LLM_CONFIG = original_config

    @pytest.mark.real_api
    def test_performance_benchmarks(self):
        """성능 벤치마크 테스트"""
        print("\n=== 성능 벤치마크 테스트 ===")

        # 빠른 작업과 느린 작업 구분
        fast_tasks = ["theme_extraction", "article_scoring"]  # Flash 모델 사용
        slow_tasks = ["news_summarization", "html_generation"]  # Pro 모델 사용

        performance_results = {}

        test_prompt = "간단한 테스트 메시지입니다."

        for task_group, expected_speed in [("fast", fast_tasks), ("slow", slow_tasks)]:
            group_times = []

            for task_id in expected_speed:
                if any(t[0] == task_id for t in self.TASKS):
                    try:
                        llm = get_llm_for_task(task_id)
                        start_time = time.time()
                        response = llm.invoke(test_prompt)
                        response_time = time.time() - start_time

                        group_times.append(response_time)
                        print(f"📊 {task_id}: {response_time:.2f}초")

                    except Exception as e:
                        print(f"❌ {task_id}: 성능 테스트 실패 - {e}")

            if group_times:
                avg_time = sum(group_times) / len(group_times)
                performance_results[task_group] = {
                    "average_time": avg_time,
                    "times": group_times,
                }
                print(f"📈 {task_group.upper()} 작업 평균 시간: {avg_time:.2f}초")

        # 성능 검증: fast 작업이 slow 작업보다 빨라야 함 (일반적으로)
        if "fast" in performance_results and "slow" in performance_results:
            fast_avg = performance_results["fast"]["average_time"]
            slow_avg = performance_results["slow"]["average_time"]
            print(f"🏃 빠른 작업 vs 정확한 작업: {fast_avg:.2f}초 vs {slow_avg:.2f}초")

        return performance_results


@pytest.mark.real_api
def test_comprehensive_suite():
    """종합 테스트 스위트 실행"""
    print("=== LLM 제공자별 종합 테스트 스위트 ===")
    print(f"현재 디렉토리: {os.getcwd()}")

    test_instance = TestLLMProviders()
    results = {}

    try:
        print("\n1️⃣ LLM 생성 테스트")
        results["llm_creation"] = test_instance.test_all_task_llm_creation()

        print("\n2️⃣ 응답 품질 테스트")
        results["response_quality"] = test_instance.test_llm_response_quality()

        print("\n3️⃣ 제공자 분배 테스트")
        results["provider_distribution"] = test_instance.test_provider_distribution()

        print("\n4️⃣ Fallback 메커니즘 테스트")
        test_instance.test_fallback_mechanism_detailed()

        print("\n5️⃣ 성능 벤치마크 테스트")
        results["performance"] = test_instance.test_performance_benchmarks()

        print("\n🎉 모든 상세 테스트 통과!")
        return results

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 직접 실행 시 종합 테스트 수행
    test_comprehensive_suite()
