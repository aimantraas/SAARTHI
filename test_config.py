#!/usr/bin/env python3
"""Test script to verify the config is being loaded correctly."""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path.cwd()))

from leadgen_backend import LeadGenConfig

# Check if the .env file exists and content
env_path = Path('.env')
print(f".env file exists: {env_path.exists()}")
if env_path.exists():
    print("Content of .env:")
    with open(env_path, 'r', encoding='utf-8') as f:
        print(f.read())
    print("-" * 50)

# Create a config instance
config = LeadGenConfig()

print("Config values:")
print(f"  SERP_API_KEY: '{config.serp_api_key}'")
print(f"  APIFY_API_TOKEN: '{config.apify_api_token}'")
print(f"  EMAIL_VERIFY_API_KEY: '{config.email_verify_api_key}'")
print(f"  GOOGLE_SHEET_ID: '{config.google_sheet_id}'")
print(f"  GOOGLE_CREDENTIALS_PATH: '{config.google_credentials_path}'")

print("\nEnvironment variables:")
for key in ['SERP_API_KEY', 'APIFY_API_TOKEN', 'EMAIL_VERIFY_API_KEY', 'GOOGLE_SHEET_ID']:
    value = os.environ.get(key)
    print(f"  {key}: '{value}'")

# Check if config is complete
is_complete = (
    config.serp_api_key and
    config.apify_api_token and
    config.email_verify_api_key and
    config.google_sheet_id
)

print(f"\nConfig is complete: {is_complete}")
