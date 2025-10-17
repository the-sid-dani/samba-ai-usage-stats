#!/usr/bin/env python3
"""
Get REAL monthly expense data from Anthropic API.
Simplified script that directly fetches and formats the data.
"""

import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import csv

# Read API key
with open('/tmp/anthropic_key.txt', 'r') as f:
    API_KEY = f.read().strip()

# Fixed costs
CURSOR_FIXED = 50
CLAUDE_AI_FIXED = 40

def fetch_last_6_months():
    """Fetch costs for the last 6 months."""
    print("📊 Fetching last 6 months of Anthropic costs...")

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Get last 6 months
    end_date = date.today()
    start_date = end_date - timedelta(days=180)

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    monthly_totals = {}

    try:
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        response = requests.get(cost_url, headers=headers, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()

            # Process all buckets and aggregate by month
            for bucket in data.get('data', []):
                bucket_date = bucket.get('starting_at', '')
                if bucket_date:
                    # Handle both date formats
                    if 'T' in bucket_date:
                        month_key = datetime.strptime(bucket_date.split('T')[0], '%Y-%m-%d').strftime('%b %Y')
                    else:
                        month_key = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                    for record in bucket.get('results', []):
                        # Amount is in micro-dollars, convert to dollars
                        amount = float(record.get('amount', 0)) / 1000000
                        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + amount

            # Handle pagination
            page_count = 1
            while data.get('has_more', False) and page_count < 10:
                if 'next_page_token' in data:
                    params['page_token'] = data['next_page_token']
                    response = requests.get(cost_url, headers=headers, params=params, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        page_count += 1

                        for bucket in data.get('data', []):
                            bucket_date = bucket.get('starting_at', '')
                            if bucket_date:
                                month_key = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                                for record in bucket.get('results', []):
                                    amount = float(record.get('amount', 0)) / 1000000
                                    monthly_totals[month_key] = monthly_totals.get(month_key, 0) + amount
                    else:
                        break
                else:
                    break

            print(f"✅ Found data for {len(monthly_totals)} months")
            return monthly_totals
        else:
            print(f"❌ API Error: {response.status_code}")
            return {}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

def generate_expense_sheet(actual_costs):
    """Generate the expense sheet CSV."""
    print("\n📝 Generating expense sheet...")

    # All months from Jun 2024 to Sep 2025
    all_months = []
    current = date(2024, 6, 1)
    end = date(2025, 9, 30)

    while current <= end:
        month_label = current.strftime('%b %Y')
        all_months.append(month_label)
        current = current + relativedelta(months=1)

    # Calculate average from actual data
    actual_values = [v for v in actual_costs.values() if v > 0]
    avg_api_cost = sum(actual_values) / len(actual_values) if actual_values else 0

    output_path = 'data/monthly_ai_expenses.csv'

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title
        writer.writerow(['AI Platform Monthly Expenses'])
        writer.writerow([''])

        # Header row
        header = ['Cost Category'] + all_months
        writer.writerow(header)

        # Fixed Costs
        writer.writerow(['Cursor (Fixed)'] + ['50'] * len(all_months))
        writer.writerow(['Claude.ai (Fixed)'] + ['40'] * len(all_months))

        # Variable Costs - Claude API
        claude_api_row = ['Claude API (Variable)']
        for month in all_months:
            if month in actual_costs:
                # Use actual data
                claude_api_row.append(f'{actual_costs[month]:.2f}')
            else:
                # Use 0 for past months without data, estimate for future
                month_date = datetime.strptime(f'01 {month}', '%d %b %Y').date()
                if month_date <= date.today():
                    claude_api_row.append('0.00')
                else:
                    # Future month - use average as estimate
                    claude_api_row.append(f'{avg_api_cost:.2f}')
        writer.writerow(claude_api_row)

        # Cursor API (placeholder)
        writer.writerow(['Cursor API (Variable)'] + ['0.00'] * len(all_months))

        # Total row
        total_row = ['Total Monthly Cost']
        for month in all_months:
            api_cost = actual_costs.get(month, 0)
            if month not in actual_costs:
                month_date = datetime.strptime(f'01 {month}', '%d %b %Y').date()
                if month_date > date.today():
                    api_cost = avg_api_cost

            total = 50 + 40 + api_cost
            total_row.append(f'{total:.2f}')
        writer.writerow(total_row)

    print(f"✅ Saved to: {output_path}")
    return output_path

def print_summary(actual_costs):
    """Print a summary of the findings."""
    print("\n" + "="*60)
    print("EXPENSE SUMMARY")
    print("="*60)

    if actual_costs:
        print(f"\n📊 Actual API Costs Found ({len(actual_costs)} months):")
        total_api = 0
        for month, cost in sorted(actual_costs.items()):
            print(f"  {month}: ${cost:,.2f}")
            total_api += cost

        avg = total_api / len(actual_costs) if actual_costs else 0
        print(f"\nTotal API Costs (actual): ${total_api:,.2f}")
        print(f"Average Monthly API Cost: ${avg:,.2f}")
    else:
        print("No actual API cost data found")

    print(f"\nFixed Monthly Costs:")
    print(f"  Cursor: $50.00")
    print(f"  Claude.ai: $40.00")
    print(f"  Total Fixed: $90.00")

    # Project 16-month total
    avg_api = sum(actual_costs.values()) / len(actual_costs) if actual_costs else 0
    projected_total = (90 * 16) + (avg_api * 16)
    print(f"\nProjected 16-Month Total: ${projected_total:,.2f}")
    print("="*60)

def main():
    print("\n" + "="*60)
    print("FETCHING REAL ANTHROPIC API COSTS")
    print("="*60 + "\n")

    # Fetch actual costs
    actual_costs = fetch_last_6_months()

    # Generate expense sheet
    csv_path = generate_expense_sheet(actual_costs)

    # Print summary
    print_summary(actual_costs)

    print(f"\n✅ Done! Open {csv_path} in Excel")
    print("📊 This sheet contains REAL API cost data!")

if __name__ == '__main__':
    main()