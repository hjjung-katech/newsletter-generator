import os

from newsletter.graph import generate_newsletter

# 테스트용 키워드 설정
test_keywords = ["AI반도체", "HBM", "추론칩", "LLM 가속"]

print("=" * 80)
print("실제 뉴스레터 생성 테스트 시작")
print("=" * 80)

print(f"사용할 키워드: {', '.join(test_keywords)}")
print("뉴스 수집 및 처리 시작...")

try:
    # 뉴스레터 생성 (뉴스 2주 이내 소식)
    file_path, error_message = generate_newsletter(test_keywords, news_period_days=14)

    if error_message:
        print(f"오류 발생: {error_message}")
    else:
        print(f"뉴스레터 생성 완료. 저장 경로: {file_path}")

        # 생성된 HTML 파일에서 날짜 정보 확인
        if os.path.exists(file_path):
            import re

            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # 소스 및 날짜 정보 추출
            source_date_pattern = r'<span class="source">\((.*?)\)</span>'
            source_dates = re.findall(source_date_pattern, html_content)

            print("\n== 실제 뉴스레터의 소스 및 날짜 정보 ==")
            if source_dates:
                for idx, source_date in enumerate(
                    source_dates[:15]
                ):  # 처음 15개만 표시
                    print(f"기사 {idx+1}: {source_date}")
                if len(source_dates) > 15:
                    print(f"... 외 {len(source_dates) - 15}개 기사")
            else:
                print("기사가 없거나 소스/날짜 정보를 찾을 수 없습니다.")
except Exception as e:
    print(f"뉴스레터 생성 중 오류 발생: {str(e)}")
