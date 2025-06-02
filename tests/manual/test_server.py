#!/usr/bin/env python3
"""
Quick test script to verify Flask server is working
"""

import requests
import json

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get('http://localhost:5000/api/health')
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
    except Exception as e:
        print(f"Health endpoint error: {e}")
    return False

def test_newsletter_generation():
    """Test newsletter generation with keywords"""
    try:
        # Test with keywords
        data = {
            'type': 'keywords',
            'keywords': ['artificial intelligence', 'machine learning', 'technology']
        }
        
        print("Testing newsletter generation with keywords...")
        response = requests.post('http://localhost:5000/api/generate', 
                                json=data, 
                                headers={'Content-Type': 'application/json'})
        
        print(f"Generate endpoint status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Job ID: {result.get('job_id')}")
            return result.get('job_id')
    except Exception as e:
        print(f"Newsletter generation error: {e}")
    return None

def test_status(job_id):
    """Test status endpoint"""
    if not job_id:
        return
        
    try:
        response = requests.get(f'http://localhost:5000/api/status/{job_id}')
        print(f"Status endpoint status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Job status: {result}")
    except Exception as e:
        print(f"Status check error: {e}")

if __name__ == '__main__':
    print("Testing Flask server...")
    
    # Test health
    if test_health():
        print("✓ Health endpoint working")
        
        # Test newsletter generation
        job_id = test_newsletter_generation()
        if job_id:
            print("✓ Newsletter generation started")
            
            # Wait a moment then check status
            import time
            time.sleep(2)
            test_status(job_id)
        else:
            print("✗ Newsletter generation failed")
    else:
        print("✗ Health endpoint not responding")
