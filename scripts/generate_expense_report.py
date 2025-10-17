#!/usr/bin/env python3
"""
Generate expense report with real data from BigQuery.
Aggregates costs by month for June 2024 through September 2025.

Usage:
    source venv/bin/activate
    python scripts/generate_expense_report.py
"""

import os
import sys
from datetime import datetime, date, timedelta
from collections import defaultdict
import csv
from google.cloud import bigquery

# Fixed costs
CURSOR_FIXED = 50  # $50/month subscription
CLAUDE_AI_FIXED = 40  # $40/month subscription

def generate_months():
    """Generate list of (label, start_date, end_date) tuples from Jun 2024 to Sep 2025."""
    months = []
    start = date(2024, 6, 1)
    end = date(2025, 9, 30)
    current = start

    while current <= end:
        # Get end of month
        if current.month == 12:
            month_end = date(current.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(current.year, current.month + 1, 1) - timedelta(days=1)

        # Don't go past today
        month_end = min(month_end, date.today())

        months.append((current.strftime('%b %Y'), current, month_end))

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return months

def fetch_costs_from_bigquery():
    """Fetch actual costs from BigQuery tables."""
    print("📊 Fetching data from BigQuery...")

    client = bigquery.Client(project="ai-workflows-459123")

    cursor_costs = {}
    claude_costs = {}
    months = generate_months()

    # Try to get Claude API costs from raw_anthropic_cost table
    print("\n  Fetching Claude API costs...")
    try:
        for month_label, month_start, month_end in months:
            if month_start > date.today():
                claude_costs[month_label] = 0
                continue

            # Query with partition filter
            cost_query = f"""
            SELECT SUM(cost_usd) as total_cost
            FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost`
            WHERE cost_date BETWEEN '{month_start}' AND '{month_end}'
              AND ingest_date >= '{month_start}'
            """

            try:
                result = client.query(cost_query).result()
                for row in result:
                    total = row['total_cost'] if row['total_cost'] else 0
                    claude_costs[month_label] = total
                    print(f"    {month_label}: ${total:.2f}")
                    break
            except Exception as e:
                print(f"    {month_label}: Error - {e}")
                claude_costs[month_label] = 0

    except Exception as e:
        print(f"  ❌ Error fetching Claude costs: {e}")
        for month_label, _, _ in months:
            claude_costs[month_label] = 0

    # Try to get Cursor costs (if they exist in BigQuery)
    print("\n  Fetching Cursor costs...")
    try:
        for month_label, month_start, month_end in months:
            if month_start > date.today():
                cursor_costs[month_label] = 0
                continue

            # Query Cursor usage - estimate API costs
            cursor_query = f"""
            SELECT SUM(api_key_reqs) as total_api_reqs
            FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
            WHERE date BETWEEN '{month_start}' AND '{month_end}'
            """

            try:
                result = client.query(cursor_query).result()
                for row in result:
                    api_reqs = row['total_api_reqs'] if row['total_api_reqs'] else 0
                    # Estimate $0.01 per API request
                    cost = api_reqs * 0.01
                    cursor_costs[month_label] = cost
                    print(f"    {month_label}: ${cost:.2f} ({api_reqs:,} API reqs)")
                    break
            except Exception as e:
                # Table might not exist or different schema
                cursor_costs[month_label] = 0

    except Exception as e:
        print(f"  ❌ Error fetching Cursor costs: {e}")
        for month_label, _, _ in months:
            cursor_costs[month_label] = 0

    return cursor_costs, claude_costs

def generate_csv(cursor_costs, claude_costs):
    """Generate the expense CSV file."""
    print("\n📝 Generating CSV...")

    months = generate_months()
    output_path = 'data/expenses.csv'

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        header = ['Cost Category'] + [m[0] for m in months]
        writer.writerow(header)

        # Cursor Fixed
        writer.writerow(['Cursor (Fixed)'] + [CURSOR_FIXED] * len(months))

        # Cursor API Variable
        writer.writerow(['Claude API - Cursor (Variable)'] +
                       [f"{cursor_costs.get(m[0], 0):.2f}" for m in months])

        # Claude.ai Fixed
        writer.writerow(['Claude.ai (Fixed)'] + [CLAUDE_AI_FIXED] * len(months))

        # Claude API Variable
        writer.writerow(['Claude API - Claude.ai (Variable)'] +
                       [f"{claude_costs.get(m[0], 0):.2f}" for m in months])

        # Total row
        totals = []
        for month_label, _, _ in months:
            total = (CURSOR_FIXED + CLAUDE_AI_FIXED +
                    cursor_costs.get(month_label, 0) +
                    claude_costs.get(month_label, 0))
            totals.append(f"{total:.2f}")
        writer.writerow(['Total Monthly Cost'] + totals)

    print(f"✅ Saved to: {output_path}")
    return output_path

def print_summary(cursor_costs, claude_costs):
    """Print expense summary."""
    months = generate_months()

    total_fixed = (CURSOR_FIXED + CLAUDE_AI_FIXED) * len(months)
    total_cursor_api = sum(cursor_costs.values())
    total_claude_api = sum(claude_costs.values())
    grand_total = total_fixed + total_cursor_api + total_claude_api

    print("\n" + "="*50)
    print("EXPENSE SUMMARY")
    print("="*50)
    print(f"Period:                 {months[0][0]} - {months[-1][0]}")
    print(f"Months:                 {len(months)}")
    print(f"\nTotal Fixed Costs:      ${total_fixed:,.2f}")
    print(f"  Cursor:               ${CURSOR_FIXED * len(months):,.2f}")
    print(f"  Claude.ai:            ${CLAUDE_AI_FIXED * len(months):,.2f}")
    print(f"\nTotal Variable Costs:   ${total_cursor_api + total_claude_api:,.2f}")
    print(f"  Cursor API:           ${total_cursor_api:,.2f}")
    print(f"  Claude API:           ${total_claude_api:,.2f}")
    print(f"\nGrand Total:            ${grand_total:,.2f}")
    print("="*50)

def main():
    print("\n" + "="*50)
    print("AI EXPENSE REPORT GENERATOR")
    print("="*50 + "\n")

    # Fetch data from BigQuery
    cursor_costs, claude_costs = fetch_costs_from_bigquery()

    # Generate CSV
    generate_csv(cursor_costs, claude_costs)

    # Print summary
    print_summary(cursor_costs, claude_costs)

    print("\n✅ Done! Open data/expenses.csv in Excel.")

if __name__ == '__main__':
    main()