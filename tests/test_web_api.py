"""
Integration tests for web API endpoints
Tests the Flask app with email functionality
"""

import json
import os
import sqlite3
import sys
import uuid

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from web.app import DATABASE_PATH, app  # noqa: E402

pytestmark = [pytest.mark.api, pytest.mark.email]


def _delete_schedule(schedule_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


def _delete_source_policy(policy_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM source_policies WHERE id = ?", (policy_id,))
    conn.commit()
    conn.close()


def _insert_schedule_row(
    *,
    schedule_id: str,
    params: dict,
    rrule: str,
    next_run: str,
    created_at: str,
) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO schedules (id, params, rrule, next_run, created_at, enabled)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (schedule_id, json.dumps(params), rrule, next_run, created_at),
    )
    conn.commit()
    conn.close()


class TestWebAPI:
    """Test web API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_generate_newsletter_without_email(self, client):
        """Test newsletter generation without email"""
        unique_topic = f"AI-{uuid.uuid4()}"
        data = {
            "keywords": f"{unique_topic}, machine learning",
            "template_style": "compact",
            "period": 14,
        }

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 202
        result = json.loads(response.data)
        assert "job_id" in result
        assert result["status"] in ["queued", "processing"]

    def test_generate_newsletter_with_email(self, client):
        """Test newsletter generation with email"""
        unique_topic = f"AI-{uuid.uuid4()}"
        data = {
            "keywords": f"{unique_topic}, machine learning",
            "template_style": "compact",
            "period": 14,
            "email": "test@example.com",
        }

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 202
        result = json.loads(response.data)
        assert "job_id" in result
        assert result["status"] in ["queued", "processing"]

    def test_generate_newsletter_idempotency_reuses_job(self, client):
        """Same Idempotency-Key should return same job_id with deduplicated flag."""
        data = {
            "keywords": "AI, machine learning",
            "template_style": "compact",
            "period": 14,
        }
        unique_key = f"web-api-idempotency-{uuid.uuid4()}"
        headers = {"Idempotency-Key": unique_key}

        first = client.post(
            "/api/generate",
            data=json.dumps(data),
            content_type="application/json",
            headers=headers,
        )
        second = client.post(
            "/api/generate",
            data=json.dumps(data),
            content_type="application/json",
            headers=headers,
        )

        assert first.status_code == 202
        assert second.status_code == 202

        first_payload = json.loads(first.data)
        second_payload = json.loads(second.data)
        assert first_payload["job_id"] == second_payload["job_id"]
        assert first_payload["deduplicated"] is False
        assert second_payload["deduplicated"] is True
        assert second_payload["idempotency_key"] == unique_key

    def test_generate_newsletter_invalid_email(self, client):
        """Test newsletter generation with invalid email"""
        data = {"keywords": "AI, machine learning", "email": "invalid-email"}

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result
        assert "Invalid email format" in result["error"]

    def test_generate_newsletter_no_keywords_or_domain(self, client):
        """Test newsletter generation without keywords or domain"""
        data = {"template_style": "compact", "period": 14}

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result

    def test_generate_newsletter_invalid_period(self, client):
        """Test newsletter generation with invalid period"""
        data = {"keywords": "AI", "period": 999}  # Invalid period

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "error" in result

    def test_job_status_endpoint(self, client):
        """Test job status endpoint"""
        # First create a job
        data = {"keywords": "test", "template_style": "compact"}

        response = client.post(
            "/api/generate", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 202
        result = json.loads(response.data)
        job_id = result["job_id"]

        # Check job status
        status_response = client.get(f"/api/status/{job_id}")
        assert status_response.status_code == 200

        status_result = json.loads(status_response.data)
        assert "job_id" in status_result
        assert "status" in status_result
        assert "sent" in status_result  # Check for sent field
        assert status_result["job_id"] == job_id

    def test_job_status_not_found(self, client):
        """Test job status for non-existent job"""
        response = client.get("/api/status/non-existent-job")
        assert response.status_code == 404

        result = json.loads(response.data)
        assert "error" in result
        assert "Job not found" in result["error"]

    def test_email_config_endpoint(self, client):
        """Test email configuration endpoint"""
        response = client.get("/api/email-config")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert "postmark_token_configured" in result
        assert "from_email_configured" in result
        assert "ready" in result

    @pytest.mark.skip(reason="Requires actual email service configuration")
    def test_send_test_email_endpoint(self, client):
        """Test send test email endpoint - skipped to avoid API calls"""
        # This test is skipped because mocking in Flask context is complex
        # and the functionality is tested in integration tests when needed.
        pass

    def test_send_test_email_invalid_email(self, client):
        """Test send test email with invalid email"""
        data = {"email": "invalid-email"}
        response = client.post(
            "/api/test-email", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert result["success"] is False
        assert "Invalid email format" in result["error"]

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert result["status"] == "healthy"
        assert "timestamp" in result

    def test_history_endpoint(self, client):
        """Test history endpoint"""
        response = client.get("/api/history")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert isinstance(result, list)

    def test_schedules_endpoint(self, client):
        """Test schedules endpoint"""
        response = client.get("/api/schedules")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert isinstance(result, list)

    def test_source_policy_crud_endpoint(self, client):
        created_policy_id = None
        response = client.post(
            "/api/source-policies",
            data=json.dumps(
                {"pattern": "https://www.reuters.com", "policy_type": "allow"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 201
        created = json.loads(response.data)
        created_policy_id = created["id"]
        assert created["pattern"] == "reuters.com"
        assert created["policy_type"] == "allow"
        assert created["is_active"] is True

        try:
            list_response = client.get("/api/source-policies")
            assert list_response.status_code == 200
            listed = json.loads(list_response.data)
            assert any(item["id"] == created_policy_id for item in listed)

            update_response = client.put(
                f"/api/source-policies/{created_policy_id}",
                data=json.dumps(
                    {
                        "pattern": "spam.example",
                        "policy_type": "block",
                        "is_active": False,
                    }
                ),
                content_type="application/json",
            )
            assert update_response.status_code == 200
            updated = json.loads(update_response.data)
            assert updated["pattern"] == "spam.example"
            assert updated["policy_type"] == "block"
            assert updated["is_active"] is False

            delete_response = client.delete(f"/api/source-policies/{created_policy_id}")
            assert delete_response.status_code == 200
            assert json.loads(delete_response.data)["success"] is True
        finally:
            if created_policy_id:
                _delete_source_policy(created_policy_id)

    def test_schedule_creation_returns_utc_next_run(self, client):
        schedule_id = None
        response = client.post(
            "/api/schedule",
            data=json.dumps(
                {
                    "keywords": ["AI", "ML"],
                    "email": "schedule@example.com",
                    "rrule": "FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        schedule_id = result["schedule_id"]

        try:
            assert result["next_run"].endswith("Z")

            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT next_run FROM schedules WHERE id = ?", (schedule_id,)
            )
            stored_next_run = cursor.fetchone()[0]
            conn.close()

            assert stored_next_run.endswith("Z")
        finally:
            if schedule_id:
                _delete_schedule(schedule_id)

    def test_schedules_endpoint_normalizes_timestamp_fields_to_utc(self, client):
        schedule_id = f"schedule-utc-{uuid.uuid4()}"
        _insert_schedule_row(
            schedule_id=schedule_id,
            params={"keywords": ["AI"], "send_email": False},
            rrule="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
            next_run="2026-03-08 09:30:00",
            created_at="2026-03-08 08:15:00",
        )

        try:
            response = client.get("/api/schedules")
            assert response.status_code == 200
            schedules = json.loads(response.data)

            matching = next(item for item in schedules if item["id"] == schedule_id)
            assert matching["next_run"] == "2026-03-08T09:30:00Z"
            assert matching["created_at"] == "2026-03-08T08:15:00Z"
        finally:
            _delete_schedule(schedule_id)


if __name__ == "__main__":
    pytest.main([__file__])


def test_protected_schedule_routes_require_admin_token_in_production_like_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "ops-secret-token")
    original_testing = app.config.get("TESTING", False)
    app.config["TESTING"] = False

    try:
        with app.test_client() as client:
            unauthorized = client.get("/api/schedules")
            authorized = client.get(
                "/api/schedules", headers={"X-Admin-Token": "ops-secret-token"}
            )

        assert unauthorized.status_code == 401
        assert unauthorized.get_json() == {"error": "Admin API token required"}
        assert authorized.status_code == 200
        assert isinstance(authorized.get_json(), list)
    finally:
        app.config["TESTING"] = original_testing
