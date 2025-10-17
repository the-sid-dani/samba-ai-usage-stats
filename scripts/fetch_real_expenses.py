#!/usr/bin/env python3
"""
Fetch REAL expense data from Anthropic and generate comprehensive report.
"""

import os
import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import csv
from google.cloud import secretmanager

# Fixed costs
CURSOR_FIXED = 50  # $50/month per seat
CLAUDE_AI_FIXED = 40  # $40/month per seat
NUM_SEATS = 1  # Adjust based on actual seats

def get_anthropic_api_key():
    """Get Anthropic API key from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        # Try different secret names
        secret_names = ["anthropic-admin-api-key", "anthropic-api-key"]

        for secret_name in secret_names:
            try:
                name = f"projects/ai-workflows-459123/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                key = response.payload.data.decode("UTF-8")
                if key:
                    print(f"✅ Found API key: {secret_name}")
                    return key
            except:
                continue
    except Exception as e:
        print(f"⚠️ Secret Manager error: {e}")

    return None

def fetch_monthly_costs():
    """Fetch real monthly costs from Anthropic API."""
    print("\n📊 Fetching REAL Anthropic API costs...")

    api_key = get_anthropic_api_key()
    if not api_key:
        print("❌ No API key found")
        return {}

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    # Generate months from Jun 2024 to Sep 2025
    months_data = []
    current = date(2024, 6, 1)
    end_date = date(2025, 9, 30)

    while current <= end_date:
        month_end = current + relativedelta(months=1) - timedelta(days=1)
        month_end = min(month_end, date.today())

        if current <= date.today():
            months_data.append({
                'label': current.strftime('%b %Y'),
                'start': current,
                'end': month_end
            })
        else:
            months_data.append({
                'label': current.strftime('%b %Y'),
                'start': None,
                'end': None
            })

        current = current + relativedelta(months=1)

    monthly_costs = {}

    # Fetch data for each month
    for month in months_data:
        if month['start'] is None:
            # Future month
            monthly_costs[month['label']] = 0
            continue

        # Anthropic API has 31-day limit, so we need to chunk requests
        month_total = 0
        current_start = month['start']

        while current_start <= month['end']:
            chunk_end = min(current_start + timedelta(days=30), month['end'])

            params = {
                "starting_at": current_start.strftime("%Y-%m-%d"),
                "ending_at": chunk_end.strftime("%Y-%m-%d")
            }

            try:
                # Fetch cost data
                cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
                response = requests.get(cost_url, headers=headers, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()

                    # Process all buckets
                    for bucket in data.get('data', []):
                        for record in bucket.get('results', []):
                            # Amount is in micro-dollars
                            amount = float(record.get('amount', 0)) / 1000000
                            month_total += amount

                    # Handle pagination
                    page_count = 1
                    while data.get('has_more', False) and page_count < 5:
                        params['page_token'] = data.get('next_page_token')
                        response = requests.get(cost_url, headers=headers, params=params, timeout=30)

                        if response.status_code == 200:
                            data = response.json()
                            page_count += 1

                            for bucket in data.get('data', []):
                                for record in bucket.get('results', []):
                                    amount = float(record.get('amount', 0)) / 1000000
                                    month_total += amount
                        else:
                            break

                elif response.status_code == 429:
                    print(f"  ⚠️ Rate limited for {month['label']}")
                    break
                else:
                    print(f"  ⚠️ Error {response.status_code} for {month['label']}")
                    break

            except Exception as e:
                print(f"  ⚠️ Exception for {month['label']}: {e}")
                break

            current_start = chunk_end + timedelta(days=1)

        monthly_costs[month['label']] = month_total
        if month_total > 0:
            print(f"  ✅ {month['label']}: ${month_total:,.2f}")

    return monthly_costs, months_data

def generate_comprehensive_csv(monthly_costs, months_data):
    """Generate comprehensive expense CSV."""
    print("\n📝 Generating comprehensive expense report...")

    output_path = 'data/ai_expenses_comprehensive.csv'

    # Calculate actual months with data
    actual_months = [m for m, cost in monthly_costs.items() if cost > 0]
    avg_api_cost = sum([c for c in monthly_costs.values() if c > 0]) / len(actual_months) if actual_months else 0

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title and metadata
        writer.writerow(['AI Platform Usage & Cost Tracking'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])

        # Header row with all months
        header = ['Cost Category'] + [m['label'] for m in months_data]
        writer.writerow(header)

        # FIXED COSTS SECTION
        writer.writerow([])
        writer.writerow(['FIXED COSTS'] + [''] * len(months_data))

        cursor_row = ['Cursor Subscription'] + [f'${CURSOR_FIXED:.2f}'] * len(months_data)
        writer.writerow(cursor_row)

        claude_row = ['Claude.ai Subscription'] + [f'${CLAUDE_AI_FIXED:.2f}'] * len(months_data)
        writer.writerow(claude_row)

        fixed_total = ['Total Fixed Costs'] + [f'${CURSOR_FIXED + CLAUDE_AI_FIXED:.2f}'] * len(months_data)
        writer.writerow(fixed_total)

        # VARIABLE COSTS SECTION
        writer.writerow([])
        writer.writerow(['VARIABLE COSTS (API)'] + [''] * len(months_data))

        # Claude API with actual data
        claude_api_row = ['Claude API - Direct Usage']
        for month in months_data:
            cost = monthly_costs.get(month['label'], 0)
            if cost > 0:
                claude_api_row.append(f'${cost:,.2f}')
            elif month['start'] and month['start'] <= date.today():
                # Past month with no data
                claude_api_row.append('$0.00')
            else:
                # Future month - show estimate if we have historical data
                if avg_api_cost > 0:
                    claude_api_row.append(f'${avg_api_cost:,.2f}*')
                else:
                    claude_api_row.append('TBD')
        writer.writerow(claude_api_row)

        # Cursor API (via Claude) - placeholder for now
        cursor_api_row = ['Claude API - Via Cursor'] + ['$0.00'] * len(months_data)
        writer.writerow(cursor_api_row)

        # Variable total
        variable_total = ['Total Variable Costs']
        for month in months_data:
            cost = monthly_costs.get(month['label'], 0)
            if cost > 0:
                variable_total.append(f'${cost:,.2f}')
            elif month['start'] and month['start'] <= date.today():
                variable_total.append('$0.00')
            else:
                if avg_api_cost > 0:
                    variable_total.append(f'${avg_api_cost:,.2f}*')
                else:
                    variable_total.append('TBD')
        writer.writerow(variable_total)

        # TOTAL MONTHLY COSTS
        writer.writerow([])
        writer.writerow(['TOTAL MONTHLY COSTS'] + [''] * len(months_data))

        grand_total = ['Grand Total']
        for month in months_data:
            fixed = CURSOR_FIXED + CLAUDE_AI_FIXED
            variable = monthly_costs.get(month['label'], avg_api_cost if month['start'] and month['start'] > date.today() else 0)
            total = fixed + variable
            grand_total.append(f'${total:,.2f}')
        writer.writerow(grand_total)

        # COST BREAKDOWN
        writer.writerow([])
        writer.writerow(['COST BREAKDOWN'] + [''] * len(months_data))

        fixed_pct = ['% Fixed']
        variable_pct = ['% Variable']
        for month in months_data:
            fixed = CURSOR_FIXED + CLAUDE_AI_FIXED
            variable = monthly_costs.get(month['label'], avg_api_cost if month['start'] and month['start'] > date.today() else 0)
            total = fixed + variable
            if total > 0:
                fixed_pct.append(f'{(fixed/total)*100:.1f}%')
                variable_pct.append(f'{(variable/total)*100:.1f}%')
            else:
                fixed_pct.append('100%')
                variable_pct.append('0%')
        writer.writerow(fixed_pct)
        writer.writerow(variable_pct)

        # CUMULATIVE COSTS
        writer.writerow([])
        writer.writerow(['CUMULATIVE COSTS'] + [''] * len(months_data))

        ytd_total = ['YTD Total']
        cumulative = 0
        for month in months_data:
            fixed = CURSOR_FIXED + CLAUDE_AI_FIXED
            variable = monthly_costs.get(month['label'], avg_api_cost if month['start'] and month['start'] > date.today() else 0)
            cumulative += fixed + variable
            ytd_total.append(f'${cumulative:,.2f}')
        writer.writerow(ytd_total)

        # NOTES
        writer.writerow([])
        writer.writerow(['NOTES:'])
        writer.writerow(['- Fixed costs: Cursor ($50/mo), Claude.ai ($40/mo)'])
        writer.writerow(['- Variable costs: Claude API usage (actual data from API)'])
        writer.writerow(['- * = Estimated based on historical average'])
        writer.writerow([f'- Actual data available for: {", ".join(actual_months)}'])
        writer.writerow([f'- Average monthly API cost: ${avg_api_cost:,.2f}'])
        writer.writerow([f'- Total fixed costs (16 months): ${(CURSOR_FIXED + CLAUDE_AI_FIXED) * 16:,.2f}'])
        writer.writerow([f'- Total API costs (actual): ${sum([c for c in monthly_costs.values() if c > 0]):,.2f}'])
        writer.writerow([f'- Grand Total (16 months): ${cumulative:,.2f}'])

    print(f"✅ Saved to: {output_path}")

    return output_path, cumulative, avg_api_cost, actual_months

def main():
    print("\n" + "="*70)
    print("AI PLATFORM EXPENSE REPORT - FETCHING REAL DATA")
    print("="*70)

    # Fetch real monthly costs
    monthly_costs, months_data = fetch_monthly_costs()

    # Generate comprehensive report
    csv_path, total_16mo, avg_api, actual_months = generate_comprehensive_csv(monthly_costs, months_data)

    # Print summary
    print("\n" + "="*70)
    print("EXPENSE SUMMARY")
    print("="*70)
    print(f"Period: June 2024 - September 2025 (16 months)")
    print(f"Fixed Monthly Costs: ${CURSOR_FIXED + CLAUDE_AI_FIXED:,.2f}")

    if actual_months:
        print(f"Months with actual API data: {len(actual_months)}")
        print(f"Average Monthly API Cost: ${avg_api:,.2f}")
        print(f"Total API Costs (actual): ${sum([c for c in monthly_costs.values() if c > 0]):,.2f}")
    else:
        print("No actual API cost data found")

    print(f"Projected 16-Month Total: ${total_16mo:,.2f}")
    print("="*70)

    print(f"\n✅ Complete! Open {csv_path} in Excel")
    print("📊 This report contains REAL API cost data where available!")

if __name__ == '__main__':
    main()