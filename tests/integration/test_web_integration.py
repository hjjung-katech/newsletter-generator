#!/usr/bin/env python3
"""
Web Integration Test
Tests the web API with actual CLI integration
"""

import json
import sys
import time

import requests


def test_web_api():
    """Test the newsletter generation web API"""
    print("🔧 Testing Newsletter Generator Web API Integration")

    # API endpoint
    base_url = "http://localhost:5000"

    # Test data
    test_data = {
        "keywords": "AI,자율주행",
        "template_style": "compact",
        "email_compatible": False,
        "period": 7,
    }

    print(f"📋 Test parameters:")
    print(f"   Keywords: {test_data['keywords']}")
    print(f"   Template style: {test_data['template_style']}")
    print(f"   Email compatible: {test_data['email_compatible']}")
    print(f"   Period: {test_data['period']} days")

    try:
        # Check if server is running
        print(f"\n🔍 Checking server availability at {base_url}")
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")

        # Test newsletter generation
        print(f"\n🚀 Starting newsletter generation...")
        start_time = time.time()

        response = requests.post(
            f"{base_url}/api/generate", json=test_data, timeout=300  # 5 minute timeout
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"⏱️  Request completed in {duration:.2f} seconds")
        print(f"📊 Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Newsletter generation successful!")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Subject: {result.get('subject', 'N/A')}")
            print(f"   Content length: {len(result.get('html_content', ''))}")
            print(f"   Articles count: {result.get('articles_count', 'unknown')}")

            # Check if it's using real CLI or mock
            cli_output = result.get("cli_output", "")
            if cli_output:
                print(f"   CLI output (first 200 chars): {cli_output[:200]}...")
                print(f"🎯 Using RealNewsletterCLI successfully!")
            else:
                print(f"⚠️  No CLI output detected - likely using Mock")

            # Save result for inspection
            with open("test_newsletter_result.html", "w", encoding="utf-8") as f:
                f.write(result.get("html_content", ""))
            print(f"💾 Newsletter saved to test_newsletter_result.html")

            return True

        else:
            print(f"❌ Newsletter generation failed!")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {base_url}")
        print(f"   Make sure Flask server is running: python web/app.py")
        return False

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 300 seconds")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_domain_generation():
    """Test domain-based newsletter generation"""
    print(f"\n🎯 Testing domain-based generation...")

    base_url = "http://localhost:5000"
    test_data = {
        "domain": "반도체",
        "template_style": "detailed",
        "email_compatible": True,
        "period": 14,
    }

    print(f"📋 Domain test parameters:")
    print(f"   Domain: {test_data['domain']}")
    print(f"   Template style: {test_data['template_style']}")
    print(f"   Email compatible: {test_data['email_compatible']}")

    try:
        response = requests.post(
            f"{base_url}/api/generate", json=test_data, timeout=300
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Domain-based generation successful!")
            print(f"   Subject: {result.get('subject', 'N/A')}")
            print(f"   Content length: {len(result.get('html_content', ''))}")

            # Save result
            with open("test_domain_newsletter_result.html", "w", encoding="utf-8") as f:
                f.write(result.get("html_content", ""))
            print(f"💾 Domain newsletter saved to test_domain_newsletter_result.html")

            return True
        else:
            print(f"❌ Domain generation failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Domain test error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Newsletter Generator Web Integration Test")
    print("=" * 60)

    # Test basic functionality
    success1 = test_web_api()

    # Test domain functionality
    success2 = test_domain_generation()

    print(f"\n" + "=" * 60)
    print(f"📊 Test Results:")
    print(f"   Keywords test: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Domain test: {'✅ PASS' if success2 else '❌ FAIL'}")

    if success1 and success2:
        print(f"🎉 All tests passed! Real CLI integration is working.")
        sys.exit(0)
    else:
        print(f"⚠️  Some tests failed. Check the output above.")
        sys.exit(1)
