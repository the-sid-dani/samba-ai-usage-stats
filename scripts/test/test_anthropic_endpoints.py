#!/usr/bin/env python3
"""Test different Anthropic API endpoints to find platform-specific data."""

import requests
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def test_all_anthropic_endpoints():
    """Test various Anthropic endpoints to find platform-specific data."""
    print("🔍 Testing All Anthropic Admin Endpoints")
    print("=" * 50)

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Test different endpoints
    endpoints = [
        "/v1/organizations",
        "/v1/organizations/usage",
        "/v1/organizations/api_keys",
        "/v1/organizations/workspaces",
        "/v1/organizations/members",
        "/v1/organizations/billing",
        "/v1/admin/api_keys",
        "/v1/admin/usage",
        "/v1/admin/workspaces"
    ]

    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        url = f"https://api.anthropic.com{endpoint}"

        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Keys: {list(data.keys())}")

                # Look for platform/api_key breakdowns
                if 'data' in data:
                    items = data['data']
                    if isinstance(items, list) and items:
                        sample = items[0]
                        print(f"Sample item keys: {list(sample.keys())}")

                        # Check for platform indicators
                        if 'api_key_id' in sample and sample['api_key_id']:
                            print(f"🎯 API Key ID found: {sample['api_key_id']}")
                        if 'name' in sample:
                            print(f"🎯 Name: {sample['name']}")
                        if 'workspace' in sample:
                            print(f"🎯 Workspace info available")

            elif response.status_code == 404:
                print("❌ Not found")
            elif response.status_code == 403:
                print("❌ Forbidden (insufficient permissions)")
            else:
                print(f"❌ Error: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

    print(f"\n🎯 CONCLUSION:")
    print("Looking for endpoints that return API key lists or workspace breakdowns...")

if __name__ == "__main__":
    test_all_anthropic_endpoints()