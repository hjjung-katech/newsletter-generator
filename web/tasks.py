"""
Background tasks for newsletter generation
Uses Redis Queue (RQ) for asynchronous processing
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
import subprocess
import traceback

# Add the parent directory to the path to import newsletter modules
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")


def update_job_status(job_id, status, result=None):
    """Update job status in database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if result:
        cursor.execute(
            "UPDATE history SET status = ?, result = ? WHERE id = ?",
            (status, json.dumps(result), job_id),
        )
    else:
        cursor.execute("UPDATE history SET status = ? WHERE id = ?", (status, job_id))

    conn.commit()
    conn.close()


def generate_newsletter_task(data, job_id, send_email=False):
    """Redis Worker에서 실행되는 뉴스레터 생성 작업"""

    print(f"🔄 Redis Worker: Starting newsletter generation for job {job_id}")
    print(f"📊 Input data: {data}")
    print(f"📧 Send email: {send_email}")

    try:
        update_job_status(job_id, "processing")

        # CLI 명령어 구성
        keywords = data.get("keywords", "")
        domain = data.get("domain", "")
        template_style = data.get("template_style", "compact")
        email_compatible = data.get("email_compatible", False)
        period = data.get("period", 14)
        email = data.get("email", "")

        # CLI 명령어 구성
        cmd = [
            os.path.join(
                os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"
            ),
            "-m",
            "newsletter.cli",
            "run",
            "--output-format",
            "html",
            "--template-style",
            template_style,
            "--period",
            str(period),
            "--log-level",
            "INFO",
        ]

        # 키워드 또는 도메인 추가
        if keywords:
            keyword_str = keywords if isinstance(keywords, str) else ",".join(keywords)
            # 한국어 키워드를 UTF-8로 안전하게 처리
            try:
                keyword_str.encode("utf-8")  # UTF-8 인코딩 가능한지 확인
            except UnicodeEncodeError:
                print(f"⚠️ Keyword encoding issue, trying to normalize: {keyword_str}")
                keyword_str = keyword_str.encode("utf-8", errors="ignore").decode(
                    "utf-8"
                )
            cmd.extend(["--keywords", keyword_str])
        elif domain:
            cmd.extend(["--domain", domain])
        else:
            raise ValueError("키워드 또는 도메인이 필요합니다")

        print(f"🚀 Executing CLI command: {' '.join(cmd)}")

        # CLI 실행 환경 설정
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(__file__))
        # 한국어 인코딩 관련 환경 변수 설정
        env["LC_ALL"] = "en_US.UTF-8"
        env["LANG"] = "en_US.UTF-8"
        env["PYTHONUTF8"] = "1"

        # CLI 실행 - 바이트 모드로 처리 후 안전하게 디코딩
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # 바이트 모드 사용
                cwd=os.path.dirname(os.path.dirname(__file__)),
                env=env,
                timeout=300,
            )

            # 안전한 UTF-8 디코딩
            stdout_text = ""
            stderr_text = ""

            if result.stdout:
                try:
                    stdout_text = result.stdout.decode("utf-8")
                except UnicodeDecodeError:
                    # CP949/EUC-KR로 시도
                    try:
                        stdout_text = result.stdout.decode("cp949")
                    except UnicodeDecodeError:
                        # 마지막으로 latin1으로 안전하게 디코딩
                        stdout_text = result.stdout.decode("latin1")

            if result.stderr:
                try:
                    stderr_text = result.stderr.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        stderr_text = result.stderr.decode("cp949")
                    except UnicodeDecodeError:
                        stderr_text = result.stderr.decode("latin1")

            # 결과 객체에 디코딩된 텍스트 할당
            result.stdout = stdout_text
            result.stderr = stderr_text

        except subprocess.TimeoutExpired:
            raise RuntimeError("CLI 실행이 시간 초과되었습니다 (300초)")
        except Exception as e:
            raise RuntimeError(f"CLI 실행 중 오류 발생: {str(e)}")

        print(f"✅ CLI execution completed")
        print(f"📝 CLI stdout: {result.stdout[:500]}...")
        if result.stderr:
            print(f"⚠️ CLI stderr: {result.stderr[:500]}...")

        if result.returncode != 0:
            raise RuntimeError(
                f"CLI failed with return code {result.returncode}: {result.stderr}"
            )

        # 생성된 HTML 파일 찾기
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

        # 키워드 기반으로 최신 파일 찾기
        search_terms = []
        if keywords:
            if isinstance(keywords, str):
                search_terms = [kw.strip().lower() for kw in keywords.split(",")]
            else:
                search_terms = [str(kw).strip().lower() for kw in keywords]
        elif domain:
            search_terms = [domain.lower()]

        html_files = [f for f in os.listdir(output_dir) if f.endswith(".html")]

        # 검색어가 포함된 파일 필터링
        matching_files = []
        for file in html_files:
            file_lower = file.lower()
            for term in search_terms:
                if term in file_lower:
                    matching_files.append(file)
                    break

        if matching_files:
            html_files = matching_files
            print(
                f"📁 Found {len(matching_files)} files matching search terms: {search_terms}"
            )
        else:
            print(f"⚠️ No files found matching search terms, using all HTML files")

        if not html_files:
            raise FileNotFoundError("생성된 HTML 파일을 찾을 수 없습니다")

        # 최신 파일 선택
        latest_file = max(
            html_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x))
        )
        file_path = os.path.join(output_dir, latest_file)

        print(f"📄 Reading HTML file: {latest_file}")
        print(f"📂 File path: {file_path}")
        print(f"📏 File size: {os.path.getsize(file_path)} bytes")

        # 다양한 인코딩으로 파일 읽기 시도
        encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr", "latin1"]
        html_content = None

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    html_content = f.read()
                    print(f"✅ Successfully read file with {encoding} encoding")
                    print(f"📊 Content length: {len(html_content)} characters")
                    break
            except UnicodeDecodeError:
                print(f"❌ Failed to read with {encoding} encoding")
                continue

        if not html_content:
            raise RuntimeError("모든 인코딩으로 파일 읽기에 실패했습니다")

        # 결과 구성
        result_data = {
            "status": "success",
            "html_content": html_content,
            "file_path": latest_file,
            "file_size": len(html_content),
            "encoding_used": encoding,
            "cli_mode": "Real CLI",
            "template_style": template_style,
            "email_compatible": email_compatible,
            "period": f"{period} days",
            "keywords": keywords,
            "domain": domain,
        }

        # 이메일 발송 (옵션)
        email_sent = False
        if send_email and email:
            print(f"📧 Sending email to: {email}")
            try:
                # 이메일 모듈 import
                from mail import send_email as mail_send_email

                # 제목 생성
                if keywords:
                    subject_keywords = (
                        keywords if isinstance(keywords, str) else ", ".join(keywords)
                    )
                    subject = f"Newsletter: {subject_keywords}"
                else:
                    subject = f"Newsletter: {domain}"

                mail_send_email(to=email, subject=subject, html=html_content)
                result_data["email_sent"] = True
                result_data["email_to"] = email
                email_sent = True
                print(f"✅ Email sent successfully to {email}")

            except Exception as e:
                print(f"❌ Email sending failed: {e}")
                result_data["email_sent"] = False
                result_data["email_error"] = str(e)

        result_data["sent"] = email_sent

        # 성공 상태로 업데이트
        update_job_status(job_id, "completed", result_data)
        print(f"🎉 Newsletter generation completed successfully for job {job_id}")

        return result_data

    except Exception as e:
        # 전체 스택트레이스 캡처
        full_traceback = traceback.format_exc()
        error_msg = f"Newsletter generation failed: {str(e)}"

        print(f"[오류] Error in generate_newsletter_task: {error_msg}")
        print(f"[추적] Full traceback:\n{full_traceback}")

        # sys 변수 상태 확인
        try:
            python_executable = os.path.join(
                os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"
            )
            print(f"🐍 Python executable: {python_executable}")
            print(f"🐍 Current working directory: {os.getcwd()}")
        except Exception as sys_check_error:
            print(f"❌ Python executable check failed: {sys_check_error}")

        # 실패 상태로 업데이트 (더 자세한 에러 정보 포함)
        detailed_error_info = {
            "error": error_msg,
            "traceback": full_traceback,
            "error_type": type(e).__name__,
        }
        update_job_status(job_id, "failed", detailed_error_info)

        # 예외를 다시 발생시켜 RQ가 처리하도록 함
        raise


def generate_subject(params):
    """Generate newsletter subject based on parameters"""
    if "keywords" in params:
        keywords = params["keywords"]
        if isinstance(keywords, list):
            keywords_str = ", ".join(keywords[:3])  # First 3 keywords
        else:
            keywords_str = keywords
        return f"Newsletter: {keywords_str}"
    elif "domain" in params:
        return f"Newsletter: {params['domain']} Insights"
    else:
        return f"Newsletter - {datetime.now().strftime('%Y-%m-%d')}"


def create_schedule_entry(params, job_id):
    """Create a scheduled newsletter entry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Calculate next run time (simplified - would use proper RRULE parsing in production)
    next_run = datetime.now() + timedelta(days=7)  # Default to weekly

    cursor.execute(
        """
        INSERT INTO schedules (id, params, rrule, next_run)
        VALUES (?, ?, ?, ?)
    """,
        (schedule_id, json.dumps(params), params.get("rrule", "FREQ=WEEKLY"), next_run),
    )

    conn.commit()
    conn.close()

    return schedule_id


# Worker entry point for RQ
if __name__ == "__main__":
    # This can be used to test tasks locally
    test_params = {"keywords": "AI, machine learning", "email": "test@example.com"}
    result = generate_newsletter_task(test_params, "test-job-id")
    print("Task result:", result)
