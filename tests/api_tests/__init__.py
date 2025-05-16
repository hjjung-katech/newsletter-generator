# API 테스트 패키지
# API 키가 필요한 테스트를 포함합니다.
"""
뉴스레터 제너레이터 API 테스트 패키지

이 패키지는 외부 API 키가 필요한 기능 테스트를 포함합니다.
테스트를 실행하기 위해서는 다음 API 키들이 필요할 수 있습니다:
- SERPER_API_KEY: Serper.dev API 접근용 (대부분의 테스트에 필요)
- GEMINI_API_KEY: 요약 및 키워드 생성용
- NAVER_CLIENT_ID, NAVER_CLIENT_SECRET: 네이버 뉴스 API용

주요 테스트 파일:
- test_collect.py: 기사 수집 기능 테스트
- test_serper_direct.py: Serper API 직접 통신 테스트
- test_sources.py: 다양한 뉴스 소스 테스트
- test_summarize.py: AI를 활용한 기사 요약 테스트
- test_article_filter_integration.py: 필터링 기능 통합 테스트
- test_news_integration_enhanced.py: 향상된 뉴스 수집 통합 테스트
- test_improved_search.py, test_search_improved.py: 향상된 검색 기능 테스트

전체 API 테스트 실행:
python run_tests.py --api
"""
