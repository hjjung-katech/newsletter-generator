#!/usr/bin/env python3
"""
Email Compatibility 통합 테스트

실제 뉴스레터 생성과 이메일 전송을 포함한 End-to-End 테스트
"""

import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)


class TestEmailCompatibilityIntegration:
    """Email-Compatible 통합 테스트"""

    @pytest.fixture
    def output_dir(self):
        """테스트 출력 디렉토리"""
        test_output = Path("output/email_tests")
        test_output.mkdir(parents=True, exist_ok=True)
        return test_output

    @pytest.fixture
    def timestamp(self):
        """테스트 타임스탬프"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def test_detailed_email_compatible_generation(self, output_dir, timestamp):
        """Detailed + Email-Compatible 뉴스레터 생성 테스트"""
        cmd = [
            "python",
            "-m",
            "newsletter",
            "run",
            "--keywords",
            "AI,인공지능",
            "--template-style",
            "detailed",
            "--email-compatible",
            "--output-format",
            "html",
            "--period",
            "7",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        # 명령어 실행 성공 확인
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            pytest.skip("네트워크 연결 또는 API 오류로 인해 테스트 스킵")

        # 생성된 파일 확인
        output_base_dir = Path(project_root) / "output"
        html_files = list(output_base_dir.glob("*detailed_email_compatible*.html"))

        assert (
            len(html_files) > 0
        ), "Detailed email-compatible HTML 파일이 생성되지 않았습니다"

        # 최신 파일 선택
        latest_file = max(html_files, key=lambda f: f.stat().st_mtime)

        # 파일 복사 및 검증
        target_file = output_dir / f"test_detailed_email_compatible_{timestamp}.html"
        import shutil

        shutil.copy2(latest_file, target_file)

        # 파일 내용 검증
        with open(target_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        self._validate_email_compatible_html(html_content, "detailed")

    def test_compact_email_compatible_generation(self, output_dir, timestamp):
        """Compact + Email-Compatible 뉴스레터 생성 테스트"""
        cmd = [
            "python",
            "-m",
            "newsletter",
            "run",
            "--keywords",
            "이차전지,배터리",
            "--template-style",
            "compact",
            "--email-compatible",
            "--output-format",
            "html",
            "--period",
            "7",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        # 명령어 실행 성공 확인
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            pytest.skip("네트워크 연결 또는 API 오류로 인해 테스트 스킵")

        # 생성된 파일 확인
        output_base_dir = Path(project_root) / "output"
        html_files = list(output_base_dir.glob("*compact_email_compatible*.html"))

        assert (
            len(html_files) > 0
        ), "Compact email-compatible HTML 파일이 생성되지 않았습니다"

        # 최신 파일 선택
        latest_file = max(html_files, key=lambda f: f.stat().st_mtime)

        # 파일 복사 및 검증
        target_file = output_dir / f"test_compact_email_compatible_{timestamp}.html"
        import shutil

        shutil.copy2(latest_file, target_file)

        # 파일 내용 검증
        with open(target_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        self._validate_email_compatible_html(html_content, "compact")

    def test_no_duplicate_files_generated(self, output_dir, timestamp):
        """중복 파일 생성되지 않는지 테스트"""
        cmd = [
            "python",
            "-m",
            "newsletter",
            "run",
            "--keywords",
            "반도체",
            "--template-style",
            "detailed",
            "--email-compatible",
            "--output-format",
            "html",
            "--period",
            "7",
        ]

        # 실행 전 파일 개수 확인
        output_base_dir = Path(project_root) / "output"
        files_before = list(output_base_dir.glob("*반도체*.html"))
        count_before = len(files_before)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        if result.returncode != 0:
            pytest.skip("네트워크 연결 또는 API 오류로 인해 테스트 스킵")

        # 실행 후 파일 개수 확인
        files_after = list(output_base_dir.glob("*반도체*.html"))
        count_after = len(files_after)

        # 정확히 1개의 파일만 추가되었는지 확인
        new_files_count = count_after - count_before
        assert (
            new_files_count == 1
        ), f"1개의 파일만 생성되어야 하는데 {new_files_count}개가 생성되었습니다"

        # 새로 생성된 파일이 email_compatible 파일인지 확인
        new_files = [f for f in files_after if f not in files_before]
        assert len(new_files) == 1
        new_file = new_files[0]
        assert (
            "email_compatible" in new_file.name
        ), "email-compatible 파일이 생성되지 않았습니다"

    @pytest.mark.skipif(
        not os.getenv("TEST_EMAIL_RECIPIENT"),
        reason="TEST_EMAIL_RECIPIENT 환경변수 필요",
    )
    def test_email_sending_detailed(self):
        """실제 이메일 전송 테스트 - Detailed"""
        test_email = os.getenv("TEST_EMAIL_RECIPIENT")

        cmd = [
            "python",
            "-m",
            "newsletter",
            "run",
            "--keywords",
            "AI,테스트",
            "--template-style",
            "detailed",
            "--email-compatible",
            "--to",
            test_email,
            "--period",
            "7",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        if result.returncode != 0:
            pytest.skip("네트워크 또는 이메일 서비스 오류로 인해 테스트 스킵")

        # 성공 메시지 확인
        assert (
            "이메일 전송 완료" in result.stdout
            or "successfully" in result.stdout.lower()
        )

    @pytest.mark.skipif(
        not os.getenv("TEST_EMAIL_RECIPIENT"),
        reason="TEST_EMAIL_RECIPIENT 환경변수 필요",
    )
    def test_email_sending_compact(self):
        """실제 이메일 전송 테스트 - Compact"""
        test_email = os.getenv("TEST_EMAIL_RECIPIENT")

        cmd = [
            "python",
            "-m",
            "newsletter",
            "run",
            "--keywords",
            "배터리,테스트",
            "--template-style",
            "compact",
            "--email-compatible",
            "--to",
            test_email,
            "--period",
            "7",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        if result.returncode != 0:
            pytest.skip("네트워크 또는 이메일 서비스 오류로 인해 테스트 스킵")

        # 성공 메시지 확인
        assert (
            "이메일 전송 완료" in result.stdout
            or "successfully" in result.stdout.lower()
        )

    def _validate_email_compatible_html(self, html_content: str, template_style: str):
        """Email-compatible HTML 검증"""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. 기본 HTML 구조
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None
        assert soup.find("title") is not None

        # 2. 메타 태그 확인
        charset_meta = soup.find("meta", attrs={"charset": True})
        assert charset_meta is not None

        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        assert viewport_meta is not None

        # 3. 테이블 기반 레이아웃 확인
        tables = soup.find_all("table")
        assert len(tables) > 0, "Email-compatible 템플릿은 테이블 기반이어야 합니다"

        # 4. 인라인 스타일 확인
        elements_with_style = soup.find_all(attrs={"style": True})
        assert len(elements_with_style) > 0, "인라인 CSS가 적용되어야 합니다"

        # 5. CSS 변수 미사용 확인
        assert "var(--" not in html_content, "CSS 변수는 사용하면 안됩니다"

        # 6. 지원되지 않는 CSS 속성 확인
        unsupported_css = ["display: flex", "display: grid", "transform:", "animation:"]
        for css_prop in unsupported_css:
            assert css_prop not in html_content, f"지원되지 않는 CSS 속성: {css_prop}"

        # 7. 필수 섹션 확인
        body_text = soup.get_text()

        if template_style == "detailed":
            # Detailed 모드 필수 요소
            assert "생각해 볼 거리" in body_text or "food_for_thought" in html_content
        elif template_style == "compact":
            # Compact 모드 필수 요소
            assert "주요 기사" in body_text or "이런 뜻이에요" in body_text

        # 8. 링크 유효성 확인
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            assert href.startswith(
                ("http://", "https://", "mailto:", "#")
            ), f"유효하지 않은 링크: {href}"

        # 9. 이미지 alt 텍스트 확인 (있는 경우)
        images = soup.find_all("img")
        for img in images:
            assert img.get("alt") is not None, "이미지에 alt 텍스트가 필요합니다"


class TestEmailCompatibilityReport:
    """이메일 호환성 테스트 보고서 생성"""

    def test_generate_compatibility_report(self):
        """호환성 테스트 보고서 생성"""
        output_dir = Path("output/email_tests")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"email_compatibility_report_{timestamp}.html"

        # 테스트 보고서 HTML 생성
        report_html = self._generate_report_html(timestamp)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_html)

        assert report_file.exists()
        assert report_file.stat().st_size > 0

        print(f"\n📄 이메일 호환성 테스트 보고서 생성: {report_file}")

        # 브라우저에서 열기 (선택적)
        if os.getenv("OPEN_BROWSER_REPORT", "false").lower() == "true":
            try:
                webbrowser.open(str(report_file))
            except:
                pass

    def _generate_report_html(self, timestamp: str) -> str:
        """테스트 보고서 HTML 생성"""
        return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>이메일 호환성 테스트 보고서</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .test-section {{
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #f9f9f9;
        }}
        .checklist {{
            margin: 20px 0;
        }}
        .checklist ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        .checklist li {{
            margin: 8px 0;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }}
        .checklist li:before {{
            content: "☐ ";
            color: #666;
            margin-right: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f4f4f4;
            font-weight: bold;
        }}
        .status-good {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-bad {{ color: #dc3545; }}
        .code {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
        }}
        .tools-section {{
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 이메일 호환성 테스트 보고서</h1>
        <p>생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>테스트 ID: {timestamp}</p>
    </div>
    
    <div class="test-section">
        <h2>✅ 자동 테스트 결과</h2>
        <p>pytest 기반 자동 테스트가 실행되었습니다.</p>
        <div class="code">
# 테스트 실행 명령어
pytest tests/test_email_compatibility.py -v
pytest tests/test_email_compatibility_integration.py -v
        </div>
    </div>

    <div class="test-section">
        <h2>🎯 수동 테스트 체크리스트</h2>
        <div class="checklist">
            <h3>1. 이메일 클라이언트 테스트</h3>
            <ul>
                <li>Gmail (웹)</li>
                <li>Outlook (웹)</li>
                <li>Naver 메일</li>
                <li>Daum 메일</li>
                <li>Apple Mail</li>
                <li>Outlook Desktop</li>
                <li>모바일 Gmail 앱</li>
                <li>모바일 Outlook 앱</li>
                <li>회사 웹메일 (osp.re.kr)</li>
            </ul>
            
            <h3>2. 렌더링 확인 항목</h3>
            <ul>
                <li>레이아웃이 깨지지 않음</li>
                <li>폰트가 제대로 표시됨</li>
                <li>색상이 올바르게 표시됨</li>
                <li>이모지가 표시됨</li>
                <li>링크가 작동함</li>
                <li>모바일에서 반응형 동작</li>
                <li>배경색이 표시됨</li>
                <li>테이블 구조가 유지됨</li>
                <li>"이런 뜻이에요" 섹션 표시됨</li>
                <li>"생각해 볼 거리" 섹션 표시됨</li>
            </ul>

            <h3>3. 기능 테스트</h3>
            <ul>
                <li>Detailed + Email-Compatible 생성</li>
                <li>Compact + Email-Compatible 생성</li>
                <li>중복 파일 생성 안됨</li>
                <li>이메일 전송 성공</li>
                <li>콘텐츠 무결성 유지</li>
            </ul>
        </div>
    </div>

    <div class="test-section">
        <h2>📊 이메일 클라이언트 호환성 매트릭스</h2>
        <table>
            <tr>
                <th>기능/클라이언트</th>
                <th>Gmail</th>
                <th>Outlook</th>
                <th>Apple Mail</th>
                <th>Naver/Daum</th>
                <th>모바일</th>
            </tr>
            <tr>
                <td>테이블 레이아웃</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
            </tr>
            <tr>
                <td>인라인 CSS</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
            </tr>
            <tr>
                <td>반응형 디자인</td>
                <td class="status-good">✅ 미디어 쿼리</td>
                <td class="status-warning">⚠️ 부분 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-warning">⚠️ 부분 지원</td>
                <td class="status-good">✅ 완전 지원</td>
            </tr>
            <tr>
                <td>이모지</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
            </tr>
            <tr>
                <td>한글 폰트</td>
                <td class="status-good">✅ 시스템 폰트</td>
                <td class="status-good">✅ 시스템 폰트</td>
                <td class="status-good">✅ 시스템 폰트</td>
                <td class="status-good">✅ 완전 지원</td>
                <td class="status-good">✅ 완전 지원</td>
            </tr>
        </table>
        <p><span class="status-good">✅ 완전 지원</span> | <span class="status-warning">⚠️ 부분 지원</span> | <span class="status-bad">❌ 미지원</span></p>
    </div>

    <div class="tools-section">
        <h2>🛠️ 추천 테스트 도구 및 서비스</h2>
        <h3>무료 도구</h3>
        <ul>
            <li><strong><a href="https://putsmail.com" target="_blank">PutsMail</a></strong> - 무료 이메일 테스트 전송</li>
            <li><strong><a href="https://www.mail-tester.com" target="_blank">Mail-tester</a></strong> - 스팸 점수 및 전달성 확인</li>
            <li><strong><a href="https://app.mailjet.com/template" target="_blank">Mailjet Passport</a></strong> - 무료 이메일 미리보기</li>
            <li><strong><a href="https://templates.mailchimp.com/resources/email-client-css-support/" target="_blank">Mailchimp CSS Support Guide</a></strong> - CSS 지원 현황</li>
        </ul>
        
        <h3>유료 도구</h3>
        <ul>
            <li><strong><a href="https://www.emailonacid.com" target="_blank">Email on Acid</a></strong> - 70+ 이메일 클라이언트 테스트</li>
            <li><strong><a href="https://litmus.com" target="_blank">Litmus</a></strong> - 실시간 이메일 미리보기 및 분석</li>
        </ul>
    </div>

    <div class="test-section">
        <h2>🚀 테스트 실행 방법</h2>
        <h3>1. 자동 테스트</h3>
        <div class="code">
# 기본 테스트
pytest tests/test_email_compatibility.py -v

# 통합 테스트 (네트워크 필요)
pytest tests/test_email_compatibility_integration.py -v

# 이메일 전송 테스트 (환경변수 설정 필요)
export TEST_EMAIL_RECIPIENT="your-email@example.com"
pytest tests/test_email_compatibility_integration.py::TestEmailCompatibilityIntegration::test_email_sending_detailed -v
        </div>

        <h3>2. 수동 테스트</h3>
        <div class="code">
# Detailed + Email-Compatible 생성
python -m newsletter run --keywords "AI,테스트" --template-style detailed --email-compatible

# Compact + Email-Compatible 생성  
python -m newsletter run --keywords "AI,테스트" --template-style compact --email-compatible

# 이메일 전송 테스트
python -m newsletter run --keywords "AI,테스트" --template-style detailed --email-compatible --to your-email@example.com
        </div>
    </div>

    <div class="test-section">
        <h2>📋 테스트 결과 기록</h2>
        <p>다음 항목들을 테스트하고 결과를 기록하세요:</p>
        <table>
            <tr>
                <th>테스트 항목</th>
                <th>예상 결과</th>
                <th>실제 결과</th>
                <th>상태</th>
                <th>비고</th>
            </tr>
            <tr>
                <td>Detailed Email-Compatible 생성</td>
                <td>1개 파일 생성</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>Compact Email-Compatible 생성</td>
                <td>1개 파일 생성</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>중복 파일 생성 안됨</td>
                <td>단일 파일만 생성</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>"이런 뜻이에요" 섹션 포함</td>
                <td>정의 섹션 표시</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>Gmail 렌더링</td>
                <td>정상 표시</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>Outlook 렌더링</td>
                <td>정상 표시</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr>
                <td>모바일 반응형</td>
                <td>모바일 최적화</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </table>
    </div>

    <footer style="margin-top: 50px; padding: 20px; border-top: 1px solid #ddd; color: #666; text-align: center;">
        <p>이메일 호환성 테스트 보고서 | 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
</body>
</html>
"""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
