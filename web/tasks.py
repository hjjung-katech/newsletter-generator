"""
Background tasks for newsletter generation
Uses Redis Queue (RQ) for asynchronous processing
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
import subprocess
import traceback

# Add the parent directory to the path to import newsletter modules
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import PathManager for unified path handling
from path_manager import get_path_manager

# Use PathManager for consistent path handling across all modules
path_manager = get_path_manager()
DATABASE_PATH = path_manager.get_database_path()

print(f"[DEBUG] tasks.py using PathManager DATABASE_PATH: {DATABASE_PATH}")
print(f"[DEBUG] Database file exists: {os.path.exists(DATABASE_PATH)}")
print(f"[DEBUG] Environment: {'PyInstaller exe' if path_manager.is_frozen else 'Development'}")


def update_job_status(job_id, status, result=None):
    """Update job status in database, creating record if it doesn't exist"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check if record exists
    cursor.execute("SELECT id FROM history WHERE id = ?", (job_id,))
    record_exists = cursor.fetchone()
    
    if not record_exists:
        # Create new record for scheduled jobs
        from datetime import datetime
        cursor.execute(
            "INSERT INTO history (id, params, status, created_at) VALUES (?, ?, ?, ?)",
            (job_id, json.dumps({"source": "scheduled"}), status, datetime.now().isoformat())
        )
        print(f"[DEBUG] Created new history record for scheduled job: {job_id}")
    else:
        # Update existing record
        if result:
            cursor.execute(
                "UPDATE history SET status = ?, result = ? WHERE id = ?",
                (status, json.dumps(result), job_id),
            )
        else:
            cursor.execute("UPDATE history SET status = ? WHERE id = ?", (status, job_id))
        print(f"[DEBUG] Updated existing history record: {job_id} -> {status}")

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

        # Direct function call instead of subprocess for PyInstaller compatibility
        print(f"🚀 Starting direct newsletter generation")
        try:
            # Import newsletter modules
            import sys
            project_root = os.path.dirname(os.path.dirname(__file__))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
                
            from newsletter import graph, tools
            from newsletter.utils.logger import get_logger
            
            print(f"📊 Keywords: {keywords}")
            print(f"📊 Domain: {domain}")
            print(f"📊 Template style: {template_style}")
            print(f"📊 Period: {period} days")
            print(f"📊 Email compatible: {email_compatible}")
            
            # Prepare keywords list
            if keywords:
                keyword_str = keywords if isinstance(keywords, str) else ",".join(keywords)
                keyword_list = [kw.strip() for kw in keyword_str.split(",") if kw.strip()]
            elif domain:
                # Generate keywords from domain
                keyword_list = tools.extract_keywords_from_domain(
                    domain, suggest_count=10
                )
                if not keyword_list:
                    raise ValueError(f"도메인 '{domain}'에서 키워드를 생성할 수 없습니다")
            else:
                raise ValueError("키워드 또는 도메인이 필요합니다")
            
            print(f"🔍 Using keywords: {keyword_list}")
            
            # Set output directory for newsletter generation using PathManager
            output_dir = path_manager.get_output_dir()
            print(f"🔧 Setting output directory: {output_dir}")
            
            # Set environment variable for newsletter module to use
            os.environ['NEWSLETTER_OUTPUT_DIR'] = output_dir
            
            # Call the core newsletter generation function
            html_content, status = graph.generate_newsletter(
                keyword_list,
                period,
                domain=domain,
                template_style=template_style,
                email_compatible=email_compatible,
            )
            
            if status != "success":
                raise RuntimeError(f"Newsletter generation failed: {status}")
                
            print(f"✅ Newsletter generated successfully")
            print(f"📝 Content length: {len(html_content)} characters")
            
            # Create a result object that matches subprocess.run structure
            class DirectCallResult:
                def __init__(self, html_content):
                    self.returncode = 0
                    self.stdout = f"Newsletter generation completed successfully.\nContent length: {len(html_content)} characters"
                    self.stderr = ""
                    self.html_content = html_content
                    
            result = DirectCallResult(html_content)
            
        except Exception as e:
            print(f"❌ Direct function call failed: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            # Fall back to original subprocess method for development
            try:
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
                    cmd.extend(["--keywords", keyword_str])
                elif domain:
                    cmd.extend(["--domain", domain])

                print(f"🔄 Falling back to CLI subprocess: {' '.join(cmd)}")

                # CLI 실행 환경 설정
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONPATH"] = os.path.dirname(os.path.dirname(__file__))
                env["LC_ALL"] = "en_US.UTF-8"
                env["LANG"] = "en_US.UTF-8"
                env["PYTHONUTF8"] = "1"

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.dirname(__file__)),
                    env=env,
                    timeout=300,
                )
            except Exception as subprocess_error:
                raise RuntimeError(f"Both direct call and subprocess failed. Direct: {str(e)}, Subprocess: {str(subprocess_error)}")

        print(f"✅ Newsletter generation completed")
        if hasattr(result, 'stdout') and result.stdout:
            print(f"📝 Output: {str(result.stdout)[:500]}...")
        if hasattr(result, 'stderr') and result.stderr:
            print(f"⚠️ Errors: {str(result.stderr)[:500]}...")

        if hasattr(result, 'returncode') and result.returncode != 0:
            raise RuntimeError(
                f"Newsletter generation failed with return code {result.returncode}: {getattr(result, 'stderr', 'Unknown error')}"
            )

        # Get HTML content - either from direct function result or file
        html_content = None
        latest_file = "direct_generation"
        encoding_used = "utf-8"
        
        # Check if we got HTML content directly from the function call
        if hasattr(result, 'html_content') and result.html_content:
            html_content = result.html_content
            print(f"📄 Using HTML content from direct function call")
            print(f"📊 Content length: {len(html_content)} characters")
        else:
            # Fallback: Read from file (for subprocess method)
            print(f"📁 Looking for generated HTML file...")
            output_dir = path_manager.get_output_dir()
            
            # Ensure output directory exists
            if not os.path.exists(output_dir):
                raise FileNotFoundError(f"Output directory not found: {output_dir}")

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

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        html_content = f.read()
                        encoding_used = encoding
                        print(f"✅ Successfully read file with {encoding} encoding")
                        print(f"📊 Content length: {len(html_content)} characters")
                        break
                except UnicodeDecodeError:
                    print(f"❌ Failed to read with {encoding} encoding")
                    continue

        if not html_content:
            raise RuntimeError("HTML 콘텐츠를 가져올 수 없습니다 (직접 호출 및 파일 읽기 모두 실패)")

        # 결과 구성
        result_data = {
            "status": "success",
            "html_content": html_content,
            "file_path": latest_file,
            "file_size": len(html_content),
            "encoding_used": encoding_used,
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
