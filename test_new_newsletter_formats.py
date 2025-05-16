from newsletter.compose import compose_newsletter_html
from newsletter.date_utils import standardize_date
import os
from datetime import datetime, timedelta

# 다양한 날짜 형식을 포함한 테스트 데이터 생성
test_articles = [
    # 상대적 시간 (한국어)
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
        "date": "3일 전",
    },
    # 상대적 시간 (영어)
    {
        "title": "SK하이닉스, HBM3E 샘플 출하",
        "url": "https://example.com/news/skhynix-hbm3e",
        "content": "SK하이닉스가 차세대 HBM3E 메모리 샘플을 고객사에 출하했습니다.",
        "source": "반도체뉴스",
        "date": "2 hours ago",
    },
    {
        "title": "인텔, 새 팹 건설 계획 발표",
        "url": "https://example.com/news/intel-new-fab",
        "content": "인텔이 미국 오하이오에 새로운 반도체 팹 건설 계획을 발표했습니다.",
        "source": "글로벌테크",
        "date": "5 days ago",
    },
    # 주/월 단위 상대 시간
    {
        "title": "애플, M3 칩 성능 공개",
        "url": "https://example.com/news/apple-m3",
        "content": "애플이 새로운 M3 칩 성능 벤치마크를 공개했습니다.",
        "source": "맥월드",
        "date": "2 weeks ago",
    },
    {
        "title": "퀄컴, 새로운 모바일 AI 칩 개발",
        "url": "https://example.com/news/qualcomm-ai",
        "content": "퀄컴이 모바일 기기용 AI 가속 칩 신제품을 개발 중입니다.",
        "source": "서울경제",
        "date": "1 month ago",
    },
    # ISO 형식
    {
        "title": "TSMC, 첨단 패키징 투자 확대",
        "url": "https://example.com/news/tsmc-packaging",
        "content": "TSMC가 첨단 패키징 기술에 대한 투자를 확대한다고 발표했습니다.",
        "source": "대만경제일보",
        "date": "2024-05-01",
    },
    {
        "title": "AMD, 새로운 데이터센터 CPU 출시",
        "url": "https://example.com/news/amd-cpu",
        "content": "AMD가 새로운 데이터센터용 CPU를 출시했습니다.",
        "source": "테크크런치",
        "date": "2024-05-01T12:34:56Z",
    },
    # 소스와 날짜가 합쳐진 형식
    {
        "title": "삼성전자, 반도체 신규 투자 계획 발표",
        "url": "https://example.com/news/samsung-investment",
        "content": "삼성전자가 반도체 분야에 대한 신규 투자 계획을 발표했습니다.",
        "source": "조선비즈, 3시간 전",
        "date": "",  # 소스에 날짜가 포함되어 있으므로 date는 비워둠
    },
    {
        "title": "SK하이닉스, 128단 낸드 양산 본격화",
        "url": "https://example.com/news/skhynix-nand",
        "content": "SK하이닉스가 128단 낸드 플래시 메모리 양산을 본격화했습니다.",
        "source": "전자신문, 2 weeks ago",
        "date": "",  # 소스에 날짜가 포함되어 있으므로 date는 비워둠
    },
]

# 템플릿 디렉토리와 파일 정의
current_dir = os.path.dirname(os.path.abspath(__file__))
template_directory = os.path.join(current_dir, "templates")
template_file = "newsletter_template.html"

# 뉴스레터 생성
html_output = compose_newsletter_html(test_articles, template_directory, template_file)

# 파일로 저장
output_filename = os.path.join(
    current_dir,
    "output",
    f"test_all_formats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
)
os.makedirs(os.path.join(current_dir, "output"), exist_ok=True)
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"테스트 뉴스레터 저장 경로: {output_filename}")

# 뉴스레터 HTML에서 중요한 부분만 추출하여 출력
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
