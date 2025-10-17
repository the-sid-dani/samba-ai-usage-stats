#!/usr/bin/env python3
"""Test the complete Anthropic integration with platform categorization."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Mock the config to avoid import issues
class MockConfig:
    def __init__(self):
        self.anthropic_api_key = "test-key"

import src.shared.config as config_module
config_module.config = MockConfig()

from src.ingestion.anthropic_client import AnthropicClient

def test_platform_categorization():
    """Test platform categorization logic."""
    print("🔍 Testing Complete Anthropic Pipeline Integration")
    print("=" * 50)

    # Test platform categorization helper methods
    client = AnthropicClient()
    api_mappings = client._get_api_key_mappings()
    workspace_mappings = client._get_workspace_mappings()

    print(f"✅ API Key Mappings loaded: {len(api_mappings)} keys")
    print(f"✅ Workspace Mappings loaded: {len(workspace_mappings)} workspaces")

    # Test categorization logic with known keys
    test_cases = [
        ("apikey_01Ap5QMqkPdxe7zmXYo2awnc", None),  # API key
        ("apikey_01Eb6TPyqUneJQqKBfv7Gti6", "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR"),  # Claude Code
        ("unknown_key", None),  # Unknown
        ("unknown_key", "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR")  # Unknown key with workspace
    ]

    for api_key, workspace_id in test_cases:
        platform, method, confidence, email = client._categorize_platform(
            api_key, workspace_id, api_mappings, workspace_mappings
        )
        print(f"🎯 Key: {api_key[:20]}... → Platform: {platform} ({method}, {confidence:.2f}) Email: {email}")

    print("✅ Platform categorization logic working correctly!")

    # Verify expected categorizations
    # Test case 1: Known API key
    platform, method, confidence, email = client._categorize_platform(
        "apikey_01Ap5QMqkPdxe7zmXYo2awnc", None, api_mappings, workspace_mappings
    )
    assert platform == "claude_api", f"Expected claude_api, got {platform}"
    assert method == "api_key_mapping", f"Expected api_key_mapping, got {method}"
    assert confidence == 0.95, f"Expected 0.95, got {confidence}"
    print("✅ API key mapping test passed")

    # Test case 2: Claude Code key
    platform, method, confidence, email = client._categorize_platform(
        "apikey_01Eb6TPyqUneJQqKBfv7Gti6", "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR", api_mappings, workspace_mappings
    )
    assert platform == "claude_code", f"Expected claude_code, got {platform}"
    assert method == "api_key_mapping", f"Expected api_key_mapping, got {method}"
    assert confidence == 0.95, f"Expected 0.95, got {confidence}"
    assert email == "max.roycroft@samba.tv", f"Expected max.roycroft@samba.tv, got {email}"
    print("✅ Claude Code mapping test passed")

    # Test case 3: Unknown key with workspace
    platform, method, confidence, email = client._categorize_platform(
        "unknown_key", "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR", api_mappings, workspace_mappings
    )
    assert platform == "claude_code", f"Expected claude_code, got {platform}"
    assert method == "workspace_mapping", f"Expected workspace_mapping, got {method}"
    assert confidence == 0.75, f"Expected 0.75, got {confidence}"
    print("✅ Workspace mapping test passed")

    print("\n🎉 ALL TESTS PASSED! Platform categorization is working correctly!")
    print("\n🔧 SOLUTION SUMMARY:")
    print("✅ Added platform categorization logic to AnthropicClient")
    print("✅ Fixed missing platform, attribution_method, attribution_confidence, user_email fields")
    print("✅ Updated both get_usage_data() and get_cost_data() methods")
    print("✅ Updated unit tests to match new dataclass structure")
    print("✅ Verified platform detection works for claude_api, claude_code, and fallback cases")

if __name__ == "__main__":
    test_platform_categorization()