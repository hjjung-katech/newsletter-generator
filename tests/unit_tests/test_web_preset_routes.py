from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from flask import Flask

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import routes_presets  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.mock_api]


def _build_preset_app(database_path: str) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    routes_presets.register_preset_routes(app, database_path)
    return app


def test_preset_routes_create_and_list(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    payload = {
        "name": "Weekly AI Digest",
        "description": "Compact weekly summary",
        "is_default": True,
        "params": {
            "keywords": ["AI", "robotics"],
            "template_style": "compact",
            "email_compatible": True,
            "period": 7,
            "email": "test@example.com",
            "rrule": "FREQ=WEEKLY;BYDAY=MO,WE;BYHOUR=9;BYMINUTE=0",
        },
    }

    with app.test_client() as client:
        create_response = client.post(
            "/api/presets",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert create_response.status_code == 201
        created = create_response.get_json()
        assert created is not None
        assert created["name"] == "Weekly AI Digest"
        assert created["is_default"] is True
        assert created["params"]["keywords"] == ["AI", "robotics"]
        assert created["params"]["rrule"].startswith("FREQ=WEEKLY")

        list_response = client.get("/api/presets")
        assert list_response.status_code == 200
        presets = list_response.get_json()

    assert isinstance(presets, list)
    assert presets[0]["id"] == created["id"]
    assert presets[0]["is_default"] is True


def test_update_route_promotes_single_default_preset(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    first_payload = {
        "name": "Daily AI",
        "is_default": True,
        "params": {
            "keywords": ["AI"],
            "template_style": "compact",
            "email_compatible": False,
            "period": 1,
        },
    }
    second_payload = {
        "name": "Domain Watch",
        "is_default": False,
        "params": {
            "domain": "semiconductor",
            "template_style": "detailed",
            "email_compatible": True,
            "period": 14,
        },
    }

    with app.test_client() as client:
        first_response = client.post(
            "/api/presets",
            data=json.dumps(first_payload),
            content_type="application/json",
        )
        second_response = client.post(
            "/api/presets",
            data=json.dumps(second_payload),
            content_type="application/json",
        )

        first = first_response.get_json()
        second = second_response.get_json()
        assert first_response.status_code == 201
        assert second_response.status_code == 201

        update_response = client.put(
            f"/api/presets/{second['id']}",
            data=json.dumps(
                {
                    "name": "Domain Watch",
                    "description": "Promoted preset",
                    "is_default": True,
                    "params": {
                        "domain": "semiconductor",
                        "template_style": "modern",
                        "email_compatible": True,
                        "period": 30,
                    },
                }
            ),
            content_type="application/json",
        )
        assert update_response.status_code == 200

        list_response = client.get("/api/presets")
        presets = list_response.get_json()

    assert isinstance(presets, list)
    preset_by_id = {preset["id"]: preset for preset in presets}
    assert preset_by_id[first["id"]]["is_default"] is False
    assert preset_by_id[second["id"]]["is_default"] is True
    assert preset_by_id[second["id"]]["params"]["template_style"] == "modern"
    assert preset_by_id[second["id"]]["params"]["period"] == 30


def test_delete_route_removes_preset(tmp_path: Path) -> None:
    app = _build_preset_app(str(tmp_path / "storage.db"))

    with app.test_client() as client:
        create_response = client.post(
            "/api/presets",
            data=json.dumps(
                {
                    "name": "Delete Me",
                    "params": {
                        "keywords": ["ai"],
                        "template_style": "compact",
                        "email_compatible": False,
                        "period": 7,
                    },
                }
            ),
            content_type="application/json",
        )
        preset = create_response.get_json()
        assert create_response.status_code == 201

        delete_response = client.delete(f"/api/presets/{preset['id']}")
        assert delete_response.status_code == 200
        assert delete_response.get_json() == {
            "success": True,
            "deleted_id": preset["id"],
        }

        list_response = client.get("/api/presets")
        assert list_response.status_code == 200
        assert list_response.get_json() == []
