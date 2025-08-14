import json
from unittest.mock import patch

import pytest


def test_suggest_ok(client, monkeypatch):
    """Test successful keyword suggestion using existing CLI function"""
    # Mock the actual tools function that CLI wrapper calls
    monkeypatch.setattr(
        "newsletter.tools.generate_keywords_with_gemini",
        lambda domain, count=10: ["인공지능", "로봇공학", "전기차"],
    )

    # Make request
    response = client.post("/api/suggest", json={"domain": "기술"})

    # Verify response
    assert response.status_code == 200
    data = response.get_json()
    assert "keywords" in data
    assert len(data["keywords"]) >= 2
    assert "인공지능" in data["keywords"]


def test_suggest_missing_domain(client):
    """Test error when domain is missing"""
    response = client.post("/api/suggest", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No data provided" in data["error"]


def test_suggest_empty_domain(client):
    """Test error when domain is empty"""
    response = client.post("/api/suggest", json={"domain": "  "})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Topic or domain is required" in data["error"]


def test_suggest_api_error(client, monkeypatch):
    """Test handling of API errors from underlying tools function"""

    # Mock the actual tools function to raise an exception
    def mock_error(domain, count=10):
        raise Exception("Gemini API Error")

    monkeypatch.setattr("newsletter.tools.generate_keywords_with_gemini", mock_error)

    response = client.post("/api/suggest", json={"domain": "기술"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "Gemini API Error" in data["error"]


def test_suggest_cli_integration(client, monkeypatch):
    """Test integration with existing CLI suggest functionality"""
    # Mock the tools function with realistic Korean keywords
    expected_keywords = [
        "인공지능 트렌드",
        "머신러닝 기술",
        "딥러닝 발전",
        "자율주행차",
        "스마트팩토리",
        "IoT 기술",
        "블록체인 혁신",
        "클라우드 컴퓨팅",
        "빅데이터 분석",
        "사이버보안",
    ]

    monkeypatch.setattr(
        "newsletter.tools.generate_keywords_with_gemini",
        lambda domain, count=10: expected_keywords[:count],
    )

    # Test with different count parameter
    response = client.post("/api/suggest", json={"domain": "IT 기술"})

    assert response.status_code == 200
    data = response.get_json()
    assert "keywords" in data
    assert len(data["keywords"]) == 10  # Default count
    assert all(keyword in expected_keywords for keyword in data["keywords"])


def test_suggest_empty_result(client, monkeypatch):
    """Test handling when tools function returns empty list"""
    monkeypatch.setattr(
        "newsletter.tools.generate_keywords_with_gemini",
        lambda domain, count=10: [],
    )

    response = client.post("/api/suggest", json={"domain": "unknown"})

    assert response.status_code == 200
    data = response.get_json()
    assert "keywords" in data
    assert data["keywords"] == []
