# mypy: ignore-errors
# flake8: noqa
"""Route registration for newsletter generation, status, history, and schedules."""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Callable

from flask import Flask, jsonify, request
from tasks import generate_newsletter_task

try:
    from newsletter_clients import MockNewsletterCLI, RealNewsletterCLI
except ImportError:
    from web.newsletter_clients import (  # pragma: no cover
        MockNewsletterCLI,
        RealNewsletterCLI,
    )


def register_generation_routes(
    app: Flask,
    database_path: str,
    newsletter_cli: Any,
    in_memory_tasks: dict[str, Any],
    task_queue: Any,
    redis_conn: Any,
    real_cli_class: type = RealNewsletterCLI,
    mock_cli_class: type = MockNewsletterCLI,
    get_newsletter_cli: Callable[[], Any] | None = None,
) -> None:
    """Register generation, status, history, and scheduling routes."""

    DATABASE_PATH = database_path
    RealNewsletterCLI = real_cli_class
    MockNewsletterCLI = mock_cli_class

    def resolve_newsletter_cli() -> Any:
        if get_newsletter_cli is None:
            return newsletter_cli
        resolved = get_newsletter_cli()
        return resolved if resolved is not None else newsletter_cli

    @app.route("/api/generate", methods=["POST"])
    def generate_newsletter():
        """Generate newsletter based on keywords or domain with optional email sending"""
        print(f"📨 Newsletter generation request received")

        try:
            data = request.get_json()
            if not data:
                print("❌ No data provided in request")
                return jsonify({"error": "No data provided"}), 400

            # Validate request using Pydantic
            try:
                # Import here to avoid conflicts with Python's built-in types module
                import importlib.util
                import os

                current_dir = os.path.dirname(os.path.abspath(__file__))

                spec = importlib.util.spec_from_file_location(
                    "web_types", os.path.join(current_dir, "types.py")
                )
                web_types = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(web_types)

                validated_data = web_types.GenerateNewsletterRequest(**data)
            except (ValueError, Exception) as e:
                print(f"❌ Validation error: {e}")
                return jsonify({"error": f"Invalid request: {str(e)}"}), 400

            # Extract email for sending
            email = validated_data.email
            send_email = bool(email)

            print(f"📋 Request data: {data}")
            print(f"📧 Send email: {send_email} to {email}")

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
                job = task_queue.enqueue(
                    generate_newsletter_task, data, job_id, send_email
                )
                return jsonify({"job_id": job_id, "status": "queued"}), 202
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
                        print(f"⚙️  Data: {data}")
                        print(f"⚙️  Current time: {datetime.now().isoformat()}")

                        # 환경 체크
                        print(
                            f"⚙️  Using CLI type: {type(resolve_newsletter_cli()).__name__}"
                        )

                        process_newsletter_in_memory(data, job_id)

                        # 메모리에서 결과 가져오기
                        if job_id in in_memory_tasks:
                            task_result = in_memory_tasks[job_id]
                            print(f"💾 Updating database for job {job_id}")
                            print(
                                f"💾 Task status: {task_result.get('status', 'unknown')}"
                            )

                            # Update database with final result
                            conn = sqlite3.connect(DATABASE_PATH)
                            cursor = conn.cursor()

                            if (
                                task_result.get("status") == "completed"
                                and "result" in task_result
                            ):
                                # 성공한 경우
                                try:
                                    result_json = json.dumps(task_result["result"])
                                    cursor.execute(
                                        "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                        (result_json, "completed", job_id),
                                    )
                                    print(
                                        f"💾 Successfully updated database for job {job_id}"
                                    )
                                except (TypeError, ValueError) as json_error:
                                    print(
                                        f"❌ JSON serialization error for job {job_id}: {json_error}"
                                    )
                                    # JSON 직렬화 실패 시 기본 응답 저장
                                    fallback_result = {
                                        "status": "completed",
                                        "title": "Newsletter Generated",
                                        "html_content": task_result["result"].get(
                                            "html_content",
                                            task_result["result"].get(
                                                "content",
                                                "Newsletter content available",
                                            ),
                                        ),
                                        "error": f"JSON serialization failed: {str(json_error)}",
                                    }
                                    cursor.execute(
                                        "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                        (
                                            json.dumps(fallback_result),
                                            "completed",
                                            job_id,
                                        ),
                                    )
                            else:
                                # 실패한 경우
                                error_result = {
                                    "error": task_result.get("error", "Unknown error"),
                                    "status": "failed",
                                }
                                cursor.execute(
                                    "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                    (json.dumps(error_result), "failed", job_id),
                                )

                            conn.commit()
                            conn.close()
                            print(f"✅ Completed background processing for job {job_id}")
                        else:
                            print(f"❌ Job {job_id} not found in in_memory_tasks")
                            # 데이터베이스에 실패 상태 업데이트
                            conn = sqlite3.connect(DATABASE_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                (
                                    json.dumps({"error": "Job not found in memory"}),
                                    "failed",
                                    job_id,
                                ),
                            )
                            conn.commit()
                            conn.close()

                    except Exception as e:
                        print(f"❌ Error in background processing for job {job_id}: {e}")
                        import traceback

                        print(f"❌ Traceback: {traceback.format_exc()}")

                        # Update database with error
                        try:
                            conn = sqlite3.connect(DATABASE_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE history SET result = ?, status = ? WHERE id = ?",
                                (json.dumps({"error": str(e)}), "failed", job_id),
                            )
                            conn.commit()
                            conn.close()
                        except Exception as db_error:
                            print(
                                f"❌ Failed to update database with error for job {job_id}: {db_error}"
                            )

                thread = threading.Thread(target=background_task)
                thread.daemon = True
                thread.start()

                return jsonify({"job_id": job_id, "status": "processing"}), 202

        except Exception as e:
            print(f"❌ Error in generate_newsletter endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/newsletter", methods=["GET"])
    def get_newsletter():
        """Generate newsletter directly with GET parameters"""
        try:
            # 파라미터 추출
            topic = request.args.get("topic", "")
            keywords = request.args.get("keywords", topic)  # topic을 keywords로도 받음
            period = request.args.get("period", 14, type=int)
            template_style = request.args.get("template_style", "compact")

            # 기간 파라미터 검증
            if period not in [1, 7, 14, 30]:
                return (
                    jsonify(
                        {"error": "Invalid period. Must be one of: 1, 7, 14, 30 days"}
                    ),
                    400,
                )

            # 키워드가 없으면 에러
            if not keywords:
                return (
                    jsonify({"error": "Missing required parameter: topic or keywords"}),
                    400,
                )

            print(f"🔍 Newsletter request - Keywords: {keywords}, Period: {period}")

            # 뉴스레터 생성
            active_newsletter_cli = resolve_newsletter_cli()
            result = active_newsletter_cli.generate_newsletter(
                keywords=keywords,
                template_style=template_style,
                email_compatible=False,
                period=period,
            )

            if result["status"] == "success":
                # HTML 응답으로 직접 반환
                return (
                    result["content"],
                    200,
                    {"Content-Type": "text/html; charset=utf-8"},
                )
            else:
                return (
                    jsonify(
                        {
                            "error": f"Newsletter generation failed: {result.get('error', 'Unknown error')}"
                        }
                    ),
                    500,
                )

        except Exception as e:
            print(f"❌ Error in newsletter endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    def process_newsletter_sync(data):
        """Process newsletter synchronously (fallback when Redis is not available)"""
        try:
            print(f"🔄 Starting synchronous newsletter processing")
            active_newsletter_cli = resolve_newsletter_cli()
            print(
                f"📊 Current newsletter_cli type: {type(active_newsletter_cli).__name__}"
            )

            # Extract parameters
            keywords = data.get("keywords", "")
            domain = data.get("domain", "")
            template_style = data.get("template_style", "compact")
            email_compatible = data.get("email_compatible", False)
            period = data.get("period", 14)
            email = data.get("email", "")  # 이메일 주소 추가

            print(f"📋 Processing parameters:")
            print(f"   Keywords: {keywords}")
            print(f"   Domain: {domain}")
            print(f"   Template style: {template_style}")
            print(f"   Email compatible: {email_compatible}")
            print(f"   Period: {period}")
            print(f"   Email: {email}")

            # Use newsletter CLI with proper parameters
            try:
                if keywords:
                    print(
                        f"🔧 Generating newsletter with keywords using {type(active_newsletter_cli).__name__}"
                    )
                    result = active_newsletter_cli.generate_newsletter(
                        keywords=keywords,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                elif domain:
                    print(
                        f"🔧 Generating newsletter with domain using {type(active_newsletter_cli).__name__}"
                    )
                    result = active_newsletter_cli.generate_newsletter(
                        domain=domain,
                        template_style=template_style,
                        email_compatible=email_compatible,
                        period=period,
                    )
                else:
                    raise ValueError("Either keywords or domain must be provided")

                print(f"📊 CLI result status: {result['status']}")
                print(f"📊 CLI result type: {type(result)}")
                print(
                    f"📊 CLI result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                )

            except Exception as cli_error:
                print(f"❌ CLI generation failed: {str(cli_error)}")
                print(f"❌ CLI error type: {type(cli_error).__name__}")
                import traceback

                print(f"❌ CLI error traceback: {traceback.format_exc()}")
                # Set result to error status for fallback logic
                result = {"status": "error", "error": str(cli_error)}

            # Handle different result formats
            if result["status"] == "error":
                # If CLI failed and returned error, try mock as fallback
                if isinstance(active_newsletter_cli, RealNewsletterCLI):
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

            # 이메일 발송 기능 추가
            email_sent = False
            if email and result.get("content") and not data.get("preview_only"):
                try:
                    print(f"📧 Attempting to send email to {email}")
                    # 이메일 발송 - try-except로 import 처리
                    try:
                        import mail

                        send_email_func = mail.send_email
                    except ImportError:
                        try:
                            from . import mail

                            send_email_func = mail.send_email
                        except ImportError:
                            return (
                                jsonify(
                                    {"error": "이메일 모듈을 찾을 수 없습니다. mail.py 파일을 확인해주세요."}
                                ),
                                500,
                            )

                    # 제목 생성
                    subject = result.get("title", "Newsletter")
                    if keywords:
                        subject = f"Newsletter: {keywords}"
                    elif domain:
                        subject = f"Newsletter: {domain} Insights"

                    # 이메일 발송
                    send_email_func(to=email, subject=subject, html=result["content"])
                    email_sent = True
                    print(f"✅ Successfully sent email to {email}")
                except Exception as e:
                    print(f"❌ Failed to send email to {email}: {str(e)}")
                    # 이메일 발송 실패해도 뉴스레터 생성은 성공으로 처리

            response = {
                "status": result.get("status", "error"),
                "html_content": result.get("content", ""),
                "title": result.get("title", "Newsletter"),
                "generation_stats": result.get("generation_stats", {}),
                "input_params": result.get("input_params", {}),
                "error": result.get("error"),
                "sent": email_sent,
                "email_sent": email_sent,
                "subject": result.get("title", "Newsletter"),  # compatibility alias
                "html_size": len(result.get("content", "")),
                "processing_info": {
                    "using_real_cli": isinstance(
                        active_newsletter_cli, RealNewsletterCLI
                    ),
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
            print(f"📊 Starting newsletter processing for job {job_id}")
            result = process_newsletter_sync(data)

            # 메모리에 결과 저장
            in_memory_tasks[job_id] = {
                "status": "completed",
                "result": result,
                "updated_at": datetime.now().isoformat(),
            }

            print(f"📊 Newsletter processing completed for job {job_id}")
            print(f"📊 Result status: {result.get('status', 'unknown')}")
            print(
                f"📊 Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
            )

            return result
        except Exception as e:
            print(f"❌ Error in process_newsletter_in_memory for job {job_id}: {e}")
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
            response = {
                "job_id": job_id,
                "status": task["status"],
                "sent": task.get("sent", False),
            }

            if "result" in task:
                response["result"] = task["result"]
                # Extract sent status from result if available
                if isinstance(task["result"], dict):
                    response["sent"] = task["result"].get("sent", False)
            if "error" in task:
                response["error"] = task["error"]

            return jsonify(response)

        # Fallback to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT params, result, status FROM history WHERE id = ?", (job_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Job not found"}), 404

        params, result, status = row
        response = {
            "job_id": job_id,
            "status": status,
            "params": json.loads(params) if params else None,
            "sent": False,
        }

        if result:
            result_data = json.loads(result)
            response["result"] = result_data
            # Extract sent status from result
            if isinstance(result_data, dict):
                response["sent"] = result_data.get("sent", False)

        return jsonify(response)

    @app.route("/api/history")
    def get_history():
        """Get recent newsletter generation history"""
        print(f"📚 Fetching history from database")

        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # 모든 기록을 가져와서 completed 우선, 최신 순으로 정렬
            cursor.execute(
                """
                SELECT id, params, result, created_at, status
                FROM history
                ORDER BY
                    CASE WHEN status = 'completed' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT 20
            """
            )
            rows = cursor.fetchall()
            conn.close()

            print(f"📚 Found {len(rows)} history records")

        except Exception as e:
            print(f"❌ Database error in get_history: {e}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500

        history = []
        for row in rows:
            job_id, params, result, created_at, status = row
            print(f"📚 Processing history record: {job_id} (status: {status})")

            try:
                parsed_params = json.loads(params) if params else None
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse params for job {job_id}: {e}")
                parsed_params = None

            try:
                parsed_result = json.loads(result) if result else None
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse result for job {job_id}: {e}")
                parsed_result = None

            history.append(
                {
                    "id": job_id,
                    "params": parsed_params,
                    "result": parsed_result,
                    "created_at": created_at,
                    "status": status,
                }
            )

        print(f"📚 Returning {len(history)} history records")
        return jsonify(history)

    @app.route("/api/schedule", methods=["POST"])
    def create_schedule():
        """Create a recurring newsletter schedule"""
        data = request.get_json()

        if not data or not data.get("rrule") or not data.get("email"):
            return jsonify({"error": "Missing required fields: rrule, email"}), 400

        # Keywords나 domain 중 하나는 필수
        if not data.get("keywords") and not data.get("domain"):
            return jsonify({"error": "Either keywords or domain is required"}), 400

        try:
            # RRULE 파싱 및 다음 실행 시간 계산
            from dateutil.rrule import rrulestr

            rrule_str = data["rrule"]
            rrule = rrulestr(rrule_str, dtstart=datetime.now())
            next_run = rrule.after(datetime.now())

            if not next_run:
                return jsonify({"error": "Invalid RRULE: no future occurrences"}), 400

        except Exception as e:
            return jsonify({"error": f"Invalid RRULE: {str(e)}"}), 400

        schedule_id = str(uuid.uuid4())

        # 스케줄 데이터 준비
        schedule_params = {
            "keywords": data.get("keywords"),
            "domain": data.get("domain"),
            "email": data["email"],
            "template_style": data.get("template_style", "compact"),
            "email_compatible": data.get("email_compatible", True),
            "period": data.get("period", 14),
        }

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schedules (id, params, rrule, next_run) VALUES (?, ?, ?, ?)",
            (schedule_id, json.dumps(schedule_params), rrule_str, next_run.isoformat()),
        )
        conn.commit()
        conn.close()

        return (
            jsonify(
                {
                    "status": "scheduled",
                    "schedule_id": schedule_id,
                    "next_run": next_run.isoformat(),
                }
            ),
            201,
        )

    @app.route("/api/schedules")
    def get_schedules():
        """Get all active schedules"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, params, rrule, next_run, created_at, enabled FROM schedules WHERE enabled = 1 ORDER BY next_run ASC"
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

    @app.route("/api/schedule/<schedule_id>/run", methods=["POST"])
    def run_schedule_now(schedule_id):
        """Immediately execute a scheduled newsletter"""
        try:
            # 스케줄 정보 조회
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT params, enabled FROM schedules WHERE id = ?", (schedule_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return jsonify({"error": "Schedule not found"}), 404

            params_json, enabled = row
            if not enabled:
                return jsonify({"error": "Schedule is disabled"}), 400

            params = json.loads(params_json)

            # 즉시 뉴스레터 생성 작업 큐에 추가
            if redis_conn and task_queue:
                immediate_job_id = f"schedule_{schedule_id}_{uuid.uuid4().hex[:8]}"
                job = task_queue.enqueue(
                    generate_newsletter_task,
                    params,
                    immediate_job_id,
                    params.get("send_email", False),
                    job_timeout="10m",
                )

                return jsonify(
                    {
                        "status": "queued",
                        "job_id": job.id,
                        "message": "Newsletter generation started",
                    }
                )
            else:
                # Redis가 없는 경우 직접 실행
                immediate_job_id = f"schedule_{schedule_id}_{uuid.uuid4().hex[:8]}"
                result = generate_newsletter_task(
                    params,
                    immediate_job_id,
                    params.get("send_email", False),
                )
                return jsonify({"status": "completed", "result": result})

        except Exception as e:
            logging.error(f"Failed to run schedule {schedule_id}: {e}")
            return jsonify({"error": f"Failed to execute schedule: {str(e)}"}), 500
