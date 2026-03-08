from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_archive  # noqa: E402
from db_state import ensure_database_schema  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_archive_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_archive.register_archive_routes(app, database_path)
    return app


def _insert_history_row(
    database_path: str,
    *,
    job_id: str,
    params: dict,
    result: dict,
    created_at: str,
    status: str = "completed",
) -> None:
    ensure_database_schema(database_path)
    conn = sqlite3.connect(database_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO history (id, params, result, created_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, json.dumps(params), json.dumps(result), created_at, status),
        )
        conn.commit()
    finally:
        conn.close()


def test_archive_search_route_returns_recent_results(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_archive_app(database_path)
    _insert_history_row(
        database_path,
        job_id="archive-job-1",
        params={"keywords": ["battery", "materials"], "template_style": "compact"},
        result={
            "title": "Battery Materials Weekly",
            "html_content": "<html><body><h1>Battery Materials Weekly</h1><p>Solid-state battery supply chain update.</p></body></html>",
        },
        created_at="2026-03-08T08:00:00Z",
    )

    with app.test_client() as client:
        response = client.get("/api/archive/search")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["count"] == 1
    assert payload["results"][0]["job_id"] == "archive-job-1"
    assert payload["results"][0]["keywords"] == ["battery", "materials"]


def test_archive_search_route_filters_by_query_and_clamps_limit(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_archive_app(database_path)
    _insert_history_row(
        database_path,
        job_id="archive-job-battery",
        params={"keywords": "battery, materials", "template_style": "compact"},
        result={
            "title": "Battery Materials Weekly",
            "html_content": "<html><body><p>Battery recycling and cathode materials.</p></body></html>",
        },
        created_at="2026-03-08T08:00:00Z",
    )
    _insert_history_row(
        database_path,
        job_id="archive-job-ai",
        params={"keywords": ["ai", "chip"], "template_style": "detailed"},
        result={
            "title": "AI Chip Radar",
            "html_content": "<html><body><p>Inference accelerator roadmap.</p></body></html>",
        },
        created_at="2026-03-08T09:00:00Z",
    )

    with app.test_client() as client:
        response = client.get("/api/archive/search?q=battery&limit=999")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["query"] == "battery"
    assert payload["count"] == 1
    assert payload["results"][0]["job_id"] == "archive-job-battery"


def test_archive_detail_route_returns_archived_payload(tmp_path: Path) -> None:
    database_path = str(tmp_path / "storage.db")
    app = _build_archive_app(database_path)
    _insert_history_row(
        database_path,
        job_id="archive-job-detail",
        params={"domain": "semiconductor", "period": 7},
        result={
            "title": "Semiconductor Weekly",
            "html_content": "<html><body><p>Packaging capacity and foundry updates.</p></body></html>",
        },
        created_at="2026-03-08T10:00:00Z",
    )

    with app.test_client() as client:
        response = client.get("/api/archive/archive-job-detail")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["job_id"] == "archive-job-detail"
    assert payload["params"]["domain"] == "semiconductor"
    assert payload["result"]["title"] == "Semiconductor Weekly"
