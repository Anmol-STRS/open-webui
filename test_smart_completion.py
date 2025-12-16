#!/usr/bin/env python3
"""
Test script for the smart chat completion endpoint.

This script tests the multi-provider routing system with:
- Simple chat completion
- Code-related queries (should route to coding model)
- Streaming responses
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8080"
API_ENDPOINT = f"{BASE_URL}/openai/chat/completions/smart"

# You'll need to set this to a valid auth token
# Get it from your browser's localStorage after logging in
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQ5MDYzZGNkLWE3YTEtNDhkZS05YjA2LWZmYWMwZWU3NTRlMSIsImV4cCI6MTc2ODMwMDU4NSwianRpIjoiODg2OWI3YTItYzUzMS00MWY1LTkwMTItNzMxMjdjM2Q5NGM0In0.S26hDhmDzRbUOXvIsHNoxMaqZyJ_UA20JIXnVcHDIgY"  # Set this to your actual token


def test_simple_completion():
    """Test a simple chat completion"""
    print("\n=== Test 1: Simple Completion ===")

    payload = {
        "messages": [
            {"role": "user", "content": "Hello! What's the weather like today?"}
        ],
        "stream": False,
    }

    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Model used: {data.get('model')}")
            print(f"Response: {data['choices'][0]['message']['content']}")
            print(f"Usage: {data.get('usage', {})}")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")


def test_coding_completion():
    """Test a coding-related query (should route to coding model)"""
    print("\n=== Test 2: Coding Completion ===")

    payload = {
        "messages": [
            {
                "role": "user",
                "content": """Write a Python function that calculates fibonacci numbers:

```python
def fibonacci(n):
    # Your code here
```"""
            }
        ],
        "stream": False,
    }

    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Model used: {data.get('model')} (should be coding model)")
            print(f"Response preview: {data['choices'][0]['message']['content'][:200]}...")
            print(f"Usage: {data.get('usage', {})}")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")


def test_streaming_completion():
    """Test streaming response"""
    print("\n=== Test 3: Streaming Completion ===")

    payload = {
        "messages": [
            {"role": "user", "content": "Count from 1 to 5, one number per line."}
        ],
        "stream": True,
    }

    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, stream=True)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("Streaming response:")
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str != '[DONE]':
                            try:
                                chunk = json.loads(data_str)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        print(content, end='', flush=True)
                            except json.JSONDecodeError:
                                pass
            print("\n")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")


def test_health():
    """Test the observability health endpoint"""
    print("\n=== Test 4: Observability Health ===")

    health_url = f"{BASE_URL}/api/v1/observability/health"

    try:
        response = requests.get(health_url)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Health: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")


def main():
    print("=" * 60)
    print("Smart Chat Completion Test Suite")
    print("=" * 60)

    if not AUTH_TOKEN:
        print("\n⚠️  WARNING: AUTH_TOKEN not set!")
        print("The tests will likely fail with 401 Unauthorized.")
        print("To set your token:")
        print("1. Log in to Open WebUI in your browser")
        print("2. Open browser DevTools (F12)")
        print("3. Go to Console tab")
        print("4. Run: localStorage.getItem('token')")
        print("5. Copy the token and set AUTH_TOKEN in this script")
        print("\nContinuing anyway...\n")
        time.sleep(2)

    # Run all tests
    test_health()
    test_simple_completion()
    test_coding_completion()
    test_streaming_completion()

    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
    print("\n📊 Check the observability dashboard:")
    print(f"   {BASE_URL}/admin/observability")
    print("\nYou should see:")
    print("- Request logs for each test")
    print("- Routing decisions (default vs coding)")
    print("- Token usage and latency metrics")


if __name__ == "__main__":
    main()
