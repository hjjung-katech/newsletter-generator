#!/usr/bin/env python3
"""
Simple test script for the newsletter web API
"""

import json
import time

import requests


def test_web_api():
    """Web API 테스트"""
    print("🧪 Testing Newsletter Web API...")

    # Test data
    test_data = {
        "keywords": "AI",
        "template_style": "compact",
        "email_compatible": False,
        "period": 14,
    }

    try:
        # Send generation request
        print(f"📤 Sending generation request: {test_data}")
        response = requests.post(
            "http://localhost:5000/api/generate", json=test_data, timeout=30
        )

        if response.status_code != 200:
            print(
                f"❌ Request failed with status {response.status_code}: {response.text}"
            )
            return False

        result = response.json()
        job_id = result.get("job_id")
        status = result.get("status")

        print(f"📋 Initial response: job_id={job_id}, status={status}")

        if not job_id:
            print(f"❌ No job_id in response")
            return False

        # Poll for completion
        max_attempts = 20
        for attempt in range(max_attempts):
            print(f"🔍 Checking status (attempt {attempt + 1}/{max_attempts})...")

            status_response = requests.get(
                f"http://localhost:5000/api/status/{job_id}", timeout=10
            )

            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.text}")
                return False

            status_data = status_response.json()
            current_status = status_data.get("status")

            print(f"📊 Current status: {current_status}")

            if current_status == "completed":
                result_data = status_data.get("result", {})
                html_content = result_data.get("html_content", "")
                subject = result_data.get("subject", "")
                cli_output = result_data.get("cli_output", "")

                print(f"✅ Newsletter generation completed!")
                print(f"   Subject: {subject}")
                print(f"   Content length: {len(html_content)}")
                print(f"   CLI output length: {len(cli_output)}")

                # Check if content looks reasonable
                if len(html_content) > 100 and "<html" in html_content.lower():
                    print(f"✅ Content appears to be valid HTML")
                    return True
                else:
                    print(f"⚠️  Content may not be valid HTML")
                    print(f"   First 200 chars: {html_content[:200]}")
                    return False

            elif current_status == "failed":
                error = status_data.get("error", "Unknown error")
                print(f"❌ Newsletter generation failed: {error}")
                return False

            elif current_status in ["pending", "processing"]:
                time.sleep(3)  # Wait 3 seconds before next check
                continue
            else:
                print(f"❌ Unknown status: {current_status}")
                return False

        print(f"⏰ Timeout waiting for completion")
        return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Flask server at http://localhost:5000")
        print(f"   Make sure the Flask server is running")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_web_api()
    if success:
        print(f"\n🎉 Web API test PASSED!")
        exit(0)
    else:
        print(f"\n💥 Web API test FAILED!")
        exit(1)
