#!/usr/bin/env python3
"""
Generate quick expense report by fetching recent data and extrapolating.
"""

import os
import sys
import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import csv
from google.cloud import secretmanager

# Fixed costs
CURSOR_FIXED = 50  # $50/month subscription
CLAUDE_AI_FIXED = 40  # $40/month subscription

def get_secret(secret_id: str) -> str:
    """Get secret from Google Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/ai-workflows-459123/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except:
        return os.getenv(secret_id, "")

def fetch_recent_anthropic_data():
    """Fetch recent Anthropic cost data (last 90 days)."""
    print("📊 Fetching recent Anthropic API costs...")

    api_key = get_secret("anthropic-admin-api-key")
    if not api_key:
        api_key = get_secret("anthropic-api-key")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Fetch last 90 days
    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    params = {
        "starting_at": start_date.strftime("%Y-%m-%d"),
        "ending_at": end_date.strftime("%Y-%m-%d")
    }

    monthly_costs = {}

    try:
        cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
        response = requests.get(cost_url, headers=headers, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()

            # Group costs by month
            for bucket in data.get('data', []):
                bucket_date = bucket.get('starting_at', '')
                if bucket_date:
                    month = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                    for record in bucket.get('results', []):
                        amount = float(record.get('amount', 0)) / 1000000  # Convert from micro-dollars
                        monthly_costs[month] = monthly_costs.get(month, 0) + amount

            # Handle pagination if needed
            page_count = 1
            while data.get('has_more', False) and page_count < 10:
                params['page_token'] = data.get('next_page_token')
                response = requests.get(cost_url, headers=headers, params=params, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    page_count += 1

                    for bucket in data.get('data', []):
                        bucket_date = bucket.get('starting_at', '')
                        if bucket_date:
                            month = datetime.strptime(bucket_date, '%Y-%m-%d').strftime('%b %Y')

                            for record in bucket.get('results', []):
                                amount = float(record.get('amount', 0)) / 1000000
                                monthly_costs[month] = monthly_costs.get(month, 0) + amount
                else:
                    break

    except Exception as e:
        print(f"  ⚠️ Error: {e}")

    return monthly_costs

def generate_expense_csv(anthropic_monthly):
    """Generate CSV with actual and estimated costs."""
    print("\n📝 Generating expense report...")

    # Generate all months
    months = []
    current = date(2024, 6, 1)
    end = date(2025, 9, 30)

    while current <= end:
        label = current.strftime('%b %Y')
        months.append(label)
        current = current + relativedelta(months=1)

    output_path = 'data/ai_expenses_report.csv'

    # Calculate average monthly API cost from recent data
    recent_api_costs = list(anthropic_monthly.values())
    avg_api_cost = sum(recent_api_costs) / len(recent_api_costs) if recent_api_costs else 5000  # Default $5k if no data

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title
        writer.writerow(['AI Platform Monthly Expenses Report'])
        writer.writerow(['Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])

        # Header
        header = ['Cost Category'] + months
        writer.writerow(header)

        # Fixed Costs
        writer.writerow(['FIXED COSTS'])
        writer.writerow(['Cursor Subscription'] + [f'${CURSOR_FIXED:.2f}'] * len(months))
        writer.writerow(['Claude.ai Subscription'] + [f'${CLAUDE_AI_FIXED:.2f}'] * len(months))
        writer.writerow(['Fixed Subtotal'] + [f'${CURSOR_FIXED + CLAUDE_AI_FIXED:.2f}'] * len(months))

        writer.writerow([])

        # Variable Costs
        writer.writerow(['VARIABLE COSTS'])

        # Claude API row with actual data where available
        claude_api_row = ['Claude API']
        for month in months:
            if month in anthropic_monthly:
                # Use actual data
                cost = anthropic_monthly[month]
                claude_api_row.append(f'${cost:,.2f}')
            else:
                # Use estimated average for future/missing months
                month_date = datetime.strptime(f'01 {month}', '%d %b %Y').date()
                if month_date <= date.today():
                    # Past month without data - use average
                    claude_api_row.append(f'${avg_api_cost:,.2f}*')
                else:
                    # Future month - use average projection
                    claude_api_row.append(f'${avg_api_cost:,.2f}**')

        writer.writerow(claude_api_row)

        # Cursor API (minimal for now)
        writer.writerow(['Cursor API (est.)'] + ['$0.00'] * len(months))

        # Variable Subtotal
        variable_row = ['Variable Subtotal']
        for month in months:
            cost = anthropic_monthly.get(month, avg_api_cost)
            variable_row.append(f'${cost:,.2f}')
        writer.writerow(variable_row)

        writer.writerow([])

        # Grand Total
        writer.writerow(['GRAND TOTAL'])
        total_row = ['Monthly Total']
        cumulative = 0
        for month in months:
            api_cost = anthropic_monthly.get(month, avg_api_cost)
            monthly_total = CURSOR_FIXED + CLAUDE_AI_FIXED + api_cost
            total_row.append(f'${monthly_total:,.2f}')
            cumulative += monthly_total
        writer.writerow(total_row)

        # Cumulative
        writer.writerow([])
        writer.writerow(['CUMULATIVE'])
        cumulative_row = ['Running Total']
        running_total = 0
        for month in months:
            api_cost = anthropic_monthly.get(month, avg_api_cost)
            running_total += CURSOR_FIXED + CLAUDE_AI_FIXED + api_cost
            cumulative_row.append(f'${running_total:,.2f}')
        writer.writerow(cumulative_row)

        # Summary
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Fixed (16 months)', f'${(CURSOR_FIXED + CLAUDE_AI_FIXED) * 16:,.2f}'])
        writer.writerow(['Total Claude API (actual)', f'${sum(anthropic_monthly.values()):,.2f}'])
        writer.writerow(['Average Monthly API Cost', f'${avg_api_cost:,.2f}'])
        writer.writerow(['Projected 16-Month Total', f'${cumulative:,.2f}'])

        writer.writerow([])
        writer.writerow(['NOTES:'])
        writer.writerow(['* = Estimated based on average of actual months'])
        writer.writerow(['** = Future projection based on recent average'])
        writer.writerow([f'Actual data available for: {", ".join(anthropic_monthly.keys())}'])

    print(f"✅ Saved to: {output_path}")
    return output_path, cumulative

def main():
    print("\n" + "="*60)
    print("AI EXPENSE REPORT GENERATOR - WITH REAL DATA")
    print("="*60 + "\n")

    # Fetch recent actual costs
    anthropic_costs = fetch_recent_anthropic_data()

    if anthropic_costs:
        print(f"\n✅ Found actual cost data for {len(anthropic_costs)} months:")
        for month, cost in sorted(anthropic_costs.items()):
            print(f"  {month}: ${cost:,.2f}")
    else:
        print("⚠️ No actual cost data found, using estimates")

    # Generate report
    csv_path, total_projected = generate_expense_csv(anthropic_costs)

    print("\n" + "="*60)
    print("REPORT SUMMARY")
    print("="*60)
    print(f"Period: Jun 2024 - Sep 2025 (16 months)")
    print(f"Fixed Monthly: ${CURSOR_FIXED + CLAUDE_AI_FIXED:.2f}")

    if anthropic_costs:
        avg_api = sum(anthropic_costs.values()) / len(anthropic_costs)
        print(f"Average API Cost: ${avg_api:,.2f}/month")

    print(f"Total Projected: ${total_projected:,.2f}")
    print("="*60)

    print(f"\n✅ Done! Open {csv_path} in Excel")
    print("📊 Report contains ACTUAL API costs where available!")

if __name__ == '__main__':
    main()