"""
Save complete API responses to files for detailed review.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_ADMIN_KEY")
CURSOR_API_KEY = os.getenv("CURSOR_ADMIN_API_KEY")
BASE_URL_ANTHROPIC = "https://api.anthropic.com/v1/organizations"
BASE_URL_CURSOR = "https://api.cursor.com"

OUTPUT_DIR = "scripts/api_investigation/responses"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_claude_cost_report():
    """Save complete Claude Cost Report response."""
    print("\n" + "="*80)
    print("FETCHING: Claude Cost Report")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    url = f"{BASE_URL_ANTHROPIC}/cost_report"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    params = {
        "starting_at": start_date,
        "ending_at": end_date
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            # Save full response
            output_file = f"{OUTPUT_DIR}/claude_cost_report_full.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✅ Saved to: {output_file}")
            print(f"   - Date buckets: {len(data.get('data', []))}")

            # Count total results
            total_results = sum(len(day.get('results', [])) for day in data.get('data', []))
            print(f"   - Total cost records: {total_results}")

            # Save sample with non-null fields (if any)
            print("\n📊 Analyzing fields...")
            non_null_samples = []
            for day in data.get('data', []):
                for result in day.get('results', []):
                    # Check if any metadata fields are non-null
                    if any(result.get(field) for field in ['workspace_id', 'description', 'model', 'cost_type', 'token_type']):
                        non_null_samples.append({
                            'date': day.get('starting_at'),
                            'result': result
                        })
                        if len(non_null_samples) >= 10:  # Get first 10 with metadata
                            break
                if len(non_null_samples) >= 10:
                    break

            if non_null_samples:
                sample_file = f"{OUTPUT_DIR}/claude_cost_report_with_metadata.json"
                with open(sample_file, 'w') as f:
                    json.dump(non_null_samples, f, indent=2)
                print(f"✅ Saved samples with metadata to: {sample_file}")
            else:
                print("⚠️  NO records found with non-null metadata fields")

            return data
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None


def save_claude_usage_report():
    """Save complete Claude Usage Report (Messages API) response."""
    print("\n" + "="*80)
    print("FETCHING: Claude Usage Report (Messages API)")
    print("="*80)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    url = f"{BASE_URL_ANTHROPIC}/usage_report/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    params = {
        "starting_at": start_date,
        "ending_at": end_date
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            output_file = f"{OUTPUT_DIR}/claude_usage_report_messages.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✅ Saved to: {output_file}")
            print(f"   - Date buckets: {len(data.get('data', []))}")

            total_results = sum(len(day.get('results', [])) for day in data.get('data', []))
            print(f"   - Total usage records: {total_results}")

            return data
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None


def save_cursor_usage():
    """Save complete Cursor usage response."""
    print("\n" + "="*80)
    print("FETCHING: Cursor Daily Usage Data")
    print("="*80)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)

    url = f"{BASE_URL_CURSOR}/teams/daily-usage-data"
    headers = {"Content-Type": "application/json"}
    payload = {"startDate": start_timestamp, "endDate": end_timestamp}

    try:
        response = requests.post(url, auth=(CURSOR_API_KEY, ""), headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()

            # Save full response
            output_file = f"{OUTPUT_DIR}/cursor_usage_full.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✅ Saved to: {output_file}")
            print(f"   - Total records: {len(data.get('data', []))}")

            # Save sample of active users with actual usage
            active_samples = [r for r in data.get('data', []) if r.get('isActive')][:20]

            if active_samples:
                sample_file = f"{OUTPUT_DIR}/cursor_usage_active_samples.json"
                with open(sample_file, 'w') as f:
                    json.dump(active_samples, f, indent=2)
                print(f"✅ Saved active user samples to: {sample_file}")
                print(f"   - Active users found: {len(active_samples)}")

            # Analyze field value ranges
            print("\n📊 Field Value Analysis:")
            if data.get('data'):
                for field in ['subscriptionIncludedReqs', 'usageBasedReqs', 'apiKeyReqs',
                             'composerRequests', 'chatRequests', 'totalLinesAdded']:
                    values = [r.get(field, 0) for r in data['data']]
                    non_zero = [v for v in values if v > 0]
                    if non_zero:
                        print(f"   - {field}: max={max(non_zero)}, records with data={len(non_zero)}")
                    else:
                        print(f"   - {field}: ALL ZERO")

            return data
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None


def main():
    print("\n" + "#"*80)
    print("# SAVING COMPLETE API RESPONSES")
    print("#"*80)

    print(f"\nOutput directory: {OUTPUT_DIR}")

    # Fetch all APIs
    claude_cost = save_claude_cost_report()
    claude_usage = save_claude_usage_report()
    cursor_usage = save_cursor_usage()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Claude Cost Report: {'SUCCESS' if claude_cost else 'FAILED'}")
    print(f"✅ Claude Usage Report: {'SUCCESS' if claude_usage else 'FAILED'}")
    print(f"✅ Cursor Usage: {'SUCCESS' if cursor_usage else 'FAILED'}")

    print(f"\n📁 All responses saved to: {OUTPUT_DIR}/")
    print("\nFiles created:")
    print("  - claude_cost_report_full.json")
    print("  - claude_usage_report_messages.json")
    print("  - cursor_usage_full.json")
    print("  - cursor_usage_active_samples.json")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
