#!/usr/bin/env python3
"""
Test script for CLI integration
"""

import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class RealNewsletterCLI:
    def __init__(self):
        # CLI 경로 설정 - 프로젝트 루트에서 실행
        self.project_root = os.path.dirname(__file__)
        self.timeout = 300  # 5분 타임아웃
        print(f"✅ RealNewsletterCLI initialized")
        print(f"   Project root: {self.project_root}")
        print(f"   Timeout: {self.timeout} seconds")

    def generate_newsletter(
        self,
        keywords=None,
        domain=None,
        template_style="compact",
        email_compatible=False,
        period=14,
    ):
        """실제 CLI를 사용하여 뉴스레터 생성"""
        try:
            # CLI 명령어 구성
            cmd = [
                sys.executable,
                "-m",
                "newsletter.cli",
                "run",
                "--output-format",
                "html",
                "--template-style",
                template_style,
                "--period",
                str(period),
            ]

            # 키워드 또는 도메인 추가
            if keywords:
                cmd.extend(["--keywords", keywords])
            elif domain:
                cmd.extend(["--domain", domain])
            else:
                raise ValueError("Either keywords or domain must be provided")

            # 이메일 호환성 옵션 추가
            if email_compatible:
                cmd.append("--email-compatible")

            # CLI 실행
            print(f"🚀 Executing CLI command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            print(f"📊 CLI execution completed")
            print(f"   Return code: {result.returncode}")
            print(f"   Stdout length: {len(result.stdout)}")
            print(f"   Stderr length: {len(result.stderr)}")

            if result.stdout:
                print(f"📝 Stdout preview: {result.stdout[:200]}...")
            if result.stderr:
                print(f"⚠️  Stderr preview: {result.stderr[:200]}...")

            # 결과 처리
            if result.returncode != 0:
                error_msg = f"CLI execution failed: {result.stderr}"
                print(f"❌ {error_msg}")
                return self._fallback_response(keywords or domain, error_msg)

            # output 디렉토리에서 최신 HTML 파일 찾기
            output_dir = os.path.join(self.project_root, "output")
            html_content = self._find_latest_html_file(output_dir)

            if html_content:
                # 제목 추출
                title = (
                    self._extract_title_from_html(html_content)
                    or f"Newsletter: {keywords or domain}"
                )

                print(f"✅ Newsletter generated successfully")
                print(f"   Title: {title}")
                print(f"   Content length: {len(html_content)}")

                return {
                    "content": html_content,
                    "title": title,
                    "status": "success",
                    "cli_output": result.stdout,
                }
            else:
                error_msg = "No HTML output file found"
                print(f"❌ {error_msg}")
                return self._fallback_response(keywords or domain, error_msg)

        except subprocess.TimeoutExpired:
            error_msg = f"CLI execution timed out after {self.timeout} seconds"
            print(f"⏰ {error_msg}")
            return self._fallback_response(keywords or domain, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"💥 {error_msg}")
            return self._fallback_response(keywords or domain, error_msg)

    def _find_latest_html_file(self, output_dir):
        """output 디렉토리에서 최신 HTML 파일 찾기"""
        try:
            if not os.path.exists(output_dir):
                print(f"📁 Output directory does not exist: {output_dir}")
                return None

            html_files = [f for f in os.listdir(output_dir) if f.endswith(".html")]
            print(f"📁 Found {len(html_files)} HTML files in output directory")

            if not html_files:
                print(f"📁 No HTML files found in {output_dir}")
                return None

            # 최신 파일 찾기
            latest_file = max(
                html_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x))
            )
            file_path = os.path.join(output_dir, latest_file)

            print(f"📄 Reading latest file: {latest_file}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            print(f"📄 File read successfully, length: {len(content)}")
            return content

        except Exception as e:
            print(f"❌ Error reading HTML file: {e}")
            return None

    def _extract_title_from_html(self, html_content):
        """HTML에서 제목 추출"""
        try:
            import re

            title_match = re.search(
                r"<title>(.*?)</title>", html_content, re.IGNORECASE
            )
            if title_match:
                return title_match.group(1)
            return None
        except Exception:
            return None

    def _fallback_response(self, input_param, error_msg):
        """에러 발생 시 폴백 응답 생성"""
        title = f"Newsletter Generation Failed: {input_param}"
        content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body>
    <h1>Newsletter Generation Error</h1>
    <p><strong>Input:</strong> {input_param}</p>
    <p><strong>Error:</strong> {error_msg}</p>
    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
"""

        return {
            "content": content,
            "title": title,
            "status": "error",
            "error": error_msg,
        }


def test_cli_integration():
    """CLI 연동 테스트"""
    print("🧪 Starting CLI integration test...")

    # CLI 객체 생성
    cli = RealNewsletterCLI()

    # 간단한 키워드 테스트
    print("\n📋 Testing with keywords: 'AI'")
    result = cli.generate_newsletter(keywords="AI", template_style="compact")

    print(f"\n📊 Test Result:")
    print(f"   Status: {result['status']}")
    print(f"   Title: {result['title']}")
    print(f"   Content length: {len(result['content'])}")

    if result["status"] == "error":
        print(f"   Error: {result.get('error', 'Unknown error')}")

    return result["status"] == "success"


if __name__ == "__main__":
    success = test_cli_integration()
    if success:
        print("\n✅ CLI integration test PASSED")
        sys.exit(0)
    else:
        print("\n❌ CLI integration test FAILED")
        sys.exit(1)
