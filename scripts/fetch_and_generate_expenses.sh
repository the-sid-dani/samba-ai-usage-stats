#!/bin/bash

# Fetch real expense data from APIs and generate CSV
# This script requires API keys to be set in environment or .env file

set -e

echo "=== AI Expense Report Generator ==="
echo ""

# Check for required API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$CURSOR_API_KEY" ]; then
    echo "❌ Error: API keys not found in environment"
    echo ""
    echo "Please set your API keys:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo "  export CURSOR_API_KEY='your-key-here'"
    echo ""
    echo "Or they should be available in Google Secret Manager"
    exit 1
fi

# Activate virtual environment
cd "$(dirname "$0")/.."
source venv/bin/activate

# Run Python script to fetch data
echo "📊 Fetching expense data from APIs..."
python3 <<'PYTHON_SCRIPT'
import os
import sys
from datetime import datetime, date, timedelta
from collections import defaultdict
import csv

sys.path.insert(0, '.')

# Import clients
try:
    from src.ingestion.cursor_client import CursorClient
    from src.ingestion.anthropic_client import AnthropicClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Fixed costs
CURSOR_FIXED = 50
CLAUDE_AI_FIXED = 40

# Generate months from Jun 2024 to Sep 2025
def generate_months():
    months = []
    start = date(2024, 6, 1)
    end = date(2025, 9, 30)
    current = start
    while current <= end:
        months.append((current.strftime('%b %Y'), current))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months

print("Generating expense report...")

months = generate_months()

# Prepare data structure
cursor_api_costs = {}
claude_api_costs = {}

# Try to fetch Cursor data
try:
    print("  Fetching Cursor API data...")
    cursor_client = CursorClient()

    for month_label, month_start in months:
        # Get end of month
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        # Limit to today
        month_end = min(month_end, date.today())

        if month_start > date.today():
            cursor_api_costs[month_label] = 0
            continue

        try:
            usage_records = cursor_client.get_daily_usage_data(month_start, month_end)
            # Calculate API costs: api_key_reqs * estimated cost per request
            total_api_reqs = sum(r.api_key_reqs for r in usage_records)
            cursor_api_costs[month_label] = total_api_reqs * 0.01  # $0.01 per API request estimate
        except Exception as e:
            print(f"    Warning: Could not fetch Cursor data for {month_label}: {e}")
            cursor_api_costs[month_label] = 0

except Exception as e:
    print(f"  ❌ Cursor client error: {e}")
    print("  Using zeros for Cursor API costs")
    for month_label, _ in months:
        cursor_api_costs[month_label] = 0

# Try to fetch Claude API data
try:
    print("  Fetching Claude API data...")
    anthropic_client = AnthropicClient()

    for month_label, month_start in months:
        # Get end of month
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        # Limit to today
        month_end = min(month_end, date.today())

        if month_start > date.today():
            claude_api_costs[month_label] = 0
            continue

        try:
            cost_records = anthropic_client.get_cost_data(month_start, month_end)
            total_cost = sum(r.cost_usd for r in cost_records)
            claude_api_costs[month_label] = total_cost
        except Exception as e:
            print(f"    Warning: Could not fetch Claude cost data for {month_label}: {e}")
            claude_api_costs[month_label] = 0

except Exception as e:
    print(f"  ❌ Anthropic client error: {e}")
    print("  Using zeros for Claude API costs")
    for month_label, _ in months:
        claude_api_costs[month_label] = 0

# Generate CSV
output_path = 'data/expenses.csv'
print(f"\n📝 Writing to {output_path}...")

with open(output_path, 'w', newline='') as f:
    writer = csv.writer(f)

    # Header
    header = ['Cost Category'] + [m[0] for m in months]
    writer.writerow(header)

    # Cursor Fixed
    writer.writerow(['Cursor (Fixed)'] + [CURSOR_FIXED] * len(months))

    # Cursor API Variable
    writer.writerow(['Claude API - Cursor (Variable)'] +
                   [f"{cursor_api_costs.get(m[0], 0):.2f}" for m in months])

    # Claude.ai Fixed
    writer.writerow(['Claude.ai (Fixed)'] + [CLAUDE_AI_FIXED] * len(months))

    # Claude API Variable
    writer.writerow(['Claude API - Claude.ai (Variable)'] +
                   [f"{claude_api_costs.get(m[0], 0):.2f}" for m in months])

    # Total
    totals = []
    for month_label, _ in months:
        total = (CURSOR_FIXED + CLAUDE_AI_FIXED +
                cursor_api_costs.get(month_label, 0) +
                claude_api_costs.get(month_label, 0))
        totals.append(f"{total:.2f}")
    writer.writerow(['Total Monthly Cost'] + totals)

print(f"\n✅ Expense report generated: {output_path}")

# Summary
total_fixed = (CURSOR_FIXED + CLAUDE_AI_FIXED) * len(months)
total_cursor_api = sum(cursor_api_costs.values())
total_claude_api = sum(claude_api_costs.values())
grand_total = total_fixed + total_cursor_api + total_claude_api

print(f"\n=== Summary ===")
print(f"Total Fixed Costs:      ${total_fixed:,.2f}")
print(f"Total Cursor API:       ${total_cursor_api:,.2f}")
print(f"Total Claude API:       ${total_claude_api:,.2f}")
print(f"Grand Total:            ${grand_total:,.2f}")

PYTHON_SCRIPT

echo ""
echo "Done! Open data/expenses.csv in Excel to view the report."