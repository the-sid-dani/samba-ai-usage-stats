#!/usr/bin/env python3
"""
Generate ACCURATE expense report understanding that Cursor API usage
is billed through Anthropic, not separately.
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
CURSOR_FIXED = 50  # Cursor subscription
CLAUDE_AI_FIXED = 40  # Claude.ai subscription

def fetch_all_anthropic_costs():
    """Fetch ALL Anthropic costs (includes both direct and Cursor usage)."""
    print("📊 Fetching complete Anthropic billing (includes Cursor API usage)...")

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    all_costs = defaultdict(float)

    # Based on the invoice, we know these are actual costs
    known_costs = {
        'Aug 2025': 827.15,  # From invoice
        'Sep 2025': 1089.33,  # Current invoice shows
    }

    # Try to fetch all available data
    end_date = date.today()
    start_date = date(2024, 1, 1)  # Go back further

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    try:
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        response = requests.get(cost_url, headers=headers, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()

            for bucket in data.get('data', []):
                bucket_date = bucket.get('starting_at', '')
                if bucket_date:
                    # Handle date format
                    if 'T' in bucket_date:
                        month_key = datetime.strptime(bucket_date.split('T')[0], '%Y-%m-%d').strftime('%b %Y')
                    else:
                        month_key = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                    for record in bucket.get('results', []):
                        amount = record.get('amount', 0)
                        if isinstance(amount, str):
                            amount = float(amount)
                        # Convert cents to dollars
                        amount_dollars = amount / 100
                        all_costs[month_key] += amount_dollars

            # Handle pagination
            page_count = 1
            while data.get('has_more', False) and page_count < 50:
                if 'next_page' in data:
                    params['page_token'] = data['next_page']
                    response = requests.get(cost_url, headers=headers, params=params, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        page_count += 1

                        for bucket in data.get('data', []):
                            bucket_date = bucket.get('starting_at', '')
                            if bucket_date:
                                if 'T' in bucket_date:
                                    month_key = datetime.strptime(bucket_date.split('T')[0], '%Y-%m-%d').strftime('%b %Y')
                                else:
                                    month_key = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                                for record in bucket.get('results', []):
                                    amount = record.get('amount', 0)
                                    if isinstance(amount, str):
                                        amount = float(amount)
                                    amount_dollars = amount / 100
                                    all_costs[month_key] += amount_dollars
                    else:
                        break
                else:
                    break

    except Exception as e:
        print(f"  API fetch error: {e}")

    # Override with known invoice amounts
    for month, cost in known_costs.items():
        all_costs[month] = cost
        print(f"  ✅ {month}: ${cost:,.2f} (from invoice)")

    return all_costs

def generate_accurate_expense_report(all_costs):
    """Generate accurate expense report."""
    print("\n📝 Generating accurate expense report...")

    # All months from Jun 2024 to Sep 2025
    all_months = []
    current = date(2024, 6, 1)
    end = date(2025, 9, 30)

    while current <= end:
        month_label = current.strftime('%b %Y')
        all_months.append(month_label)
        current = current + relativedelta(months=1)

    output_path = 'data/accurate_ai_expenses.csv'

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title
        writer.writerow(['AI Platform Usage & Cost Report - ACCURATE'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([''])

        # Header row
        header = ['Cost Category'] + all_months
        writer.writerow(header)

        # FIXED COSTS SECTION
        writer.writerow([''])
        writer.writerow(['FIXED COSTS (Subscriptions)'])
        writer.writerow(['Cursor Subscription'] + ['50.00'] * len(all_months))
        writer.writerow(['Claude.ai Subscription'] + ['40.00'] * len(all_months))
        writer.writerow(['Total Fixed'] + ['90.00'] * len(all_months))

        # VARIABLE COSTS SECTION
        writer.writerow([''])
        writer.writerow(['VARIABLE COSTS (API Usage)'])

        # Combined Anthropic API costs (includes Cursor's usage)
        api_row = ['Anthropic API (includes Cursor usage)']
        for month in all_months:
            cost = all_costs.get(month, 0)
            api_row.append(f'{cost:.2f}')
        writer.writerow(api_row)

        # Breakdown if known
        writer.writerow(['  - Direct Claude API usage'] + ['—'] * len(all_months))
        writer.writerow(['  - Cursor API usage (via Anthropic)'] + ['—'] * len(all_months))

        # Total Variable
        writer.writerow(['Total Variable'] + [f'{all_costs.get(month, 0):.2f}' for month in all_months])

        # GRAND TOTALS
        writer.writerow([''])
        writer.writerow(['TOTALS'])

        monthly_total_row = ['Monthly Total']
        cumulative_row = ['Cumulative']
        cumulative = 0

        for month in all_months:
            fixed = 90.00
            variable = all_costs.get(month, 0)
            total = fixed + variable
            cumulative += total

            monthly_total_row.append(f'{total:.2f}')
            cumulative_row.append(f'{cumulative:.2f}')

        writer.writerow(monthly_total_row)
        writer.writerow(cumulative_row)

        # COST BREAKDOWN
        writer.writerow([''])
        writer.writerow(['COST ANALYSIS'])

        pct_fixed_row = ['% Fixed']
        pct_variable_row = ['% Variable']

        for month in all_months:
            total = 90 + all_costs.get(month, 0)
            if total > 0:
                pct_fixed = (90 / total) * 100
                pct_variable = (all_costs.get(month, 0) / total) * 100
                pct_fixed_row.append(f'{pct_fixed:.1f}%')
                pct_variable_row.append(f'{pct_variable:.1f}%')
            else:
                pct_fixed_row.append('100.0%')
                pct_variable_row.append('0.0%')

        writer.writerow(pct_fixed_row)
        writer.writerow(pct_variable_row)

        # SUMMARY
        writer.writerow([''])
        writer.writerow(['SUMMARY'])

        total_fixed = 90 * 16
        total_variable = sum(all_costs.values())
        grand_total = total_fixed + total_variable

        writer.writerow(['Total Fixed (16 months)', f'${total_fixed:,.2f}'])
        writer.writerow(['Total Variable (API)', f'${total_variable:,.2f}'])
        writer.writerow(['GRAND TOTAL', f'${grand_total:,.2f}'])

        # Calculate monthly average
        months_with_data = len([c for c in all_costs.values() if c > 0])
        avg_monthly_api = total_variable / months_with_data if months_with_data > 0 else 0
        writer.writerow(['Average Monthly API', f'${avg_monthly_api:,.2f}'])

        # NOTES
        writer.writerow([''])
        writer.writerow(['IMPORTANT NOTES:'])
        writer.writerow(['1. Cursor API usage is billed through Anthropic (not separate)'])
        writer.writerow(['2. Fixed costs: Cursor subscription ($50/mo) + Claude.ai subscription ($40/mo)'])
        writer.writerow(['3. Variable costs: All API usage (both direct and via Cursor) billed by Anthropic'])
        writer.writerow(['4. Known invoice amounts: Aug 2025 = $827.15, Sep 2025 = $1089.33'])
        writer.writerow([f'5. Data retrieved: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])

    print(f"✅ Saved to: {output_path}")
    return output_path, grand_total, total_variable, avg_monthly_api

def main():
    print("\n" + "="*70)
    print("ACCURATE AI EXPENSE REPORT")
    print("Understanding: Cursor API usage is billed through Anthropic")
    print("="*70)

    # Fetch all costs
    all_costs = fetch_all_anthropic_costs()

    # Generate report
    csv_path, grand_total, total_api, avg_api = generate_accurate_expense_report(all_costs)

    # Print summary
    print("\n" + "="*70)
    print("ACCURATE EXPENSE SUMMARY")
    print("="*70)

    print(f"\n📊 Key Findings:")
    print(f"1. Cursor's API usage is billed through Anthropic (not separate)")
    print(f"2. Your invoice shows significant API costs:")
    print(f"   - Aug 2025: $827.15")
    print(f"   - Sep 2025: $1,089.33")

    print(f"\n💰 Totals:")
    print(f"Fixed Monthly: $90.00 (Cursor + Claude.ai subscriptions)")
    print(f"Total API Costs: ${total_api:,.2f}")
    print(f"Average Monthly API: ${avg_api:,.2f}")
    print(f"16-Month Grand Total: ${grand_total:,.2f}")

    print("="*70)
    print(f"\n✅ Complete! Open {csv_path} in Excel")
    print("📊 This reflects the TRUE cost structure with Cursor billed via Anthropic")

if __name__ == '__main__':
    main()