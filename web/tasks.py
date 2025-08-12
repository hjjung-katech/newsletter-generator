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
        try:
            from web.time_utils import get_utc_now, to_iso_utc  # PyInstaller
        except ImportError:
            from time_utils import get_utc_now, to_iso_utc      # Development
        cursor.execute(
            "INSERT INTO history (id, params, status, created_at) VALUES (?, ?, ?, ?)",
            (job_id, json.dumps({"source": "scheduled"}), status, to_iso_utc(get_utc_now()))
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

        # 새로운 source_type 기반 처리
        source_type = data.get("source_type", "keywords")  # 기존 호환성을 위한 기본값
        source_value = data.get("source_value", "")
        suggest_count = data.get("suggest_count", 10)
        template_style = data.get("template_style", "compact")
        email_compatible = data.get("email_compatible", False)
        period = data.get("period", 14)
        email = data.get("email", "")

        # 기존 format 호환성 처리 (legacy support)
        if not source_type or source_type == "keywords":
            if data.get("keywords"):
                source_type = "keywords"
                source_value = data.get("keywords")
            elif data.get("domain"):
                source_type = "domain"
                source_value = data.get("domain")

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
            
            print(f"📊 Source type: {source_type}")
            print(f"📊 Source value: {source_value}")
            print(f"📊 Suggest count: {suggest_count}")
            print(f"📊 Template style: {template_style}")
            print(f"📊 Period: {period} days")
            print(f"📊 Email compatible: {email_compatible}")
            
            # 키워드 생성 로직 (동적 vs 정적)
            if source_type == "domain":
                # 도메인 기반: 매번 새로운 키워드 생성
                print(f"🔄 Generating fresh keywords from domain: {source_value}")
                keyword_list = tools.generate_keywords_with_gemini(
                    source_value, count=suggest_count
                )
                if not keyword_list:
                    raise ValueError(f"도메인 '{source_value}'에서 키워드를 생성할 수 없습니다")
                
                # 생성된 키워드를 로그에 출력
                print(f"✅ Generated keywords: {', '.join(keyword_list)}")
                
                # 결과에 포함할 정보
                generation_info = {
                    "source_type": "domain",
                    "domain": source_value,
                    "generated_keywords": keyword_list,
                    "suggest_count": suggest_count,
                    "generation_time": to_iso_utc(get_utc_now())
                }
            else:
                # 키워드 기반: 고정된 키워드 사용
                print(f"📝 Using fixed keywords: {source_value}")
                keyword_str = source_value if isinstance(source_value, str) else ",".join(source_value)
                keyword_list = [kw.strip() for kw in keyword_str.split(",") if kw.strip()]
                
                if not keyword_list:
                    raise ValueError("키워드가 비어있습니다")
                
                # 결과에 포함할 정보
                generation_info = {
                    "source_type": "keywords",
                    "fixed_keywords": keyword_list
                }

            if not keyword_list:
                raise ValueError("키워드 목록이 비어있습니다")
            
            print(f"🔍 Using keywords: {keyword_list}")
            
            # Set output directory for newsletter generation using PathManager
            output_dir = path_manager.get_output_dir()
            print(f"🔧 Setting output directory: {output_dir}")
            
            # Set environment variable for newsletter module to use
            os.environ['NEWSLETTER_OUTPUT_DIR'] = output_dir
            
            # Call the core newsletter generation function
            domain_param = source_value if source_type == "domain" else None
            html_content, status = graph.generate_newsletter(
                keyword_list,
                period,
                domain=domain_param,
                template_style=template_style,
                email_compatible=email_compatible,
            )
            
            if status != "success":
                raise RuntimeError(f"Newsletter generation failed: {status}")
                
            print(f"✅ Newsletter generated successfully")
            print(f"📝 Content length: {len(html_content)} characters")
            
            # Create a result object that matches subprocess.run structure
            class DirectCallResult:
                def __init__(self, html_content, generation_info):
                    self.returncode = 0
                    self.stdout = f"Newsletter generation completed successfully.\nContent length: {len(html_content)} characters"
                    self.stderr = ""
                    self.html_content = html_content
                    self.generation_info = generation_info
                    
            result = DirectCallResult(html_content, generation_info)
            
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

                # 새로운 구조에 맞게 키워드 또는 도메인 추가
                if source_type == "domain":
                    cmd.extend(["--domain", source_value, "--suggest-count", str(suggest_count)])
                else:
                    keyword_str = source_value if isinstance(source_value, str) else ",".join(keyword_list)
                    cmd.extend(["--keywords", keyword_str])

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
            if source_type == "domain":
                search_terms = [source_value.lower()]
            else:
                if isinstance(source_value, str):
                    search_terms = [kw.strip().lower() for kw in source_value.split(",")]
                else:
                    search_terms = [str(kw).strip().lower() for kw in keyword_list]

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

        # 결과에 generation_info 포함
        result_generation_info = generation_info if 'generation_info' in locals() else {}
        if hasattr(result, 'generation_info'):
            result_generation_info = result.generation_info
        
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
            "source_type": source_type,
            "source_value": source_value,
            "generation_info": result_generation_info,
            # 하위 호환성을 위한 레거시 필드들
            "keywords": source_value if source_type == "keywords" else None,
            "domain": source_value if source_type == "domain" else None,
        }

        # 이메일 발송 (옵션)
        email_sent = False
        if send_email and email:
            print(f"📧 Sending email to: {email}")
            try:
                # 이메일 모듈 import
                from mail import send_email as mail_send_email

                # 제목 생성 (CLI 로직과 일치)
                if source_type == "domain":
                    # 도메인 기반: "도메인명 주간 산업동향"
                    subject = f"{source_value} 주간 산업동향"
                    
                    # 실제 사용된 키워드 정보 추가
                    if result_generation_info.get("generated_keywords"):
                        keyword_info = f" (키워드: {', '.join(result_generation_info['generated_keywords'])})"
                        if len(subject + keyword_info) <= 100:  # 이메일 제목 길이 제한
                            subject += keyword_info
                else:
                    # 키워드 기반: 키워드 개수에 따라 처리
                    if isinstance(source_value, str):
                        keywords_list = [kw.strip() for kw in source_value.split(",") if kw.strip()]
                    else:
                        keywords_list = keyword_list if 'keyword_list' in locals() else []
                    
                    if len(keywords_list) == 1:
                        subject = f"{keywords_list[0]} 주간 산업동향"
                    elif len(keywords_list) > 1:
                        subject = f"{keywords_list[0]} 외 {len(keywords_list)-1}개 분야 주간 산업동향"
                    else:
                        subject = "주간 산업동향 뉴스레터"

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
