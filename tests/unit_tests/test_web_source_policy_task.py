from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_state import create_source_policy, ensure_database_schema  # noqa: E402
from tasks import generate_newsletter_task  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def test_generate_newsletter_task_loads_active_source_policies(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))
    create_source_policy(
        str(db_path),
        "policy_allow",
        "reuters.com",
        "allow",
        is_active=True,
    )
    create_source_policy(
        str(db_path),
        "policy_block",
        "spam.example",
        "block",
        is_active=True,
    )

    with patch("tasks.generate_newsletter") as generate_mock:
        generate_mock.return_value = {
            "status": "success",
            "html_content": "<html><head><title>Smoke</title></head><body>ok</body></html>",
            "title": "Smoke",
            "generation_stats": {},
            "input_params": {},
            "error": None,
        }

        result = generate_newsletter_task(
            {"keywords": ["AI"]},
            "job-source-policy",
            database_path=str(db_path),
        )

    request = generate_mock.call_args.args[0]
    assert request.source_allowlist == ["reuters.com"]
    assert request.source_blocklist == ["spam.example"]
    assert result["status"] == "success"
