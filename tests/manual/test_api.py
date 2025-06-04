#!/usr/bin/env python3
"""
Simple test script to verify the newsletter generation API
"""

import json
import time

import pytest
import requests

BASE_URL = "http://127.0.0.1:5000"


@pytest.mark.manual
def test_generate_newsletter():
    """Test newsletter generation with keywords"""
    print("Testing newsletter generation...")

    # Test data
    data = {
        "keywords": "AI, machine learning, deep learning",
        "email": "test@example.com",
    }

    # Make API request
    response = requests.post(f"{BASE_URL}/api/generate", json=data)

    if response.status_code == 200:
        result = response.json()
        job_id = result.get("job_id")
        print(f"✓ Newsletter generation started. Job ID: {job_id}")

        # Poll for results
        if job_id:
            return poll_job_status(job_id)
    else:
        print(f"✗ Failed to start newsletter generation: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def poll_job_status(job_id):
    """Poll job status until completion"""
    print(f"Polling job status for {job_id}...")

    for i in range(30):  # Poll for up to 30 seconds
        response = requests.get(f"{BASE_URL}/api/status/{job_id}")

        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            print(f"Status: {status}")

            if status == "completed":
                print("✓ Newsletter generation completed!")
                print(f"Articles count: {result.get('articles_count', 'unknown')}")
                return True
            elif status == "failed":
                print(
                    f"✗ Newsletter generation failed: {result.get('error', 'Unknown error')}"
                )
                return False

        time.sleep(1)

    print("✗ Timeout waiting for job completion")
    return False


@pytest.mark.manual
def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")

    response = requests.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Health check passed: {result}")
        return True
    else:
        print(f"✗ Health check failed: {response.status_code}")
        return False


def main():
    print("Newsletter Generator API Test")
    print("=" * 40)

    # Test health check first
    if not test_health_check():
        print("Health check failed, stopping tests")
        return

    # Test newsletter generation
    test_generate_newsletter()


if __name__ == "__main__":
    main()
