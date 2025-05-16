# 단위 테스트 패키지
# API 연결이 필요하지 않은 테스트를 포함합니다.
"""
뉴스레터 제너레이터 단위 테스트 패키지

이 패키지는 외부 API 연결이나 인터넷 접속이 필요 없는 독립적인 단위 테스트들을 포함합니다.
주로 다음과 같은 기능들에 대한 테스트를 포함합니다:
- 날짜 처리 유틸리티 (test_date_utils.py, test_weeks_ago.py)
- 뉴스레터 생성 기능 (test_new_newsletter.py, test_new_newsletter_with_weeks.py)
- 날짜 스크래핑 (test_scrape_dates.py)
- 실제 뉴스레터 시나리오 (test_real_newsletter.py)

전체 테스트 실행:
python run_tests.py --unit
"""
