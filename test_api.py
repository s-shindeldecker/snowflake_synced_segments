#!/usr/bin/env python3
"""
Test script for the Snowflake → LaunchDarkly Sync API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_root():
    """Test the root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_sync():
    """Test the sync endpoint"""
    print("Testing sync endpoint...")
    
    # Test data matching the requirements
    test_data = {
        "audience": "snowflake_test_segment",
        "included": ["user_123", "user_456"],
        "excluded": [],
        "version": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/snowflake-sync",
        headers={"Content-Type": "application/json"},
        json=test_data
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_validation():
    """Test input validation"""
    print("Testing input validation...")
    
    # Test with invalid data
    invalid_data = {
        "audience": "",
        "included": "not_a_list",
        "excluded": [],
        "version": 0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/snowflake-sync",
        headers={"Content-Type": "application/json"},
        json=invalid_data
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("Snowflake → LaunchDarkly Sync API Test Suite")
    print("=" * 50)
    
    try:
        test_health()
        test_root()
        test_sync()
        test_validation()
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"Error: {e}")
