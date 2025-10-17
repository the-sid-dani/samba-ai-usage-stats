#!/usr/bin/env python3
"""
Map Anthropic API keys and workspaces to platforms.
Creates mapping: API Key ID → Platform (Claude.AI, Claude Code, Claude API)
"""

import requests
import json
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_api_key_mappings():
    """Get all API keys and map them to platforms."""
    print("🔑 MAPPING ANTHROPIC API KEYS TO PLATFORMS")
    print("=" * 50)

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Get all API keys
    keys_url = "https://api.anthropic.com/v1/organizations/api_keys"
    response = requests.get(keys_url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"❌ API Keys error: {response.status_code}")
        return {}

    data = response.json()
    api_keys = data.get('data', [])

    print(f"Found {len(api_keys)} API keys:")

    key_mappings = {}
    for i, key_info in enumerate(api_keys, 1):
        key_id = key_info.get('id')
        key_name = key_info.get('name', 'unknown')
        workspace_id = key_info.get('workspace_id')
        status = key_info.get('status', 'unknown')

        print(f"\n{i}. API Key: {key_id}")
        print(f"   Name: {key_name}")
        print(f"   Workspace: {workspace_id}")
        print(f"   Status: {status}")

        # Determine platform based on name patterns
        platform = "claude_api"  # default
        if "code" in key_name.lower():
            platform = "claude_code"
        elif "web" in key_name.lower() or "claude.ai" in key_name.lower():
            platform = "claude_web"
        elif "api" in key_name.lower():
            platform = "claude_api"

        key_mappings[key_id] = {
            "platform": platform,
            "name": key_name,
            "workspace_id": workspace_id
        }

        print(f"   🎯 Mapped to: {platform}")

    return key_mappings

def get_workspace_mappings():
    """Get all workspaces to understand platform structure."""
    print(f"\n🏢 MAPPING ANTHROPIC WORKSPACES")
    print("=" * 50)

    api_key = get_secret("anthropic-api-key")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Get all workspaces
    workspaces_url = "https://api.anthropic.com/v1/organizations/workspaces"
    response = requests.get(workspaces_url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"❌ Workspaces error: {response.status_code}")
        return {}

    data = response.json()
    workspaces = data.get('data', [])

    print(f"Found {len(workspaces)} workspaces:")

    workspace_mappings = {}
    for i, workspace in enumerate(workspaces, 1):
        workspace_id = workspace.get('id')
        workspace_name = workspace.get('name', 'unknown')
        created_at = workspace.get('created_at', '')

        print(f"\n{i}. Workspace: {workspace_id}")
        print(f"   Name: {workspace_name}")
        print(f"   Created: {created_at[:10]}")

        # Map workspace name to platform
        platform = "claude_web"  # default
        if "code" in workspace_name.lower():
            platform = "claude_code"
        elif "api" in workspace_name.lower():
            platform = "claude_api"
        elif "web" in workspace_name.lower() or workspace_name.lower() == "claude code":
            platform = "claude_web"

        workspace_mappings[workspace_id] = {
            "platform": platform,
            "name": workspace_name
        }

        print(f"   🎯 Mapped to: {platform}")

    return workspace_mappings

def create_platform_mapping_sheet():
    """Create a comprehensive platform mapping."""
    print(f"\n📋 CREATING COMPREHENSIVE PLATFORM MAPPING")
    print("=" * 50)

    api_key_mappings = get_api_key_mappings()
    workspace_mappings = get_workspace_mappings()

    # Create comprehensive mapping
    platform_mapping = {
        "api_keys": api_key_mappings,
        "workspaces": workspace_mappings,
        "platform_rules": {
            "claude_code": ["code", "vscode", "cursor"],
            "claude_web": ["web", "claude.ai", "browser"],
            "claude_api": ["api", "direct", "sdk"]
        }
    }

    # Save mapping to file
    with open('anthropic_platform_mapping.json', 'w') as f:
        json.dump(platform_mapping, f, indent=2)

    print(f"✅ Platform mapping saved to: anthropic_platform_mapping.json")

    # Summary
    print(f"\n🎯 PLATFORM MAPPING SUMMARY:")
    print(f"API keys mapped: {len(api_key_mappings)}")
    print(f"Workspaces mapped: {len(workspace_mappings)}")

    # Show platform distribution strategy
    print(f"\n📊 PLATFORM IDENTIFICATION STRATEGY:")
    if api_key_mappings:
        print("✅ Use api_key_id to identify platform")
    if workspace_mappings:
        print("✅ Use workspace_id to identify platform")
    if not api_key_mappings and not workspace_mappings:
        print("⚠️ May need to use organization-level aggregation")

    return platform_mapping

if __name__ == "__main__":
    try:
        mapping = create_platform_mapping_sheet()

        print(f"\n🎉 PLATFORM MAPPING COMPLETE!")

        # Next steps
        print(f"\n📋 NEXT STEPS:")
        print("1. Review anthropic_platform_mapping.json")
        print("2. Use mapping to distinguish platforms in data ingestion")
        print("3. Update BigQuery schema with platform field")
        print("4. Test with platform-specific analytics")

    except Exception as e:
        print(f"❌ Mapping failed: {e}")
        import traceback
        traceback.print_exc()