from __future__ import annotations

from datetime import datetime, timezone

import pytest

from web.ops_logging import build_log_message


@pytest.mark.unit
def test_build_log_message_sorts_and_serializes_fields() -> None:
    message = build_log_message(
        "schedule.execute.started",
        schedule_id="sched-1",
        params={"keywords": ["AI"]},
        intended_run_at=datetime(2026, 3, 8, 12, 30, tzinfo=timezone.utc),
        ignored=None,
    )

    assert message.startswith("schedule.execute.started ")
    assert "intended_run_at=2026-03-08T12:30:00+00:00" in message
    assert 'params={"keywords": ["AI"]}' in message
    assert 'schedule_id="sched-1"' in message
    assert "ignored=" not in message
