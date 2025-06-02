"""
Newsletter Generator Web Service
Flask application that provides web interface for the CLI newsletter generator
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import redis
from rq import Queue
import sqlite3
from datetime import datetime
import uuid
import json

# Import task function for RQ
from tasks import generate_newsletter_task

# Add the parent directory to the path to import newsletter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Real newsletter CLI integration
import subprocess
import tempfile
import logging


class RealNewsletterCLI:
    def __init__(self):
        # CLI 경로 설정 - 프로젝트 루트에서 실행
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        self.timeout = 300  # 5분 타임아웃

        # 환경 확인
        self._check_environment()

    def _check_environment(self):
        """환경 설정 확인"""
        # 프로젝트 루트 확인
        if not os.path.exists(os.path.join(self.project_root, "newsletter")):
            raise Exception(f"Newsletter module not found in {self.project_root}")

        # .env 파일 확인
        env_file = os.path.join(self.project_root, ".env")
        if not os.path.exists(env_file):
            print(f"⚠️  Warning: .env file not found at {env_file}")

        print(f"✅ Environment check passed")
        print(f"   Project root: {self.project_root}")
        print(
            f"   Newsletter module exists: {os.path.exists(os.path.join(self.project_root, 'newsletter'))}"
        )
        print(f"   .env file exists: {os.path.exists(env_file)}")

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
            # CLI 명령어 구성 - 더 안정적인 방식으로 개선
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
                "--log-level",
                "INFO",  # 웹서비스에서는 INFO 레벨로 설정
            ]

            # 키워드 또는 도메인 추가
            if keywords:
                # 키워드가 문자열인 경우 그대로, 리스트인 경우 조인
                keyword_str = (
                    keywords if isinstance(keywords, str) else ",".join(keywords)
                )
                cmd.extend(["--keywords", keyword_str])
                input_description = f"keywords: {keyword_str}"
            elif domain:
                cmd.extend(["--domain", domain])
                input_description = f"domain: {domain}"
            else:
                raise ValueError("Either keywords or domain must be provided")

            # 이메일 호환성 옵션 추가
            if email_compatible:
                cmd.append("--email-compatible")

            # 고유한 output 디렉토리 생성 (여러 요청 동시 처리를 위해)
            import time

            timestamp = int(time.time() * 1000)  # 밀리초 타임스탬프
            unique_output_dir = os.path.join(
                self.project_root, "output", f"web_request_{timestamp}"
            )
            os.makedirs(unique_output_dir, exist_ok=True)

            # 고유한 출력 파일 경로 지정
            output_filename = f"newsletter_web_{timestamp}.html"
            output_filepath = os.path.join(unique_output_dir, output_filename)

            # CLI 명령어에 출력 경로 추가
            cmd.extend(["--output", output_filepath])

            # CLI 실행 환경 설정
            env = dict(os.environ)
            env["PYTHONPATH"] = self.project_root

            # CLI 실행
            logging.info(f"Executing CLI command: {' '.join(cmd)}")
            logging.info(f"Working directory: {self.project_root}")
            logging.info(f"Input: {input_description}")
            logging.info(f"Output directory: {unique_output_dir}")

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )

            logging.info(
                f"CLI execution completed with return code: {result.returncode}"
            )

            # 결과 처리
            if result.returncode != 0:
                error_msg = (
                    f"CLI execution failed (code {result.returncode}): {result.stderr}"
                )
                logging.error(error_msg)
                logging.error(f"CLI stdout: {result.stdout}")
                return self._fallback_response(keywords or domain, error_msg)

            # 지정된 출력 파일이 생성되었는지 먼저 확인
            html_content = None
            if os.path.exists(output_filepath):
                try:
                    with open(output_filepath, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    logging.info(f"Successfully read output file: {output_filepath}")
                except Exception as e:
                    logging.error(f"Failed to read output file {output_filepath}: {e}")

            # 지정된 파일이 없으면 디렉토리에서 최신 파일 검색 (폴백)
            if not html_content:
                logging.warning(
                    "Specified output file not found, searching in directory..."
                )
                html_content = self._find_latest_html_file(unique_output_dir)

            # 고유 디렉토리에서도 못찾으면 기본 output 디렉토리에서 검색 (마지막 폴백)
            if not html_content:
                default_output_dir = os.path.join(self.project_root, "output")
                html_content = self._find_latest_html_file(default_output_dir)
                logging.warning(
                    f"HTML not found in unique directory, found in default: {html_content is not None}"
                )

            if html_content:
                # 제목 추출
                title = (
                    self._extract_title_from_html(html_content)
                    or f"Newsletter: {keywords or domain}"
                )

                # 성공 통계 정보 추출
                stats = self._extract_generation_stats(result.stdout)

                logging.info(f"Newsletter generated successfully: {title}")
                logging.info(f"Generated HTML size: {len(html_content)} characters")

                response = {
                    "content": html_content,
                    "title": title,
                    "status": "success",
                    "cli_output": result.stdout,
                    "generation_stats": stats,
                    "input_params": {
                        "keywords": keywords,
                        "domain": domain,
                        "template_style": template_style,
                        "email_compatible": email_compatible,
                        "period": period,
                    },
                }

                # 임시 디렉토리 정리
                try:
                    import shutil

                    shutil.rmtree(unique_output_dir, ignore_errors=True)
                except Exception as cleanup_error:
                    logging.warning(
                        f"Failed to cleanup temporary directory: {cleanup_error}"
                    )

                return response
            else:
                error_msg = f"No HTML output file found in {unique_output_dir} or default output directory"
                logging.error(error_msg)
                return self._fallback_response(keywords or domain, error_msg)

        except subprocess.TimeoutExpired:
            error_msg = f"CLI execution timed out after {self.timeout} seconds"
            logging.error(error_msg)
            return self._fallback_response(keywords or domain, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg, exc_info=True)  # 스택 트레이스 포함
            return self._fallback_response(keywords or domain, error_msg)

    def _find_latest_html_file(self, output_dir):
        """output 디렉토리에서 최신 HTML 파일 찾기"""
        try:
            if not os.path.exists(output_dir):
                return None

            html_files = [f for f in os.listdir(output_dir) if f.endswith(".html")]
            if not html_files:
                return None

            # 최신 파일 찾기
            latest_file = max(
                html_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x))
            )
            file_path = os.path.join(output_dir, latest_file)

            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        except Exception as e:
            logging.error(f"Error reading HTML file: {e}")
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

    def _extract_generation_stats(self, cli_output):
        """CLI 출력에서 생성 통계 정보 추출"""
        stats = {}
        try:
            import re

            # 처리 시간 추출
            time_pattern = r"(\w+)\s+time:\s*([\d.]+)\s*seconds"
            time_matches = re.findall(time_pattern, cli_output)
            if time_matches:
                stats["step_times"] = {step: float(time) for step, time in time_matches}

            # 총 시간 추출
            total_time_pattern = r"Total generation time:\s*([\d.]+)\s*seconds"
            total_match = re.search(total_time_pattern, cli_output)
            if total_match:
                stats["total_time"] = float(total_match.group(1))

            # 기사 수 추출
            article_pattern = r"(\d+)\s+articles?\s+(?:collected|processed|found)"
            article_match = re.search(article_pattern, cli_output, re.IGNORECASE)
            if article_match:
                stats["articles_count"] = int(article_match.group(1))

            # 키워드 정보 추출
            if "Generated keywords:" in cli_output:
                keyword_pattern = r"Generated keywords:\s*(.+)"
                keyword_match = re.search(keyword_pattern, cli_output)
                if keyword_match:
                    stats["generated_keywords"] = keyword_match.group(1).strip()

        except Exception as e:
            logging.warning(f"Failed to extract generation stats: {e}")

        return stats

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
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; border: 1px solid #f5c6cb; }}
        .info {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="error">
        <h2>Newsletter Generation Error</h2>
        <p><strong>Input:</strong> {input_param}</p>
        <p><strong>Error:</strong> {error_msg}</p>
        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="info">
        <h3>What happened?</h3>
        <p>The newsletter CLI encountered an error during generation. This could be due to:</p>
        <ul>
            <li>Network connectivity issues</li>
            <li>API rate limits or quota exceeded</li>
            <li>Invalid input parameters</li>
            <li>CLI timeout (process took longer than {self.timeout} seconds)</li>
        </ul>
        <p>Please try again with different parameters or check the system logs for more details.</p>
    </div>
</body>
</html>
"""

        return {
            "content": content,
            "title": title,
            "status": "error",
            "error": error_msg,
        }


# MockNewsletterCLI는 폴백용으로 유지
class MockNewsletterCLI:
    def __init__(self):
        pass

    def generate_newsletter(
        self,
        keywords=None,
        domain=None,
        template_style="compact",
        email_compatible=False,
        period=14,
    ):
        """Mock newsletter generation with more realistic content"""
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",")]
            title = f"Newsletter: {', '.join(keyword_list)} (Mock)"

            content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .article {{ margin-bottom: 20px; padding: 15px; border-left: 3px solid #007bff; }}
        .article h3 {{ color: #007bff; margin-top: 0; }}
        .footer {{ background: #f4f4f4; padding: 15px; text-align: center; font-size: 0.9em; }}
        .mock-notice {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="mock-notice">
        <strong>⚠️ Mock Mode:</strong> This is a test newsletter generated using mock data. 
        Template Style: {template_style} | Email Compatible: {email_compatible} | Period: {period} days
    </div>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        <h2>Top Stories</h2>
"""

            for i, keyword in enumerate(keyword_list, 1):
                content += f"""
        <div class="article">
            <h3>{i}. Latest developments in {keyword}</h3>
            <p>This is a mock article about recent developments in {keyword}. In a real implementation, this would contain actual news content collected from various sources.</p>
            <p><strong>Key points:</strong></p>
            <ul>
                <li>Market trends and analysis for {keyword}</li>
                <li>Recent technological advancements</li>
                <li>Industry impact and future outlook</li>
            </ul>
        </div>
"""

            content += """
    </div>
    <div class="footer">
        <p>This newsletter was generated by Newsletter Generator Web Service (Mock Mode)</p>
        <p>For more information, visit our website</p>
    </div>
</body>
</html>
"""

        elif domain:
            title = f"Newsletter: {domain} Domain Insights (Mock)"
            content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .footer {{ background: #f4f4f4; padding: 15px; text-align: center; font-size: 0.9em; }}
        .mock-notice {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="mock-notice">
        <strong>⚠️ Mock Mode:</strong> This is a test newsletter generated using mock data. 
        Template Style: {template_style} | Email Compatible: {email_compatible} | Period: {period} days
    </div>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        <div class="section">
            <h3>Recent Developments in {domain}</h3>
            <p>Mock analysis of recent developments in the {domain} sector. This would contain real news and insights in the actual implementation.</p>
        </div>
        <div class="section">
            <h3>Key Trends</h3>
            <p>Analysis of key trends affecting the {domain} industry, including market movements and technological advances.</p>
        </div>
        <div class="section">
            <h3>Future Outlook</h3>
            <p>Forward-looking analysis and predictions for the {domain} sector based on current trends and market indicators.</p>
        </div>
    </div>
    <div class="footer">
        <p>This newsletter was generated by Newsletter Generator Web Service (Mock Mode)</p>
    </div>
</body>
</html>
"""
        else:
            title = "Sample Newsletter (Mock)"
            content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample Newsletter (Mock)</title>
</head>
<body>
    <h1>Sample Newsletter (Mock)</h1>
    <p>No keywords or domain specified. Please provide either keywords or a domain for newsletter generation.</p>
</body>
</html>
"""

        return {"content": content, "title": title, "status": "success"}


# Try to use real CLI first, fallback to mock if it fails
try:
    newsletter_cli = RealNewsletterCLI()
    print("✅ Using RealNewsletterCLI for actual newsletter generation")
    print(f"   Project root: {newsletter_cli.project_root}")
    print(f"   Timeout: {newsletter_cli.timeout} seconds")
except Exception as e:
    print(f"❌ Failed to initialize RealNewsletterCLI: {e}")
    newsletter_cli = MockNewsletterCLI()
    print("⚠️  Falling back to MockNewsletterCLI")

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
print("🔧 Flask app initialized with detailed logging")

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Queue name can be customized via environment variable
QUEUE_NAME = os.getenv("RQ_QUEUE", "default")

# Redis connection with fallback to in-memory processing
try:
    redis_conn = redis.from_url(app.config["REDIS_URL"])
    redis_conn.ping()  # Test connection
    task_queue = Queue(QUEUE_NAME, connection=redis_conn)
    print("Redis connected successfully")
except Exception as e:
    print(f"Redis connection failed: {e}. Using in-memory processing.")
    redis_conn = None
    task_queue = None

# In-memory task storage for when Redis is unavailable
in_memory_tasks = {}

# Database initialization
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage.db")


def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # History table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            result JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """
    )

    # Schedules table for recurring newsletters
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            params JSON NOT NULL,
            rrule TEXT NOT NULL,
            next_run TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
    """
    )

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


@app.route("/")
def index():
    """Main dashboard page"""
    try:
        print(f"Template folder: {app.template_folder}")
        print(f"App root path: {app.root_path}")
        template_path = os.path.join(app.template_folder, "index_en.html")
        print(f"Template path: {template_path}")
        print(f"Template exists: {os.path.exists(template_path)}")
        return render_template("index_en.html")
    except Exception as e:
        print(f"Template rendering error: {e}")
        return f"Template error: {str(e)}", 500


@app.route("/api/generate", methods=["POST"])
def generate_newsletter():
    """Generate newsletter based on keywords or domain"""
    print(f"📨 Newsletter generation request received")

    data = request.get_json()

    if not data:
        print("❌ No data provided in request")
        return jsonify({"error": "No data provided"}), 400

    print(f"📋 Request data: {data}")

    # Create unique job ID
    job_id = str(uuid.uuid4())
    print(f"🆔 Generated job ID: {job_id}")

    # Store request in history
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (id, params, status) VALUES (?, ?, ?)",
        (job_id, json.dumps(data), "pending"),
    )
    conn.commit()
    conn.close()
    print(f"💾 Stored request in database")
    # If Redis is available, queue the task
    if task_queue:
        print(f"📤 Queueing task with Redis")
        job = task_queue.enqueue(generate_newsletter_task, data, job_id)
        return jsonify({"job_id": job_id, "status": "queued"})
    else:
        print(f"🔄 Processing in-memory (Redis not available)")
        # Fallback: process in background using in-memory tracking
        import threading

        # Store initial task status
        in_memory_tasks[job_id] = {
            "status": "processing",
            "started_at": datetime.now().isoformat(),
        }

        # Process in background thread
        def background_task():
            try:
                print(f"⚙️  Starting background processing for job {job_id}")
                process_newsletter_in_memory(data, job_id)
                # Update database with final result
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE history SET result = ?, status = ? WHERE id = ?",
                    (
                        json.dumps(in_memory_tasks[job_id]["result"]),
                        "completed",
                        job_id,
                    ),
                )
                conn.commit()
                conn.close()
                print(f"✅ Completed background processing for job {job_id}")
            except Exception as e:
                print(f"❌ Error in background processing for job {job_id}: {e}")
                # Update database with error
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE history SET result = ?, status = ? WHERE id = ?",
                    (json.dumps({"error": str(e)}), "failed", job_id),
                )
                conn.commit()
                conn.close()

        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()

        return jsonify({"job_id": job_id, "status": "processing"})


def process_newsletter_sync(data):
    """Process newsletter synchronously (fallback when Redis is not available)"""
    try:
        print(f"🔄 Starting synchronous newsletter processing")

        # Extract parameters
        keywords = data.get("keywords", "")
        domain = data.get("domain", "")
        template_style = data.get("template_style", "compact")
        email_compatible = data.get("email_compatible", False)
        period = data.get("period", 14)

        print(f"📋 Processing parameters:")
        print(f"   Keywords: {keywords}")
        print(f"   Domain: {domain}")
        print(f"   Template style: {template_style}")
        print(f"   Email compatible: {email_compatible}")
        print(f"   Period: {period}")

        # Use newsletter CLI with proper parameters
        if keywords:
            print(f"🔧 Generating newsletter with keywords")
            result = newsletter_cli.generate_newsletter(
                keywords=keywords,
                template_style=template_style,
                email_compatible=email_compatible,
                period=period,
            )
        elif domain:
            print(f"🔧 Generating newsletter with domain")
            result = newsletter_cli.generate_newsletter(
                domain=domain,
                template_style=template_style,
                email_compatible=email_compatible,
                period=period,
            )
        else:
            raise ValueError("Either keywords or domain must be provided")

        print(f"📊 CLI result status: {result['status']}")

        # Handle different result formats
        if result["status"] == "error":
            # If CLI failed and returned error, try mock as fallback
            if isinstance(newsletter_cli, RealNewsletterCLI):
                print("⚠️  Real CLI failed, trying mock fallback...")
                mock_cli = MockNewsletterCLI()
                if keywords:
                    result = mock_cli.generate_newsletter(
                        keywords=keywords,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                else:
                    result = mock_cli.generate_newsletter(
                        domain=domain,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                print(f"📊 Mock fallback result status: {result['status']}")

        response = {
            "html_content": result["content"],
            "subject": result["title"],
            "articles_count": result.get("generation_stats", {}).get(
                "articles_count", 0
            ),
            "status": result["status"],
            "cli_output": result.get("cli_output", ""),
            "error": result.get("error"),
            "generation_stats": result.get("generation_stats", {}),
            "input_params": result.get("input_params", {}),
            "html_size": len(result["content"]) if result.get("content") else 0,
            "processing_info": {
                "using_real_cli": isinstance(newsletter_cli, RealNewsletterCLI),
                "template_style": template_style,
                "email_compatible": email_compatible,
                "period_days": period,
            },
        }

        print(f"✅ Processing completed successfully")
        return response

    except Exception as e:
        error_msg = f"Newsletter generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)


def process_newsletter_in_memory(data, job_id):
    """Process newsletter in memory and update task status"""
    try:
        result = process_newsletter_sync(data)
        in_memory_tasks[job_id] = {
            "status": "completed",
            "result": result,
            "updated_at": datetime.now().isoformat(),
        }
        return result
    except Exception as e:
        in_memory_tasks[job_id] = {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.now().isoformat(),
        }
        raise e


@app.route("/api/status/<job_id>")
def get_job_status(job_id):
    """Get status of a newsletter generation job"""
    # Check in-memory tasks first (for non-Redis mode)
    if job_id in in_memory_tasks:
        task = in_memory_tasks[job_id]
        response = {"job_id": job_id, "status": task["status"]}

        if "result" in task:
            response["result"] = task["result"]
        if "error" in task:
            response["error"] = task["error"]

        return jsonify(response)

    # Fallback to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT params, result, status FROM history WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Job not found"}), 404

    params, result, status = row
    response = {
        "job_id": job_id,
        "status": status,
        "params": json.loads(params) if params else None,
    }

    if result:
        response["result"] = json.loads(result)

    return jsonify(response)


@app.route("/api/history")
def get_history():
    """Get recent newsletter generation history"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, params, result, created_at, status FROM history ORDER BY created_at DESC LIMIT 20"
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        job_id, params, result, created_at, status = row
        history.append(
            {
                "id": job_id,
                "params": json.loads(params) if params else None,
                "result": json.loads(result) if result else None,
                "created_at": created_at,
                "status": status,
            }
        )

    return jsonify(history)


@app.route("/api/schedule", methods=["POST"])
def create_schedule():
    """Create a recurring newsletter schedule"""
    data = request.get_json()

    if not data or not data.get("rrule") or not data.get("email"):
        return jsonify({"error": "Missing required fields: rrule, email"}), 400

    schedule_id = str(uuid.uuid4())

    # Parse RRULE to calculate next_run (simplified for now)
    # In production, use proper RRULE library
    next_run = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schedules (id, params, rrule, next_run) VALUES (?, ?, ?, ?)",
        (schedule_id, json.dumps(data), data["rrule"], next_run),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "scheduled", "schedule_id": schedule_id}), 201


@app.route("/api/schedules")
def get_schedules():
    """Get all active schedules"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, params, rrule, next_run, created_at, enabled FROM schedules WHERE enabled = 1"
    )
    rows = cursor.fetchall()
    conn.close()

    schedules = []
    for row in rows:
        schedule_id, params, rrule, next_run, created_at, enabled = row
        schedules.append(
            {
                "id": schedule_id,
                "params": json.loads(params) if params else None,
                "rrule": rrule,
                "next_run": next_run,
                "created_at": created_at,
                "enabled": bool(enabled),
            }
        )

    return jsonify(schedules)


@app.route("/api/schedule/<schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """Cancel a recurring schedule"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE schedules SET enabled = 0 WHERE id = ?", (schedule_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return jsonify({"error": "Schedule not found"}), 404

    return jsonify({"status": "cancelled"})


@app.route("/health")
def health_check():
    """Health check endpoint for Railway"""
    return jsonify(
        {
            "status": "healthy",
            "redis_connected": redis_conn is not None,
            "database": "sqlite",
        }
    )


@app.route("/test")
def test():
    """Simple test route"""
    return "Flask is working! Template folder: " + str(app.template_folder)


@app.route("/test-template")
def test_template():
    """Test template rendering"""
    try:
        return render_template("test.html")
    except Exception as e:
        return f"Template error: {str(e)}", 500


@app.route("/test-api")
def test_api():
    """API test page"""
    return render_template("test.html")


@app.route("/manual-test")
def manual_test():
    """Manual test page for newsletter generation workflow"""
    return render_template("manual_test.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=True)
