#!/usr/bin/env python3
import requests
import json

data = {
    "limit": 5,
}

try:
    response = requests.post(
        'http://localhost:5000/api/email-verify',
        headers={'Content-Type': 'application/json'},
        data=json.dumps(data)
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
