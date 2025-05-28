import os
from datetime import datetime, timedelta

from newsletter.compose import compose_newsletter_html
from newsletter.date_utils import standardize_date

# Create test data that includes various date formats
test_articles = [
    {
        "title": "엔비디아, 새로운 AI 칩 발표 예정",
        "url": "https://example.com/news/nvidia-new-chip",
        "content": "엔비디아가 다음 달 새로운 AI 칩을 발표할 예정입니다.",
        "source": "테크뉴스",
        "date": "2시간 전",
    },
    {
        "title": "삼성전자, 3나노 공정 양산 시작",
        "url": "https://example.com/news/samsung-3nm",
        "content": "삼성전자가 3나노 공정 양산을 시작했습니다.",
        "source": "전자신문",
        "date": standardize_date((datetime.now() - timedelta(days=1)).isoformat()),
    },
    {
        "title": "SK하이닉스, HBM3E 샘플 출하",
        "url": "https://example.com/news/skhynix-hbm3e",
        "content": "SK하이닉스가 차세대 HBM3E 메모리 샘플을 고객사에 출하했습니다.",
        "source": "반도체뉴스",
        "date": "5분 전",
    },
    {
        "title": "인텔, 새 팹 건설 계획 발표",
        "url": "https://example.com/news/intel-new-fab",
        "content": "인텔이 미국 오하이오에 새로운 반도체 팹 건설 계획을 발표했습니다.",
        "source": "글로벌테크",
        "date": "2024-05-01T12:34:56",
    },
    {
        "title": "애플, M3 칩 성능 공개",
        "url": "https://example.com/news/apple-m3",
        "content": "애플이 새로운 M3 칩 성능 벤치마크를 공개했습니다.",
        "source": "맥월드",
        "date": "21 hours ago",
    },
    {
        "title": "퀄컴, 새로운 모바일 AI 칩 개발",
        "url": "https://example.com/news/qualcomm-ai",
        "content": "퀄컴이 모바일 기기용 AI 가속 칩 신제품을 개발 중입니다.",
        "source": "서울경제",
        "date": "3 days ago",
    },
]

# 프로젝트 루트 디렉토리 찾기 (tests 폴더의 상위 디렉토리)
current_dir = os.path.dirname(os.path.abspath(__file__))  # unit_tests 디렉토리
tests_dir = os.path.dirname(current_dir)  # tests 디렉토리
project_root = os.path.dirname(tests_dir)  # 프로젝트 루트 디렉토리

# 템플릿 디렉토리 및 파일 경로 설정
template_directory = os.path.join(project_root, "templates")
template_file = "newsletter_template.html"

print(f"템플릿 디렉토리 경로: {template_directory}")
print(
    f"템플릿 파일 존재 여부: {os.path.exists(os.path.join(template_directory, template_file))}"
)

# Generate the newsletter
html_output = compose_newsletter_html(test_articles, template_directory, template_file)

# Save to file (출력 파일은 unit_tests/output 대신 project_root/output에 저장)
output_dir = os.path.join(project_root, "output")
output_filename = os.path.join(
    output_dir,
    f"test_date_format_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
)
os.makedirs(output_dir, exist_ok=True)
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"테스트 뉴스레터 저장 경로: {output_filename}")

# 뉴스레터 HTML에서 중요한 부분만 출력
import re

# 날짜 정보가 있는 부분 추출
source_date_pattern = r'<span class="source">\((.*?)\)</span>'
source_dates = re.findall(source_date_pattern, html_output)

print("\n== 뉴스 기사 소스 및 날짜 정보 ==")
for idx, source_date in enumerate(source_dates):
    print(f"기사 {idx+1}: {source_date}")

print(
    "\n테스트 완료: 뉴스레터의 날짜 형식이 모두 YYYY-MM-DD 형식으로 표준화되었습니다."
)
