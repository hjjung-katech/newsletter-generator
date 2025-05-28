import unittest
from unittest.mock import patch, MagicMock
import json
import os


class TestScrapeDates(unittest.TestCase):
    def setUp(self):
        """테스트 설정"""
        print("=" * 80)
        print("뉴스 스크래핑 단계 테스트")
        print("=" * 80)

    @patch("newsletter.sources.console")
    def test_scrape_dates_functionality(self, mock_console):
        """뉴스 스크래핑 날짜 기능 테스트"""
        # Mock console to prevent AttributeError
        mock_console.print = MagicMock()

        from newsletter.sources import SerperAPISource, NewsSourceManager
        from newsletter.date_utils import standardize_date, format_date_for_display

        # 테스트용 키워드
        test_keywords = ["AI반도체", "HBM"]

        # 뉴스 소스 매니저 설정
        source_manager = NewsSourceManager()

        # Mock the SerperAPISource to avoid actual API calls
        mock_serper_source = MagicMock()
        mock_serper_source.get_source_name.return_value = "MockSerperAPI"
        mock_serper_source.fetch_news.return_value = [
            {
                "title": "Test Article 1",
                "url": "http://test1.com",
                "content": "Test content about AI반도체",
                "source": "Test Source",
                "date": "2024-01-01",
                "original_date": "1일 전",
            },
            {
                "title": "Test Article 2",
                "url": "http://test2.com",
                "content": "Test content about HBM",
                "source": "Test Source",
                "date": "2024-01-02",
                "original_date": "2 hours ago",
            },
        ]

        source_manager.add_source(mock_serper_source)

        # 뉴스 기사 수집
        print(f"키워드 '{', '.join(test_keywords)}'로 뉴스 기사 수집 중...")
        articles = source_manager.fetch_all_sources(
            test_keywords, num_results_per_source=3
        )
        print(f"총 {len(articles)}개 기사 수집 완료\n")

        # 프로젝트 루트 디렉토리 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))  # unit_tests 디렉토리
        tests_dir = os.path.dirname(current_dir)  # tests 디렉토리
        project_root = os.path.dirname(tests_dir)  # 프로젝트 루트 디렉토리

        # 출력 디렉토리 생성
        output_dir = os.path.join(project_root, "output", "test_results")
        os.makedirs(output_dir, exist_ok=True)

        # 결과 저장할 파일 경로
        output_file = os.path.join(output_dir, "scrape_test_results.json")

        # 날짜 정보 테스트
        print("== 수집된 기사의 날짜 정보 분석 ==")
        date_formats = {}
        for idx, article in enumerate(articles[:10]):  # 처음 10개만 표시
            title = article.get("title", "제목 없음")
            original_date = article.get("original_date", "날짜 정보 없음")
            date = article.get("date", "")

            # 날짜 형식 분류
            date_format = "알 수 없음"
            if "시간 전" in str(original_date):
                date_format = "상대적 시간 (한국어)"
            elif "hours ago" in str(original_date):
                date_format = "상대적 시간 (영어)"
            elif "days ago" in str(original_date):
                date_format = "상대적 시간 (영어)"
            elif "weeks ago" in str(original_date):
                date_format = "상대적 시간 (영어)"
            elif "months ago" in str(original_date):
                date_format = "상대적 시간 (영어)"
            elif "-" in str(original_date) and len(str(original_date).split("-")) == 3:
                date_format = "ISO 형식"

            if date_format not in date_formats:
                date_formats[date_format] = 0
            date_formats[date_format] += 1

            # 날짜 정보 출력
            formatted_date = (
                format_date_for_display(date_str=date) if date else "날짜 없음"
            )

            print(f"\n기사 {idx+1}: {title}")
            print(f"  원본 날짜: {original_date}")
            print(f"  표준화된 날짜: {date}")
            print(f"  표시용 날짜: {formatted_date}")
            print(f"  날짜 형식: {date_format}")

        # 전체 날짜 형식 분포 출력
        print("\n== 수집된 기사의 날짜 형식 분포 ==")
        for format_type, count in date_formats.items():
            print(f"{format_type}: {count}개")

        # 결과 저장
        result_data = {
            "articles": [
                {
                    "title": article.get("title", "제목 없음"),
                    "original_date": article.get("original_date", "날짜 정보 없음"),
                    "standardized_date": article.get("date", ""),
                    "display_date": (
                        format_date_for_display(date_str=article.get("date", ""))
                        if article.get("date", "")
                        else "날짜 없음"
                    ),
                }
                for article in articles
            ],
            "date_formats": date_formats,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"\n테스트 결과 저장 완료: {output_file}")
        print("테스트 완료")

        # 테스트 검증
        self.assertGreater(len(articles), 0, "기사가 수집되어야 합니다")
        self.assertTrue(os.path.exists(output_file), "결과 파일이 생성되어야 합니다")

        # Mock이 호출되었는지 확인
        mock_console.print.assert_called()


if __name__ == "__main__":
    unittest.main()
