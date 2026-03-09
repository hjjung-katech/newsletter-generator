from __future__ import annotations

import json
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_history import (  # noqa: E402
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_PENDING,
    DELIVERY_STATUS_APPROVED,
    DELIVERY_STATUS_PENDING_APPROVAL,
    build_idempotency_key,
    create_or_get_history_job,
    derive_job_id,
    get_history_row,
    get_history_row_by_idempotency_key,
    update_history_review_state,
    update_history_status,
)


def test_create_or_get_history_job_deduplicates_by_idempotency_key(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    params = {"email": "ops@example.com", "require_approval": True}
    idempotency_key = build_idempotency_key(params, namespace="generate")

    first_job_id, deduplicated, stored_status = create_or_get_history_job(
        str(db_path),
        derive_job_id(idempotency_key),
        params,
        idempotency_key,
        status="pending",
    )
    second_job_id, second_deduplicated, second_status = create_or_get_history_job(
        str(db_path),
        "job_should_not_replace_existing",
        params,
        idempotency_key,
        status="pending",
    )

    assert deduplicated is False
    assert stored_status == "pending"
    assert second_deduplicated is True
    assert second_job_id == first_job_id
    assert second_status == "pending"

    row = get_history_row_by_idempotency_key(str(db_path), idempotency_key)
    assert row is not None
    assert row["approval_status"] == APPROVAL_STATUS_PENDING
    assert row["delivery_status"] == DELIVERY_STATUS_PENDING_APPROVAL


def test_update_history_status_and_review_state_persist_expected_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    job_id = "job-review-state"
    params = {"email": "ops@example.com", "keywords": ["AI"]}

    update_history_status(
        str(db_path),
        job_id,
        "completed",
        result={"html_content": "<html>ok</html>", "title": "History"},
        params=params,
        idempotency_key="generate:test-history",
    )
    update_history_review_state(
        str(db_path),
        job_id,
        approval_status=APPROVAL_STATUS_APPROVED,
        delivery_status=DELIVERY_STATUS_APPROVED,
        approved_at="2026-03-09T10:00:00Z",
        approval_note="approved by test",
    )

    row = get_history_row(str(db_path), job_id)
    assert row is not None
    assert row["status"] == "completed"
    assert json.loads(str(row["result"]))["title"] == "History"
    assert row["approval_status"] == APPROVAL_STATUS_APPROVED
    assert row["delivery_status"] == DELIVERY_STATUS_APPROVED
    assert row["approved_at"] == "2026-03-09T10:00:00Z"
    assert row["approval_note"] == "approved by test"
