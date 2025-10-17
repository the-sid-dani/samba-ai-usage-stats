#!/usr/bin/env python3
"""Simple standalone API test using Google Secret Manager."""

import requests
import json
from google.cloud import secretmanager
from datetime import datetime, timedelta

def get_secret(project_id: str, secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def test_cursor_api():
    """Test Cursor API connectivity."""
    print("🧪 Testing Cursor API")
    print("-" * 40)

    try:
        # Get API key from Secret Manager
        api_key = get_secret("ai-workflows-459123", "cursor-api-key")
        print(f"✅ Retrieved Cursor API key: {api_key[:12]}...")

        # Test API call (POST method for Cursor)
        url = "https://api.cursor.com/teams/daily-usage-data"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Get last 3 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        data = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cursor API response: {response.status_code}")
            print(f"✅ Data type: {type(data)}")

            if isinstance(data, list):
                print(f"✅ Records retrieved: {len(data)}")
                if data:
                    sample = data[0]
                    print(f"✅ Sample user: {sample.get('email', 'unknown')}")
                    print(f"✅ Sample metrics: {sample.get('total_lines_added', 0)} lines")
            else:
                print(f"✅ Response structure: {list(data.keys()) if isinstance(data, dict) else 'unknown'}")

            return True
        else:
            print(f"❌ Cursor API error: {response.status_code}")
            print(f"❌ Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Cursor API test failed: {e}")
        return False

def test_anthropic_api():
    """Test Anthropic API connectivity."""
    print("\n🧪 Testing Anthropic API")
    print("-" * 40)

    try:
        # Get API key from Secret Manager
        api_key = get_secret("ai-workflows-459123", "anthropic-api-key")
        print(f"✅ Retrieved Anthropic API key: {api_key[:15]}...")

        # Test usage endpoint
        url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Add date parameters
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        params = {
            "starting_at": start_date.strftime("%Y-%m-%d"),
            "ending_at": end_date.strftime("%Y-%m-%d")
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Anthropic API response: {response.status_code}")
            print(f"✅ Data structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            if isinstance(data, dict) and 'data' in data:
                records = data['data']
                print(f"✅ Usage records: {len(records)}")
                if records:
                    sample = records[0]
                    print(f"✅ Sample API key: {sample.get('api_key_id', 'unknown')}")
                    print(f"✅ Sample tokens: input={sample.get('uncached_input_tokens', 0)}, output={sample.get('output_tokens', 0)}")

            return True
        else:
            print(f"❌ Anthropic API error: {response.status_code}")
            print(f"❌ Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Anthropic API test failed: {e}")
        return False

def test_bigquery_insertion():
    """Test BigQuery data insertion capability."""
    print("\n🧪 Testing BigQuery Data Insertion")
    print("-" * 40)

    try:
        from google.cloud import bigquery
        client = bigquery.Client(project="ai-workflows-459123")

        # Test insertion into raw_cursor_usage
        table_id = "ai-workflows-459123.ai_usage_analytics.raw_cursor_usage"

        test_data = [{
            "email": "test@samba.tv",
            "usage_date": "2025-09-27",
            "total_lines_added": 100,
            "accepted_lines_added": 85,
            "total_accepts": 10,
            "subscription_included_reqs": 5,
            "usage_based_reqs": 0,
            "ingest_date": "2025-09-27",
            "request_id": "test-validation-001",
            "raw_response": '{"test": "validation"}'
        }]

        table = client.get_table(table_id)
        errors = client.insert_rows_json(table, test_data)

        if not errors:
            print("✅ BigQuery insertion successful")

            # Query the test data (with partition filter)
            query = f"SELECT COUNT(*) as count FROM `{table_id}` WHERE request_id = 'test-validation-001' AND ingest_date = '2025-09-27'"
            results = list(client.query(query).result())
            if results and results[0].count > 0:
                print("✅ Test data successfully inserted and queryable")

                # Clean up test data
                cleanup_query = f"DELETE FROM `{table_id}` WHERE request_id = 'test-validation-001' AND ingest_date = '2025-09-27'"
                client.query(cleanup_query).result()
                print("✅ Test data cleaned up")

            return True
        else:
            print(f"❌ BigQuery insertion errors: {errors}")
            return False

    except Exception as e:
        print(f"❌ BigQuery test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🎯 AI Usage Analytics - Production Validation")
    print("=" * 60)

    results = []

    # Test BigQuery
    print("1. Testing BigQuery Data Warehouse...")
    bq_result = test_bigquery_insertion()
    results.append(("BigQuery", bq_result))

    # Test APIs
    print("\n2. Testing API Connectivity...")
    cursor_result = test_cursor_api()
    results.append(("Cursor API", cursor_result))

    anthropic_result = test_anthropic_api()
    results.append(("Anthropic API", anthropic_result))

    # Summary
    print("\n" + "=" * 60)
    print("🎯 VALIDATION RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "🎉" if all_passed else "⚠️")
    if all_passed:
        print("ALL VALIDATION TESTS PASSED!")
        print("✅ BigQuery data warehouse is operational")
        print("✅ API connectivity is working")
        print("✅ Ready for full production pipeline")
    else:
        print("Some validation tests failed")
        print("❌ Check API keys and permissions")

    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        exit(1)