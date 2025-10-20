#!/usr/bin/env python3
"""
Test Cursor spend delta calculation with Oct 18-20 data

This validates the delta logic before deploying to production.
"""

import os
from datetime import datetime, timezone
from google.cloud import bigquery, secretmanager
from cursor_client import CursorAdminClient
from ingest_cursor_daily import (
    get_cursor_api_key,
    calculate_daily_spend_deltas
)

def test_with_october_data():
    """Test delta calculation with real October data"""
    print("=" * 70)
    print("TESTING CURSOR SPEND DELTA CALCULATION")
    print("=" * 70)

    # Initialize clients
    secret_client = secretmanager.SecretManagerServiceClient()
    bq_client = bigquery.Client(project='ai-workflows-459123')
    cursor_api_key = get_cursor_api_key(secret_client)
    cursor_client = CursorAdminClient(cursor_api_key)

    # Fetch current spend
    print("\n1. Fetching current spend from /teams/spend...")
    spend_members, billing_cycle_start_ms = cursor_client.get_all_spend_pages()
    billing_cycle_start = datetime.fromtimestamp(
        billing_cycle_start_ms / 1000,
        tz=timezone.utc
    )

    print(f"   Billing cycle started: {billing_cycle_start}")
    print(f"   Team members: {len(spend_members)}")

    # Test Oct 18 delta calculation
    print("\n2. Simulating Oct 18 delta (first snapshot)...")
    oct18 = datetime(2025, 10, 18, 0, 0, 0, tzinfo=timezone.utc)
    deltas_oct18 = calculate_daily_spend_deltas(
        bq_client,
        spend_members,
        billing_cycle_start,
        oct18
    )

    users_with_spend_18 = {k: v for k, v in deltas_oct18.items() if v > 0}
    print(f"   Users with spend: {len(users_with_spend_18)}")
    print(f"   Total spend Oct 18: ${sum(deltas_oct18.values()):.2f}")

    if users_with_spend_18:
        top_5 = sorted(users_with_spend_18.items(), key=lambda x: x[1], reverse=True)[:5]
        print("   Top 5 spenders:")
        for email, cost in top_5:
            print(f"     {email}: ${cost:.2f}")

    # Test Oct 20 delta calculation
    print("\n3. Simulating Oct 20 delta (second snapshot)...")
    oct20 = datetime(2025, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    deltas_oct20 = calculate_daily_spend_deltas(
        bq_client,
        spend_members,
        billing_cycle_start,
        oct20
    )

    users_with_spend_20 = {k: v for k, v in deltas_oct20.items() if v > 0}
    print(f"   Users with spend: {len(users_with_spend_20)}")
    print(f"   Total spend Oct 20: ${sum(deltas_oct20.values()):.2f}")

    # Validation
    print("\n4. VALIDATION:")
    print("   Expected behavior:")
    print("     Oct 18: High total (cumulative since Oct 3)")
    print("     Oct 20: Low/zero total (little change from Oct 18)")

    print(f"\n   Actual results:")
    print(f"     Oct 18 total: ${sum(deltas_oct18.values()):.2f}")
    print(f"     Oct 20 total: ${sum(deltas_oct20.values()):.2f}")

    # Check for negatives
    negatives_18 = {k: v for k, v in deltas_oct18.items() if v < 0}
    negatives_20 = {k: v for k, v in deltas_oct20.items() if v < 0}

    if negatives_18 or negatives_20:
        print(f"\n   ⚠️  WARNING: Found negative deltas!")
        print(f"     Oct 18 negatives: {len(negatives_18)}")
        print(f"     Oct 20 negatives: {len(negatives_20)}")
    else:
        print(f"\n   ✅ PASS: No negative deltas")

    # Validate against known October invoice
    print("\n5. Invoice Validation:")
    print(f"   October invoice total: $41.92")
    print(f"   Our calculated total: ${sum(deltas_oct18.values()) + sum(deltas_oct20.values()):.2f}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    test_with_october_data()
