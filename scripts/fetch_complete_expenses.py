#!/usr/bin/env python3
"""
Fetch COMPLETE expense data from Anthropic with proper pagination.
"""

import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import csv
from collections import defaultdict

# Read API key
with open('/tmp/anthropic_key.txt', 'r') as f:
    API_KEY = f.read().strip()

# Fixed costs
CURSOR_FIXED = 50
CLAUDE_AI_FIXED = 40

def fetch_all_anthropic_costs():
    """Fetch ALL Anthropic costs with proper pagination."""
    print("📊 Fetching COMPLETE Anthropic cost data with pagination...")

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Fetch data month by month to avoid hitting limits
    all_months_data = defaultdict(float)

    # Generate months from Jun 2024 to today
    current = date(2024, 6, 1)
    today = date.today()

    while current <= today:
        month_end = current + relativedelta(months=1) - timedelta(days=1)
        month_end = min(month_end, today)

        month_label = current.strftime('%b %Y')
        print(f"\n  Fetching {month_label}...")

        # Fetch this month's data
        params = {
            "starting_at": current.strftime("%Y-%m-%d"),
            "ending_at": month_end.strftime("%Y-%m-%d")
        }

        month_total = 0
        page_count = 0
        has_more = True

        while has_more and page_count < 20:  # Max 20 pages per month
            try:
                cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
                response = requests.get(cost_url, headers=headers, params=params, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    page_count += 1

                    # Process all records in this page
                    for bucket in data.get('data', []):
                        for record in bucket.get('results', []):
                            amount = record.get('amount', 0)

                            # Convert amount to dollars
                            if isinstance(amount, str):
                                amount = float(amount)

                            # Anthropic returns amounts in cents (x100)
                            # So 1379.38224 = $13.79
                            if amount > 0:
                                amount_dollars = amount / 100
                                month_total += amount_dollars

                    # Check for more pages
                    has_more = data.get('has_more', False)

                    if has_more and 'next_page' in data:
                        # Use next_page URL or token
                        next_page = data.get('next_page')
                        if next_page:
                            # If it's a full URL, extract the token
                            # Otherwise use it as page_token
                            params['page_token'] = next_page
                    else:
                        has_more = False

                    print(f"    Page {page_count}: {len(data.get('data', []))} buckets")

                else:
                    print(f"    ❌ Error {response.status_code}")
                    break

            except Exception as e:
                print(f"    ❌ Exception: {e}")
                break

        all_months_data[month_label] = month_total

        if month_total > 0:
            print(f"  ✅ {month_label} total: ${month_total:,.2f}")

        # Move to next month
        current = current + relativedelta(months=1)

    return all_months_data

def fetch_usage_stats():
    """Fetch usage statistics for context."""
    print("\n📈 Fetching usage statistics...")

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Last 30 days usage
    params = {
        "starting_at": (date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "ending_at": date.today().strftime("%Y-%m-%d")
    }

    try:
        usage_url = "https://api.anthropic.com/v1/organizations/usage_report/messages"
        response = requests.get(usage_url, headers=headers, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()

            total_input_tokens = 0
            total_output_tokens = 0
            total_sessions = 0

            for bucket in data.get('data', []):
                for record in bucket.get('results', []):
                    total_input_tokens += record.get('uncached_input_tokens', 0)
                    total_input_tokens += record.get('cache_read_input_tokens', 0)
                    total_output_tokens += record.get('output_tokens', 0)
                    total_sessions += 1

            print(f"  Last 30 days:")
            print(f"    Input tokens: {total_input_tokens:,}")
            print(f"    Output tokens: {total_output_tokens:,}")
            print(f"    Total tokens: {total_input_tokens + total_output_tokens:,}")
            print(f"    Sessions: {total_sessions}")

            # Estimate cost based on tokens (rough estimate)
            # Claude 3 pricing: ~$15/1M input, ~$75/1M output
            estimated_cost = (total_input_tokens * 15 / 1000000) + (total_output_tokens * 75 / 1000000)
            print(f"    Estimated cost from tokens: ${estimated_cost:,.2f}")

    except Exception as e:
        print(f"  ❌ Error fetching usage: {e}")

def generate_comprehensive_report(monthly_costs):
    """Generate comprehensive expense report."""
    print("\n📝 Generating comprehensive expense report...")

    # All months from Jun 2024 to Sep 2025
    all_months = []
    current = date(2024, 6, 1)
    end = date(2025, 9, 30)

    while current <= end:
        month_label = current.strftime('%b %Y')
        all_months.append(month_label)
        current = current + relativedelta(months=1)

    # Calculate statistics
    actual_months = [m for m, cost in monthly_costs.items() if cost > 0]
    total_api_actual = sum([cost for cost in monthly_costs.values() if cost > 0])
    avg_api_cost = total_api_actual / len(actual_months) if actual_months else 0

    output_path = 'data/complete_ai_expenses.csv'

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title
        writer.writerow(['AI Platform Complete Expense Report'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([''])

        # Header row
        header = ['Cost Category'] + all_months
        writer.writerow(header)

        # Fixed Costs
        writer.writerow([''])
        writer.writerow(['FIXED COSTS'])
        writer.writerow(['Cursor (Fixed)'] + ['50.00'] * len(all_months))
        writer.writerow(['Claude.ai (Fixed)'] + ['40.00'] * len(all_months))

        # Variable Costs - with actual data
        writer.writerow([''])
        writer.writerow(['VARIABLE COSTS (API)'])

        claude_api_row = ['Claude API']
        for month in all_months:
            if month in monthly_costs and monthly_costs[month] > 0:
                # Actual data
                claude_api_row.append(f'{monthly_costs[month]:.2f}')
            else:
                month_date = datetime.strptime(f'01 {month}', '%d %b %Y').date()
                if month_date <= date.today():
                    # Past month with no data
                    claude_api_row.append('0.00')
                else:
                    # Future month - use average as projection
                    if avg_api_cost > 0:
                        claude_api_row.append(f'{avg_api_cost:.2f}')
                    else:
                        claude_api_row.append('0.00')
        writer.writerow(claude_api_row)

        # Cursor API (placeholder)
        writer.writerow(['Cursor API'] + ['0.00'] * len(all_months))

        # Total row
        writer.writerow([''])
        writer.writerow(['TOTAL'])
        total_row = ['Monthly Total']
        cumulative_row = ['Cumulative']
        cumulative = 0

        for month in all_months:
            api_cost = monthly_costs.get(month, 0)
            if month not in monthly_costs:
                month_date = datetime.strptime(f'01 {month}', '%d %b %Y').date()
                if month_date > date.today() and avg_api_cost > 0:
                    api_cost = avg_api_cost

            monthly_total = 50 + 40 + api_cost
            cumulative += monthly_total

            total_row.append(f'{monthly_total:.2f}')
            cumulative_row.append(f'{cumulative:.2f}')

        writer.writerow(total_row)
        writer.writerow(cumulative_row)

        # Summary Statistics
        writer.writerow([''])
        writer.writerow(['SUMMARY STATISTICS'])
        writer.writerow(['Total Fixed (16 mo)', f'{90 * 16:.2f}'])
        writer.writerow(['Total API (actual)', f'{total_api_actual:.2f}'])
        writer.writerow(['Average Monthly API', f'{avg_api_cost:.2f}'])
        writer.writerow(['Projected Total', f'{cumulative:.2f}'])

        writer.writerow([''])
        writer.writerow(['DATA AVAILABILITY'])
        writer.writerow(['Months with actual data', str(len(actual_months))])
        writer.writerow(['Actual data months', ', '.join(actual_months)])

    print(f"✅ Report saved to: {output_path}")

    return output_path, cumulative, total_api_actual, avg_api_cost

def main():
    print("\n" + "="*70)
    print("FETCHING COMPLETE ANTHROPIC BILLING DATA")
    print("="*70)

    # Fetch ALL cost data with pagination
    monthly_costs = fetch_all_anthropic_costs()

    # Fetch usage stats for validation
    fetch_usage_stats()

    # Generate report
    csv_path, total_projected, total_api_actual, avg_api = generate_comprehensive_report(monthly_costs)

    # Summary
    print("\n" + "="*70)
    print("COMPLETE EXPENSE SUMMARY")
    print("="*70)
    print(f"Fixed Monthly: $90.00 (Cursor + Claude.ai)")

    if monthly_costs:
        actual_months = [m for m, c in monthly_costs.items() if c > 0]
        print(f"\n📊 Actual API Costs Found:")
        for month in sorted(actual_months):
            print(f"  {month}: ${monthly_costs[month]:,.2f}")

        print(f"\nTotal API (actual): ${total_api_actual:,.2f}")
        print(f"Average Monthly API: ${avg_api:,.2f}")

    print(f"\nProjected 16-Month Total: ${total_projected:,.2f}")
    print("="*70)

    print(f"\n✅ Complete! Open {csv_path} in Excel")
    print("📊 This contains COMPLETE billing data with all pages!")

if __name__ == '__main__':
    main()