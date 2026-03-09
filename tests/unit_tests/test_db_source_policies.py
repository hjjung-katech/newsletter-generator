from __future__ import annotations

import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from db_source_policies import (  # noqa: E402
    SOURCE_POLICY_ALLOW,
    SOURCE_POLICY_BLOCK,
    create_source_policy,
    get_active_source_policies,
    list_source_policies,
    update_source_policy,
)
from db_state import ensure_database_schema  # noqa: E402


def test_list_source_policies_returns_saved_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    create_source_policy(
        str(db_path),
        "policy-allow",
        "reuters.com",
        SOURCE_POLICY_ALLOW,
        is_active=True,
    )
    create_source_policy(
        str(db_path),
        "policy-block",
        "spam.example",
        SOURCE_POLICY_BLOCK,
        is_active=False,
    )

    policies = {policy["id"]: policy for policy in list_source_policies(str(db_path))}

    assert policies["policy-allow"]["policy_type"] == SOURCE_POLICY_ALLOW
    assert policies["policy-block"]["is_active"] is False


def test_get_active_source_policies_groups_allow_and_block(tmp_path: Path) -> None:
    db_path = tmp_path / "storage.db"
    ensure_database_schema(str(db_path))

    create_source_policy(
        str(db_path),
        "policy-allow",
        "ft.com",
        SOURCE_POLICY_ALLOW,
        is_active=True,
    )
    create_source_policy(
        str(db_path),
        "policy-block",
        "spam.example",
        SOURCE_POLICY_BLOCK,
        is_active=True,
    )
    update_source_policy(
        str(db_path),
        "policy-block",
        "spam.example",
        SOURCE_POLICY_BLOCK,
        is_active=True,
    )

    active = get_active_source_policies(str(db_path))

    assert active == {"allowlist": ["ft.com"], "blocklist": ["spam.example"]}
