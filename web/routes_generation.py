# mypy: ignore-errors
# flake8: noqa
"""Route registration for newsletter generation, status, history, and schedules."""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Any, Callable

from flask import Flask, jsonify, request
from tasks import generate_newsletter_task

try:
    from db_state import (
        build_idempotency_key,
        build_schedule_idempotency_key,
        create_or_get_history_job,
        derive_job_id,
        ensure_database_schema,
        is_feature_enabled,
    )
except ImportError:
    from web.db_state import (  # pragma: no cover
        build_idempotency_key,
        build_schedule_idempotency_key,
        create_or_get_history_job,
        derive_job_id,
        ensure_database_schema,
        is_feature_enabled,
    )

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
    ensure_database_schema(DATABASE_PATH)

    def resolve_newsletter_cli() -> Any:
        if get_newsletter_cli is None:
            return newsletter_cli
        resolved = get_newsletter_cli()
        return resolved if resolved is not None else newsletter_cli

    def run_in_memory_job(
        job_id: str,
        data: dict[str, Any],
        send_email: bool,
        idempotency_key: str | None,
    ) -> None:
        try:
            result = generate_newsletter_task(
                data,
                job_id,
                send_email,
                idempotency_key,
                DATABASE_PATH,
            )
            in_memory_tasks[job_id] = {
                "status": "completed",
                "result": result,
                "updated_at": datetime.now().isoformat(),
            }
        except Exception as exc:
            in_memory_tasks[job_id] = {
                "status": "failed",
                "error": str(exc),
                "updated_at": datetime.now().isoformat(),
            }

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
                    "web.types", os.path.join(current_dir, "types.py")
                )
                web_types_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(web_types_module)

                validated_data = web_types_module.GenerateNewsletterRequest(**data)
            except (ValueError, Exception) as e:
                print(f"❌ Validation error: {e}")
                return jsonify({"error": f"Invalid request: {str(e)}"}), 400

            # Extract email for sending
            email = validated_data.email
            send_email = bool(email)

            print(f"📋 Request data: {data}")
            print(f"📧 Send email: {send_email} to {email}")

            idempotency_enabled = is_feature_enabled(
                "WEB_IDEMPOTENCY_ENABLED", default=True
            )
            provided_idempotency_key = request.headers.get("Idempotency-Key")
            idempotency_key = build_idempotency_key(
                payload=data,
                provided_key=provided_idempotency_key,
                namespace="generate",
            )
            if not idempotency_enabled:
                idempotency_key = f"generate:{uuid.uuid4()}"

            proposed_job_id = (
                derive_job_id(idempotency_key, prefix="job")
                if idempotency_enabled
                else str(uuid.uuid4())
            )
            job_id, deduplicated, stored_status = create_or_get_history_job(
                db_path=DATABASE_PATH,
                job_id=proposed_job_id,
                params=data,
                idempotency_key=idempotency_key if idempotency_enabled else None,
                status="pending",
            )
            print(f"🆔 Resolved job ID: {job_id} (deduplicated={deduplicated})")

            if deduplicated:
                return (
                    jsonify(
                        {
                            "job_id": job_id,
                            "status": stored_status,
                            "deduplicated": True,
                            "idempotency_key": idempotency_key,
                        }
                    ),
                    202,
                )

            if task_queue:
                print("📤 Queueing task with Redis")
                task_queue.enqueue(
                    generate_newsletter_task,
                    data,
                    job_id,
                    send_email,
                    idempotency_key if idempotency_enabled else None,
                    DATABASE_PATH,
                    job_id=job_id,
                )
                return (
                    jsonify(
                        {
                            "job_id": job_id,
                            "status": "queued",
                            "deduplicated": False,
                            "idempotency_key": idempotency_key,
                        }
                    ),
                    202,
                )

            print("🔄 Processing in-memory (Redis not available)")
            in_memory_tasks[job_id] = {
                "status": "processing",
                "started_at": datetime.now().isoformat(),
                "idempotency_key": idempotency_key,
            }

            if not app.config.get("TESTING", False):
                thread = threading.Thread(
                    target=run_in_memory_job,
                    kwargs={
                        "job_id": job_id,
                        "data": data,
                        "send_email": send_email,
                        "idempotency_key": (
                            idempotency_key if idempotency_enabled else None
                        ),
                    },
                    daemon=True,
                )
                thread.start()

            return (
                jsonify(
                    {
                        "job_id": job_id,
                        "status": "processing",
                        "deduplicated": False,
                        "idempotency_key": idempotency_key,
                    }
                ),
                202,
            )

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
                "idempotency_key": task.get("idempotency_key"),
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
            "SELECT params, result, status, idempotency_key FROM history WHERE id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Job not found"}), 404

        params, result, status, idempotency_key = row
        response = {
            "job_id": job_id,
            "status": status,
            "params": json.loads(params) if params else None,
            "sent": False,
            "idempotency_key": idempotency_key,
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
                SELECT id, params, result, created_at, status, idempotency_key
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
            job_id, params, result, created_at, status, idempotency_key = row
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
                    "idempotency_key": idempotency_key,
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
            "send_email": True,
        }
        is_test = bool(data.get("is_test", False))
        expires_at = data.get("expires_at")

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO schedules (id, params, rrule, next_run, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                schedule_id,
                json.dumps(schedule_params),
                rrule_str,
                next_run.isoformat(),
                int(is_test),
                expires_at,
            ),
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
            intended_run_at = datetime.now()
            idempotency_enabled = is_feature_enabled(
                "WEB_IDEMPOTENCY_ENABLED", default=True
            )
            idempotency_key = build_schedule_idempotency_key(
                schedule_id=schedule_id,
                intended_run_at=intended_run_at,
            )
            if not idempotency_enabled:
                idempotency_key = (
                    f"schedule:{schedule_id}:{intended_run_at.isoformat()}"
                )
            job_suffix = derive_job_id(idempotency_key, prefix="sched").split("_", 1)[1]
            immediate_job_id = f"schedule_{schedule_id}_{job_suffix}"

            # 즉시 뉴스레터 생성 작업 큐에 추가
            if redis_conn and task_queue:
                job = task_queue.enqueue(
                    generate_newsletter_task,
                    params,
                    immediate_job_id,
                    params.get("send_email", False),
                    idempotency_key if idempotency_enabled else None,
                    DATABASE_PATH,
                    job_id=immediate_job_id,
                    job_timeout="10m",
                )

                return jsonify(
                    {
                        "status": "queued",
                        "job_id": immediate_job_id,
                        "message": "Newsletter generation started",
                        "idempotency_key": idempotency_key,
                    }
                )
            else:
                # Redis가 없는 경우 직접 실행
                result = generate_newsletter_task(
                    params,
                    immediate_job_id,
                    params.get("send_email", False),
                    idempotency_key if idempotency_enabled else None,
                    DATABASE_PATH,
                )
                return jsonify(
                    {
                        "status": "completed",
                        "result": result,
                        "job_id": immediate_job_id,
                        "idempotency_key": idempotency_key,
                    }
                )

        except Exception as e:
            logging.error(f"Failed to run schedule {schedule_id}: {e}")
            return jsonify({"error": f"Failed to execute schedule: {str(e)}"}), 500
