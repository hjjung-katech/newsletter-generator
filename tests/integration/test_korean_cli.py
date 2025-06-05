#!/usr/bin/env python3
"""
Korean CLI Integration Tests
한국어 키워드를 사용한 뉴스레터 생성 CLI 테스트
"""

import os
import pytest
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# 상수 정의
TIMEOUT_SECONDS = 300
KOREAN_TEST_KEYWORDS = ["토요타", "삼성전자", "AI", "반도체"]
EXPECTED_MIN_CONTENT_LENGTH = 1000
PROJECT_ROOT = Path(__file__).parent.parent.parent


class KoreanCLITester:
    """한국어 CLI 테스트를 위한 유틸리티 클래스"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.output_dir = self.project_root / "output"
        self.timeout = TIMEOUT_SECONDS

    def _get_safe_environment(self) -> Dict[str, str]:
        """한국어 인코딩을 위한 안전한 환경 변수 설정"""
        env = os.environ.copy()
        env.update(
            {
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "CHCP": "65001",
                "LC_ALL": "en_US.UTF-8",
                "LANG": "en_US.UTF-8",
            }
        )
        return env

    def _safe_decode(self, byte_data: bytes) -> str:
        """여러 인코딩을 시도하여 안전하게 디코딩"""
        if not byte_data:
            return ""

        encodings = ["utf-8", "cp949", "euc-kr", "latin1"]
        for encoding in encodings:
            try:
                return byte_data.decode(encoding)
            except UnicodeDecodeError:
                continue

        # 마지막 수단: 에러 무시
        return byte_data.decode("utf-8", errors="ignore")

    def run_cli_command(self, keywords: str, **kwargs) -> Dict[str, Any]:
        """CLI 명령어 실행"""
        cmd = [
            sys.executable,
            "-m",
            "newsletter.cli",
            "run",
            "--keywords",
            keywords,
            "--output-format",
            "html",
            "--template-style",
            kwargs.get("template_style", "compact"),
            "--period",
            str(kwargs.get("period", 14)),
            "--log-level",
            "INFO",
        ]

        if kwargs.get("email_compatible"):
            cmd.append("--email-compatible")

        logging.info(f"🚀 Executing Korean CLI test: {keywords}")
        logging.info(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=False,  # 바이트 모드로 실행
                env=self._get_safe_environment(),
                timeout=self.timeout,
            )

            # 안전한 디코딩
            stdout = self._safe_decode(result.stdout)
            stderr = self._safe_decode(result.stderr)

            return {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"CLI command timed out after {self.timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"CLI execution failed: {str(e)}")

    def find_latest_output_file(self) -> Optional[Path]:
        """최신 출력 파일 찾기"""
        if not self.output_dir.exists():
            return None

        html_files = list(self.output_dir.glob("*.html"))
        if not html_files:
            return None

        # 수정 시간 기준 최신 파일 반환
        return max(html_files, key=lambda f: f.stat().st_mtime)

    def read_output_content(self, file_path: Path) -> str:
        """출력 파일 내용 읽기"""
        encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]

        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        # 마지막 수단
        return file_path.read_text(encoding="utf-8", errors="ignore")

    def validate_korean_content(self, content: str, keywords: str) -> Dict[str, Any]:
        """한국어 콘텐츠 검증"""
        validation_result = {"is_valid": True, "issues": [], "metrics": {}}

        # 기본 길이 체크
        if len(content) < EXPECTED_MIN_CONTENT_LENGTH:
            validation_result["is_valid"] = False
            validation_result["issues"].append(
                f"Content too short: {len(content)} < {EXPECTED_MIN_CONTENT_LENGTH}"
            )

        # HTML 구조 체크
        required_tags = ["<html", "<head", "<body", "<title"]
        for tag in required_tags:
            if tag not in content.lower():
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Missing required tag: {tag}")

        # 키워드 포함 여부 체크 (대소문자 무시)
        content_lower = content.lower()
        keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
        found_keywords = [kw for kw in keyword_list if kw in content_lower]

        validation_result["metrics"] = {
            "content_length": len(content),
            "keyword_matches": len(found_keywords),
            "total_keywords": len(keyword_list),
            "found_keywords": found_keywords,
        }

        if not found_keywords:
            validation_result["issues"].append("No keywords found in content")

        return validation_result


@pytest.fixture
def korean_cli_tester():
    """Korean CLI 테스터 픽스처"""
    return KoreanCLITester()


@pytest.mark.korean
@pytest.mark.integration
class TestKoreanCLI:
    """한국어 CLI 테스트 클래스"""

    def test_single_korean_keyword(self, korean_cli_tester):
        """단일 한국어 키워드 테스트"""
        keyword = "토요타"

        result = korean_cli_tester.run_cli_command(keyword)

        assert result["success"], f"CLI failed: {result['stderr']}"
        assert result["returncode"] == 0

        # 출력 파일 확인
        output_file = korean_cli_tester.find_latest_output_file()
        assert output_file is not None, "No output file generated"
        assert output_file.exists(), f"Output file does not exist: {output_file}"

        # 콘텐츠 검증
        content = korean_cli_tester.read_output_content(output_file)
        validation = korean_cli_tester.validate_korean_content(content, keyword)

        assert validation[
            "is_valid"
        ], f"Content validation failed: {validation['issues']}"
        assert validation["metrics"]["content_length"] > EXPECTED_MIN_CONTENT_LENGTH

    def test_multiple_korean_keywords(self, korean_cli_tester):
        """복수 한국어 키워드 테스트"""
        keywords = "삼성전자,토요타,AI"

        result = korean_cli_tester.run_cli_command(keywords)

        assert result["success"], f"CLI failed: {result['stderr']}"

        output_file = korean_cli_tester.find_latest_output_file()
        assert output_file is not None

        content = korean_cli_tester.read_output_content(output_file)
        validation = korean_cli_tester.validate_korean_content(content, keywords)

        assert validation["is_valid"], f"Validation failed: {validation['issues']}"
        # 적어도 하나의 키워드는 찾아야 함
        assert validation["metrics"]["keyword_matches"] > 0

    def test_mixed_language_keywords(self, korean_cli_tester):
        """한국어와 영어 혼합 키워드 테스트"""
        keywords = "반도체,semiconductor,AI"

        result = korean_cli_tester.run_cli_command(keywords)

        assert result["success"], f"CLI failed: {result['stderr']}"

        output_file = korean_cli_tester.find_latest_output_file()
        assert output_file is not None

        content = korean_cli_tester.read_output_content(output_file)
        validation = korean_cli_tester.validate_korean_content(content, keywords)

        assert validation["is_valid"], f"Validation failed: {validation['issues']}"

    def test_korean_with_different_periods(self, korean_cli_tester):
        """다양한 기간으로 한국어 키워드 테스트"""
        keyword = "AI"
        periods = [1, 7, 14]

        for period in periods:
            result = korean_cli_tester.run_cli_command(keyword, period=period)

            assert result[
                "success"
            ], f"CLI failed for period {period}: {result['stderr']}"

            output_file = korean_cli_tester.find_latest_output_file()
            assert output_file is not None, f"No output for period {period}"

    def test_korean_email_compatible(self, korean_cli_tester):
        """이메일 호환 모드로 한국어 키워드 테스트"""
        keyword = "토요타"

        result = korean_cli_tester.run_cli_command(
            keyword, email_compatible=True, template_style="compact"
        )

        assert result["success"], f"CLI failed: {result['stderr']}"

        output_file = korean_cli_tester.find_latest_output_file()
        assert output_file is not None

        content = korean_cli_tester.read_output_content(output_file)

        # 이메일 호환성 검증
        assert "<!DOCTYPE html" in content
        assert "charset=" in content
        validation = korean_cli_tester.validate_korean_content(content, keyword)
        assert validation["is_valid"]

    def test_encoding_stability(self, korean_cli_tester):
        """인코딩 안정성 테스트"""
        special_keywords = [
            "한글테스트",
            "특수문자!@#",
            "漢字混合",
            "émojï🎉",
        ]

        for keyword in special_keywords:
            try:
                result = korean_cli_tester.run_cli_command(keyword)
                # 실패해도 크래시하지 않아야 함
                assert isinstance(result["stdout"], str)
                assert isinstance(result["stderr"], str)
            except Exception as e:
                pytest.fail(f"Encoding failed for keyword '{keyword}': {e}")


@pytest.mark.slow
@pytest.mark.korean
@pytest.mark.integration
class TestKoreanCLIPerformance:
    """한국어 CLI 성능 테스트"""

    def test_korean_cli_timeout(self, korean_cli_tester):
        """타임아웃 테스트"""
        keyword = "토요타"

        # 타임아웃이 설정된 시간 내에 완료되어야 함
        result = korean_cli_tester.run_cli_command(keyword)
        assert result["success"] or "timeout" not in result["stderr"].lower()


if __name__ == "__main__":
    # 직접 실행 시 기본 테스트 수행
    tester = KoreanCLITester()

    print("🚀 한국어 CLI 테스트 시작")
    try:
        result = tester.run_cli_command("토요타")
        print(f"✅ 테스트 완료: {result['success']}")

        if result["success"]:
            output_file = tester.find_latest_output_file()
            if output_file:
                content = tester.read_output_content(output_file)
                validation = tester.validate_korean_content(content, "토요타")
                print(f"📊 검증 결과: {validation}")
        else:
            print(f"❌ 테스트 실패: {result['stderr']}")

    except Exception as e:
        print(f"💥 예외 발생: {e}")
