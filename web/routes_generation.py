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

try:
    from tasks import generate_newsletter_task
except ImportError:
    from web.tasks import generate_newsletter_task  # pragma: no cover

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

try:
    from time_utils import get_utc_now, parse_sqlite_timestamp, to_iso_utc, to_utc
except ImportError:
    from web.time_utils import (  # pragma: no cover
        get_utc_now,
        parse_sqlite_timestamp,
        to_iso_utc,
        to_utc,
    )

try:
    from ops_logging import log_debug, log_exception, log_info
except ImportError:
    from web.ops_logging import log_debug, log_exception, log_info  # pragma: no cover

try:
    from analytics import record_schedule_event
except ImportError:
    from web.analytics import record_schedule_event  # pragma: no cover

try:
    from generation_route_actions import (
        build_generation_dispatch_action,
        build_schedule_create_action,
        build_schedule_run_completed_action,
        build_schedule_run_dispatch_action,
        build_schedule_run_failed_action,
        build_schedule_run_queued_action,
        build_schedule_run_requested_action,
        build_sync_email_action,
    )
except ImportError:
    from web.generation_route_actions import (  # pragma: no cover
        build_generation_dispatch_action,
        build_schedule_create_action,
        build_schedule_run_completed_action,
        build_schedule_run_dispatch_action,
        build_schedule_run_failed_action,
        build_schedule_run_queued_action,
        build_schedule_run_requested_action,
        build_sync_email_action,
    )

try:
    from generation_route_dispatch import (
        GenerationJobResolution,
        ScheduleRunResolution,
        build_generation_dispatch_plan,
        build_generation_job_response,
        build_in_memory_completed_task,
        build_in_memory_failed_task,
        build_in_memory_processing_task,
        build_schedule_created_response,
        build_schedule_entry,
        build_schedule_run_resolution,
        build_schedule_run_response,
    )
except ImportError:
    from web.generation_route_dispatch import (  # pragma: no cover
        GenerationJobResolution,
        ScheduleRunResolution,
        build_generation_dispatch_plan,
        build_generation_job_response,
        build_in_memory_completed_task,
        build_in_memory_failed_task,
        build_in_memory_processing_task,
        build_schedule_created_response,
        build_schedule_entry,
        build_schedule_run_resolution,
        build_schedule_run_response,
    )

try:
    from generation_route_support import (
        build_generate_request_context,
        build_generation_invoke_plan,
        build_history_entry,
        build_status_response_from_row,
        build_status_response_from_task,
        build_sync_email_subject,
        build_sync_generation_options,
        build_sync_generation_response,
        parse_preview_request,
        parse_schedule_create_request,
        validate_generate_request,
    )
except ImportError:
    from web.generation_route_support import (  # pragma: no cover
        build_generate_request_context,
        build_generation_invoke_plan,
        build_history_entry,
        build_status_response_from_row,
        build_status_response_from_task,
        build_sync_email_subject,
        build_sync_generation_options,
        build_sync_generation_response,
        parse_preview_request,
        parse_schedule_create_request,
        validate_generate_request,
    )

logger = logging.getLogger("web.routes_generation")


def _resolve_generation_job(
    *,
    payload: dict[str, Any],
    database_path: str,
    provided_idempotency_key: str | None,
) -> GenerationJobResolution:
    idempotency_enabled = is_feature_enabled("WEB_IDEMPOTENCY_ENABLED", default=True)
    idempotency_key = build_idempotency_key(
        payload=payload,
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
        db_path=database_path,
        job_id=proposed_job_id,
        params=payload,
        idempotency_key=idempotency_key if idempotency_enabled else None,
        status="pending",
    )
    return GenerationJobResolution(
        job_id=job_id,
        deduplicated=deduplicated,
        stored_status=stored_status,
        idempotency_key=idempotency_key,
        effective_idempotency_key=idempotency_key if idempotency_enabled else None,
    )


def _dispatch_generation_job(
    *,
    app: Flask,
    payload: dict[str, Any],
    resolution: GenerationJobResolution,
    send_email: bool,
    database_path: str,
    in_memory_tasks: dict[str, Any],
    task_queue: Any,
    run_in_memory_job: Callable[..., None],
) -> dict[str, Any]:
    dispatch_plan = build_generation_dispatch_plan(
        has_task_queue=task_queue is not None,
        is_testing=bool(app.config.get("TESTING", False)),
    )
    dispatch_action = build_generation_dispatch_action(
        dispatch_via=dispatch_plan.via,
        response_status=dispatch_plan.response_status,
        should_start_in_memory_thread=dispatch_plan.should_start_in_memory_thread,
        payload=payload,
        job_id=resolution.job_id,
        send_email=send_email,
        task_idempotency_key=resolution.effective_idempotency_key,
        response_idempotency_key=resolution.idempotency_key,
        database_path=database_path,
        started_at=datetime.now().isoformat(),
        build_processing_task_fn=build_in_memory_processing_task,
    )

    if dispatch_action.via == "redis":
        log_info(
            logger,
            "generate.job.queued",
            job_id=resolution.job_id,
            via=dispatch_action.via,
        )
        task_queue.enqueue(
            generate_newsletter_task,
            *dispatch_action.task_call.args,
            **dispatch_action.task_call.queue_kwargs,
        )
        return build_generation_job_response(
            resolution=resolution,
            status=dispatch_plan.response_status,
            deduplicated=False,
        )

    log_info(
        logger, "generate.job.queued", job_id=resolution.job_id, via=dispatch_plan.via
    )
    in_memory_tasks[resolution.job_id] = dispatch_action.processing_task

    if dispatch_action.thread_kwargs is not None:
        thread = threading.Thread(
            target=run_in_memory_job,
            kwargs=dispatch_action.thread_kwargs,
            daemon=True,
        )
        thread.start()

    return build_generation_job_response(
        resolution=resolution,
        status=dispatch_plan.response_status,
        deduplicated=False,
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
    get_task_queue: Callable[[], Any] | None = None,
    get_redis_conn: Callable[[], Any] | None = None,
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

    def resolve_task_queue() -> Any:
        if get_task_queue is None:
            return task_queue
        resolved = get_task_queue()
        return resolved if resolved is not None else task_queue

    def resolve_redis_conn() -> Any:
        if get_redis_conn is None:
            return redis_conn
        resolved = get_redis_conn()
        return resolved if resolved is not None else redis_conn

    def _serialize_schedule_timestamp(value: str | None) -> str | None:
        if not value:
            return None
        return to_iso_utc(parse_sqlite_timestamp(value))

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
            in_memory_tasks[job_id] = build_in_memory_completed_task(
                result=result,
                updated_at=datetime.now().isoformat(),
            )
        except Exception as exc:
            in_memory_tasks[job_id] = build_in_memory_failed_task(
                error=str(exc),
                updated_at=datetime.now().isoformat(),
            )

    @app.route("/api/generate", methods=["POST"])
    def generate_newsletter():
        """Generate newsletter based on keywords or domain with optional email sending"""
        try:
            data = request.get_json()
            if not data:
                log_info(logger, "generate.request.empty")
                return jsonify({"error": "No data provided"}), 400

            try:
                validated_data = validate_generate_request(data)
            except Exception as e:
                log_exception(logger, "generate.request.invalid", e)
                return jsonify({"error": f"Invalid request: {str(e)}"}), 400

            request_context = build_generate_request_context(validated_data)
            log_info(
                logger,
                "generate.request.received",
                has_domain=request_context.has_domain,
                has_keywords=request_context.has_keywords,
                email=request_context.email,
                send_email=request_context.send_email,
            )
            log_debug(logger, "generate.request.payload", payload=data)

            resolution = _resolve_generation_job(
                payload=data,
                database_path=DATABASE_PATH,
                provided_idempotency_key=request.headers.get("Idempotency-Key"),
            )
            log_info(
                logger,
                "generate.job.resolved",
                job_id=resolution.job_id,
                deduplicated=resolution.deduplicated,
                idempotency_key=resolution.idempotency_key,
                stored_status=resolution.stored_status,
            )

            if resolution.deduplicated:
                return (
                    jsonify(
                        build_generation_job_response(
                            resolution=resolution,
                            status=resolution.stored_status,
                            deduplicated=True,
                        )
                    ),
                    202,
                )

            response_payload = _dispatch_generation_job(
                app=app,
                payload=data,
                resolution=resolution,
                send_email=request_context.send_email,
                database_path=DATABASE_PATH,
                in_memory_tasks=in_memory_tasks,
                task_queue=resolve_task_queue(),
                run_in_memory_job=run_in_memory_job,
            )
            return (
                jsonify(response_payload),
                202,
            )

        except Exception as e:
            log_exception(logger, "generate.request.failed", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/newsletter", methods=["GET"])
    def get_newsletter():
        """Generate newsletter directly with GET parameters"""
        try:
            try:
                preview_request = parse_preview_request(request.args.to_dict(flat=True))
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

            log_info(
                logger,
                "newsletter.preview.requested",
                keywords=preview_request.keywords,
                period=preview_request.period,
                template_style=preview_request.template_style,
            )

            # 뉴스레터 생성
            active_newsletter_cli = resolve_newsletter_cli()
            result = active_newsletter_cli.generate_newsletter(
                keywords=preview_request.keywords,
                template_style=preview_request.template_style,
                email_compatible=False,
                period=preview_request.period,
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
            log_exception(logger, "newsletter.preview.failed", e)
            return jsonify({"error": str(e)}), 500

    def process_newsletter_sync(data):
        """Process newsletter synchronously (fallback when Redis is not available)"""
        try:
            active_newsletter_cli = resolve_newsletter_cli()
            log_info(
                logger,
                "generate.sync.started",
                cli_type=type(active_newsletter_cli).__name__,
            )

            options = build_sync_generation_options(data)

            log_debug(
                logger,
                "generate.sync.parameters",
                keywords=options.keywords,
                domain=options.domain,
                template_style=options.template_style,
                email_compatible=options.email_compatible,
                period=options.period,
                email=options.email,
            )

            # Use newsletter CLI with proper parameters
            try:
                invoke_plan = build_generation_invoke_plan(options)
                log_info(
                    logger,
                    "generate.sync.invoke",
                    mode=invoke_plan.mode,
                    cli_type=type(active_newsletter_cli).__name__,
                )
                result = active_newsletter_cli.generate_newsletter(**invoke_plan.kwargs)

                log_info(
                    logger,
                    "generate.sync.result",
                    status=result.get("status"),
                    result_type=type(result).__name__,
                    result_keys=(
                        list(result.keys()) if isinstance(result, dict) else None
                    ),
                )

            except Exception as cli_error:
                import traceback

                log_exception(
                    logger,
                    "generate.sync.cli_failed",
                    cli_error,
                    traceback=traceback.format_exc(),
                )
                # Set result to error status for fallback logic
                result = {"status": "error", "error": str(cli_error)}

            # Handle different result formats
            if result["status"] == "error":
                # If CLI failed and returned error, try mock as fallback
                if isinstance(active_newsletter_cli, RealNewsletterCLI):
                    log_info(logger, "generate.sync.fallback_mock")
                    mock_cli = MockNewsletterCLI()
                    fallback_plan = build_generation_invoke_plan(options)
                    result = mock_cli.generate_newsletter(**fallback_plan.kwargs)
                    log_info(
                        logger,
                        "generate.sync.fallback_result",
                        status=result.get("status"),
                    )

            # 이메일 발송 기능 추가
            email_sent = False
            email_action = build_sync_email_action(
                email=options.email,
                preview_only=options.preview_only,
                result=result,
                keywords=options.keywords,
                domain=options.domain,
                subject_builder=build_sync_email_subject,
            )
            if email_action is not None:
                try:
                    log_info(
                        logger,
                        "generate.sync.email_sending",
                        email=email_action.to,
                    )
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

                    # 이메일 발송
                    send_email_func(
                        to=email_action.to,
                        subject=email_action.subject,
                        html=email_action.html,
                    )
                    email_sent = True
                    log_info(
                        logger,
                        "generate.sync.email_sent",
                        email=email_action.to,
                    )
                except Exception as e:
                    log_exception(
                        logger,
                        "generate.sync.email_failed",
                        e,
                        email=email_action.to,
                    )
                    # 이메일 발송 실패해도 뉴스레터 생성은 성공으로 처리

            response = build_sync_generation_response(
                result,
                using_real_cli=isinstance(active_newsletter_cli, RealNewsletterCLI),
                template_style=options.template_style,
                email_compatible=options.email_compatible,
                period=options.period,
                email_sent=email_sent,
            )

            log_info(
                logger,
                "generate.sync.completed",
                status=response["status"],
                email_sent=email_sent,
            )
            return response

        except Exception as e:
            error_msg = f"Newsletter generation failed: {str(e)}"
            log_exception(logger, "generate.sync.failed", e)
            raise Exception(error_msg)

    def process_newsletter_in_memory(data, job_id):
        """Process newsletter in memory and update task status"""
        try:
            log_info(logger, "generate.in_memory.started", job_id=job_id)
            result = process_newsletter_sync(data)

            # 메모리에 결과 저장
            in_memory_tasks[job_id] = build_in_memory_completed_task(
                result=result,
                updated_at=datetime.now().isoformat(),
            )

            log_info(
                logger,
                "generate.in_memory.completed",
                job_id=job_id,
                status=result.get("status", "unknown"),
                result_keys=list(result.keys()) if isinstance(result, dict) else None,
            )

            return result
        except Exception as e:
            log_exception(logger, "generate.in_memory.failed", e, job_id=job_id)
            in_memory_tasks[job_id] = build_in_memory_failed_task(
                error=str(e),
                updated_at=datetime.now().isoformat(),
            )
            raise e

    def _parse_optional_json(
        raw_value: str | None, *, job_id: str, field_name: str
    ) -> Any:
        if not raw_value:
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            log_exception(
                logger,
                f"{field_name}.parse_failed",
                exc,
                job_id=job_id,
            )
            return None

    def _load_job_status_row(job_id: str) -> tuple[Any, ...] | None:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    params,
                    result,
                    status,
                    idempotency_key,
                    approval_status,
                    delivery_status,
                    approved_at,
                    rejected_at,
                    approval_note
                FROM history
                WHERE id = ?
                """,
                (job_id,),
            )
            return cursor.fetchone()
        finally:
            conn.close()

    def _load_recent_history_rows(limit: int = 20) -> list[tuple[Any, ...]]:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, params, result, created_at, status, idempotency_key
                     , approval_status, delivery_status, approved_at, rejected_at, approval_note
                FROM history
                ORDER BY
                    CASE WHEN approval_status = 'pending' THEN 0 ELSE 1 END,
                    CASE WHEN status = 'completed' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def _compute_schedule_next_run(rrule_str: str) -> datetime:
        from dateutil.rrule import rrulestr

        now_utc = get_utc_now()
        rrule = rrulestr(rrule_str, dtstart=now_utc.replace(tzinfo=None))
        next_run = rrule.after(now_utc.replace(tzinfo=None))
        if not next_run:
            raise ValueError("Invalid RRULE: no future occurrences")
        return to_utc(next_run)

    def _list_active_schedules() -> list[dict[str, Any]]:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, params, rrule, next_run, created_at, enabled FROM schedules WHERE enabled = 1 ORDER BY next_run ASC"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        schedules = []
        for row in rows:
            schedules.append(
                build_schedule_entry(
                    row,
                    parse_params=lambda raw, schedule_id=row[0]: _parse_optional_json(
                        raw,
                        job_id=schedule_id,
                        field_name="schedule.params",
                    ),
                    serialize_timestamp=_serialize_schedule_timestamp,
                )
            )
        return schedules

    def _load_schedule_run_payload(
        schedule_id: str,
    ) -> tuple[dict[str, Any], int] | None:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT params, enabled FROM schedules WHERE id = ?", (schedule_id,)
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        params_json, enabled = row
        params = _parse_optional_json(
            params_json, job_id=schedule_id, field_name="schedule.run_now.params"
        )
        return (params or {}, int(enabled))

    def _resolve_schedule_run(
        schedule_id: str, params: dict[str, Any]
    ) -> ScheduleRunResolution:
        intended_run_at = get_utc_now()
        idempotency_enabled = is_feature_enabled(
            "WEB_IDEMPOTENCY_ENABLED", default=True
        )
        return build_schedule_run_resolution(
            schedule_id=schedule_id,
            params=params,
            intended_run_at=intended_run_at,
            idempotency_enabled=idempotency_enabled,
            schedule_idempotency_key_builder=build_schedule_idempotency_key,
            derive_job_id_fn=derive_job_id,
            to_iso_utc_fn=to_iso_utc,
        )

    def _dispatch_schedule_run(resolution: ScheduleRunResolution) -> dict[str, Any]:
        active_redis_conn = resolve_redis_conn()
        active_task_queue = resolve_task_queue()
        dispatch_action = build_schedule_run_dispatch_action(
            params=resolution.params,
            immediate_job_id=resolution.immediate_job_id,
            effective_idempotency_key=resolution.effective_idempotency_key,
            database_path=DATABASE_PATH,
            has_async_runtime=bool(active_redis_conn and active_task_queue),
        )

        if dispatch_action.mode == "queued":
            job = active_task_queue.enqueue(
                generate_newsletter_task,
                *dispatch_action.task_call.args,
                **dispatch_action.task_call.queue_kwargs,
            )
            queued_event = build_schedule_run_queued_action(
                schedule_id=resolution.schedule_id,
                job_id=resolution.immediate_job_id,
                queue_job_id=job.id,
            )
            record_schedule_event(DATABASE_PATH, **queued_event.as_record_kwargs())
            return build_schedule_run_response(
                resolution=resolution,
                status="queued",
            )

        result = generate_newsletter_task(
            *dispatch_action.task_call.args,
        )
        completed_event = build_schedule_run_completed_action(
            schedule_id=resolution.schedule_id,
            job_id=resolution.immediate_job_id,
            result_status=result.get("status"),
        )
        record_schedule_event(DATABASE_PATH, **completed_event.as_record_kwargs())
        return build_schedule_run_response(
            resolution=resolution,
            status="completed",
            result=result,
        )

    @app.route("/api/status/<job_id>")
    def get_job_status(job_id):
        """Get status of a newsletter generation job"""
        if job_id in in_memory_tasks:
            return jsonify(
                build_status_response_from_task(job_id, in_memory_tasks[job_id])
            )

        row = _load_job_status_row(job_id)

        if not row:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(
            build_status_response_from_row(
                job_id,
                row,
                parse_params=lambda raw: _parse_optional_json(
                    raw,
                    job_id=job_id,
                    field_name="status.params",
                ),
                parse_result=lambda raw: _parse_optional_json(
                    raw,
                    job_id=job_id,
                    field_name="status.result",
                ),
            )
        )

    @app.route("/api/history")
    def get_history():
        """Get recent newsletter generation history"""
        try:
            rows = _load_recent_history_rows()
            log_info(logger, "history.loaded", count=len(rows))
        except Exception as e:
            log_exception(logger, "history.load_failed", e)
            return jsonify({"error": f"Database error: {str(e)}"}), 500

        history = [
            build_history_entry(
                row,
                parse_params=lambda raw, job_id=row[0]: _parse_optional_json(
                    raw,
                    job_id=job_id,
                    field_name="history.params",
                ),
                parse_result=lambda raw, job_id=row[0]: _parse_optional_json(
                    raw,
                    job_id=job_id,
                    field_name="history.result",
                ),
            )
            for row in rows
        ]
        log_info(logger, "history.returned", count=len(history))
        return jsonify(history)

    @app.route("/api/schedule", methods=["POST"])
    def create_schedule():
        """Create a recurring newsletter schedule"""
        data = request.get_json()
        try:
            schedule_request = parse_schedule_create_request(data)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        rrule_str = schedule_request.rrule
        try:
            next_run_utc = _compute_schedule_next_run(rrule_str)
        except Exception as e:
            return jsonify({"error": f"Invalid RRULE: {str(e)}"}), 400

        schedule_id = str(uuid.uuid4())
        next_run_iso = to_iso_utc(next_run_utc)
        schedule_create_action = build_schedule_create_action(
            schedule_id=schedule_id,
            params=schedule_request.params,
            rrule=rrule_str,
            next_run_iso=next_run_iso,
            is_test=schedule_request.is_test,
            expires_at=schedule_request.expires_at,
        )

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO schedules (id, params, rrule, next_run, is_test, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            schedule_create_action.insert_values,
        )
        conn.commit()
        conn.close()
        record_schedule_event(
            DATABASE_PATH,
            **schedule_create_action.created_event.as_record_kwargs(),
        )
        return (
            jsonify(
                build_schedule_created_response(
                    schedule_id=schedule_id,
                    next_run=next_run_iso,
                )
            ),
            201,
        )

    @app.route("/api/schedules")
    def get_schedules():
        """Get all active schedules"""
        return jsonify(_list_active_schedules())

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
            loaded_schedule = _load_schedule_run_payload(schedule_id)
            if loaded_schedule is None:
                return jsonify({"error": "Schedule not found"}), 404

            params, enabled = loaded_schedule
            if not enabled:
                return jsonify({"error": "Schedule is disabled"}), 400

            resolution = _resolve_schedule_run(schedule_id, params)
            requested_event = build_schedule_run_requested_action(
                schedule_id=schedule_id,
                job_id=resolution.immediate_job_id,
                idempotency_key=resolution.idempotency_key,
            )
            record_schedule_event(DATABASE_PATH, **requested_event.as_record_kwargs())
            return jsonify(_dispatch_schedule_run(resolution))

        except Exception as e:
            if locals().get("resolution"):
                failed_event = build_schedule_run_failed_action(
                    schedule_id=schedule_id,
                    job_id=locals()["resolution"].immediate_job_id,
                    error=str(e),
                )
                record_schedule_event(DATABASE_PATH, **failed_event.as_record_kwargs())
            log_exception(logger, "schedule.run_now.failed", e, schedule_id=schedule_id)
            return jsonify({"error": f"Failed to execute schedule: {str(e)}"}), 500
