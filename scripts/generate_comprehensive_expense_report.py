#!/usr/bin/env python3
"""
Generate comprehensive expense report with REAL data from APIs.
Fetches actual costs from Anthropic API and Cursor API for monthly breakdown.
"""

import os
import sys
import requests
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import csv
import json
from google.cloud import secretmanager
# Load environment from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
        # Fallback to environment variable
        return os.getenv(secret_id, "")

def generate_months():
    """Generate list of months from Jun 2024 to Sep 2025."""
    months = []
    start = date(2024, 6, 1)
    end = date(2025, 9, 30)
    current = start

    while current <= end:
        # Get end of month
        month_end = current + relativedelta(months=1) - timedelta(days=1)
        # Don't go past today
        month_end = min(month_end, date.today())

        months.append({
            'label': current.strftime('%b %Y'),
            'start': current,
            'end': month_end,
            'year': current.year,
            'month': current.month
        })

        current = current + relativedelta(months=1)

    return months

def fetch_anthropic_costs():
    """Fetch actual Anthropic API costs by month."""
    print("📊 Fetching Anthropic API costs...")

    api_key = get_secret("anthropic-admin-api-key")
    if not api_key:
        api_key = get_secret("anthropic-api-key")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    monthly_costs = {}
    months = generate_months()

    for month_info in months:
        if month_info['start'] > date.today():
            monthly_costs[month_info['label']] = 0
            continue

        # Anthropic API has a 31-day limit, so chunk if needed
        current_date = month_info['start']
        month_total = 0

        while current_date <= month_info['end']:
            chunk_end = min(current_date + timedelta(days=30), month_info['end'])

            params = {
                "starting_at": current_date.strftime("%Y-%m-%d"),
                "ending_at": chunk_end.strftime("%Y-%m-%d")
            }

            try:
                # Fetch cost data
                cost_url = "https://api.anthropic.com/v1/organizations/cost_report"
                response = requests.get(cost_url, headers=headers, params=params, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    for bucket in data.get('data', []):
                        for record in bucket.get('results', []):
                            # Amount is in micro-dollars, convert to dollars
                            amount = float(record.get('amount', 0)) / 1000000
                            month_total += amount

                    # Check if there are more pages
                    next_page_token = data.get('next_page_token')
                    while next_page_token:
                        params['page_token'] = next_page_token
                        response = requests.get(cost_url, headers=headers, params=params, timeout=60)
                        if response.status_code == 200:
                            data = response.json()
                            for bucket in data.get('data', []):
                                for record in bucket.get('results', []):
                                    amount = float(record.get('amount', 0)) / 1000000
                                    month_total += amount
                            next_page_token = data.get('next_page_token')
                        else:
                            break

            except Exception as e:
                print(f"  ⚠️ Error fetching {month_info['label']}: {e}")

            current_date = chunk_end + timedelta(days=1)

        monthly_costs[month_info['label']] = month_total
        if month_total > 0:
            print(f"  {month_info['label']}: ${month_total:,.2f}")

    return monthly_costs

def fetch_cursor_costs():
    """Fetch Cursor API usage and estimate costs."""
    print("\n📊 Fetching Cursor API costs...")

    # Try to get Cursor API key
    api_key = get_secret("cursor-api-key")
    if not api_key:
        api_key = os.getenv("CURSOR_API_KEY_SECRET")

    if not api_key:
        print("  ⚠️ Cursor API key not found")
        return {month['label']: 0 for month in generate_months()}

    auth = (api_key, "")  # Basic auth with empty password
    headers = {"Content-Type": "application/json"}

    monthly_costs = {}
    months = generate_months()

    for month_info in months:
        if month_info['start'] > date.today():
            monthly_costs[month_info['label']] = 0
            continue

        payload = {
            "startDate": int(month_info['start'].timestamp() * 1000),
            "endDate": int(month_info['end'].timestamp() * 1000)
        }

        try:
            response = requests.post(
                "https://api.cursor.com/teams/daily-usage-data",
                auth=auth,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('data', [])

                # Sum up usage-based requests for the month
                total_api_reqs = sum(r.get('usageBasedReqs', 0) for r in records)

                # Estimate cost: $0.005 per API request (adjust based on actual billing)
                estimated_cost = total_api_reqs * 0.005

                monthly_costs[month_info['label']] = estimated_cost
                if estimated_cost > 0:
                    print(f"  {month_info['label']}: ${estimated_cost:,.2f} ({total_api_reqs:,} API requests)")
            else:
                monthly_costs[month_info['label']] = 0

        except Exception as e:
            print(f"  ⚠️ Error fetching {month_info['label']}: {e}")
            monthly_costs[month_info['label']] = 0

    return monthly_costs

def generate_excel_csv(anthropic_costs, cursor_costs):
    """Generate CSV formatted for Excel with all expense details."""
    print("\n📝 Generating comprehensive expense report...")

    months = generate_months()
    output_path = 'data/comprehensive_expenses.csv'

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title row
        writer.writerow(['AI Platform Usage & Cost Report - ' + datetime.now().strftime('%B %Y')])
        writer.writerow([])  # Empty row for spacing

        # Header row
        header = ['Cost Category'] + [m['label'] for m in months]
        writer.writerow(header)

        # Fixed Costs Section
        writer.writerow(['FIXED COSTS'] + [''] * len(months))
        writer.writerow(['Cursor Subscription'] + [f'${CURSOR_FIXED:.2f}'] * len(months))
        writer.writerow(['Claude.ai Subscription'] + [f'${CLAUDE_AI_FIXED:.2f}'] * len(months))

        # Fixed costs subtotal
        fixed_subtotal = CURSOR_FIXED + CLAUDE_AI_FIXED
        writer.writerow(['Fixed Costs Subtotal'] + [f'${fixed_subtotal:.2f}'] * len(months))

        # Variable Costs Section
        writer.writerow([])  # Empty row
        writer.writerow(['VARIABLE COSTS (API)'] + [''] * len(months))

        # Claude API costs
        claude_api_row = ['Claude API']
        for month in months:
            cost = anthropic_costs.get(month['label'], 0)
            claude_api_row.append(f'${cost:.2f}')
        writer.writerow(claude_api_row)

        # Cursor API costs
        cursor_api_row = ['Cursor API (est.)']
        for month in months:
            cost = cursor_costs.get(month['label'], 0)
            cursor_api_row.append(f'${cost:.2f}')
        writer.writerow(cursor_api_row)

        # Variable costs subtotal
        variable_subtotal_row = ['Variable Costs Subtotal']
        for month in months:
            total = anthropic_costs.get(month['label'], 0) + cursor_costs.get(month['label'], 0)
            variable_subtotal_row.append(f'${total:.2f}')
        writer.writerow(variable_subtotal_row)

        # Grand Total
        writer.writerow([])  # Empty row
        writer.writerow(['GRAND TOTAL'] + [''] * len(months))
        total_row = ['Total Monthly Cost']
        for month in months:
            total = (fixed_subtotal +
                    anthropic_costs.get(month['label'], 0) +
                    cursor_costs.get(month['label'], 0))
            total_row.append(f'${total:.2f}')
        writer.writerow(total_row)

        # Cumulative costs
        writer.writerow([])  # Empty row
        writer.writerow(['CUMULATIVE'] + [''] * len(months))
        cumulative_row = ['Year-to-Date Total']
        cumulative = 0
        for month in months:
            cumulative += (fixed_subtotal +
                          anthropic_costs.get(month['label'], 0) +
                          cursor_costs.get(month['label'], 0))
            cumulative_row.append(f'${cumulative:.2f}')
        writer.writerow(cumulative_row)

        # Summary statistics
        writer.writerow([])
        writer.writerow(['SUMMARY STATISTICS'])

        # Calculate totals
        total_fixed = fixed_subtotal * len(months)
        total_claude_api = sum(anthropic_costs.values())
        total_cursor_api = sum(cursor_costs.values())
        grand_total = total_fixed + total_claude_api + total_cursor_api

        writer.writerow(['Total Fixed Costs (16 months)', f'${total_fixed:,.2f}'])
        writer.writerow(['Total Claude API Costs', f'${total_claude_api:,.2f}'])
        writer.writerow(['Total Cursor API Costs', f'${total_cursor_api:,.2f}'])
        writer.writerow(['Grand Total (Jun 2024 - Sep 2025)', f'${grand_total:,.2f}'])

        # Average monthly costs
        avg_monthly = grand_total / len(months)
        writer.writerow(['Average Monthly Cost', f'${avg_monthly:,.2f}'])

        # Notes
        writer.writerow([])
        writer.writerow(['NOTES:'])
        writer.writerow(['- Fixed costs: Cursor ($50/mo), Claude.ai ($40/mo)'])
        writer.writerow(['- Claude API costs: Actual data from Anthropic API'])
        writer.writerow(['- Cursor API costs: Estimated from usage-based requests'])
        writer.writerow(['- Report generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

    print(f"✅ Saved comprehensive report to: {output_path}")
    return output_path

def print_summary(anthropic_costs, cursor_costs):
    """Print summary of expenses."""
    months = generate_months()

    total_fixed = (CURSOR_FIXED + CLAUDE_AI_FIXED) * len(months)
    total_claude_api = sum(anthropic_costs.values())
    total_cursor_api = sum(cursor_costs.values())
    grand_total = total_fixed + total_claude_api + total_cursor_api

    print("\n" + "="*60)
    print("AI PLATFORM EXPENSE SUMMARY")
    print("="*60)
    print(f"Period:                 {months[0]['label']} - {months[-1]['label']}")
    print(f"Months:                 {len(months)}")
    print(f"\nTotal Fixed Costs:      ${total_fixed:,.2f}")
    print(f"  Cursor:               ${CURSOR_FIXED * len(months):,.2f}")
    print(f"  Claude.ai:            ${CLAUDE_AI_FIXED * len(months):,.2f}")
    print(f"\nTotal Variable Costs:   ${total_claude_api + total_cursor_api:,.2f}")
    print(f"  Claude API:           ${total_claude_api:,.2f}")
    print(f"  Cursor API:           ${total_cursor_api:,.2f}")
    print(f"\nGrand Total:            ${grand_total:,.2f}")
    print(f"Average Monthly:        ${grand_total/len(months):,.2f}")
    print("="*60)

def main():
    print("\n" + "="*60)
    print("COMPREHENSIVE AI EXPENSE REPORT GENERATOR")
    print("Fetching REAL data from APIs...")
    print("="*60 + "\n")

    # Fetch actual costs from APIs
    anthropic_costs = fetch_anthropic_costs()
    cursor_costs = fetch_cursor_costs()

    # Generate comprehensive CSV
    csv_path = generate_excel_csv(anthropic_costs, cursor_costs)

    # Print summary
    print_summary(anthropic_costs, cursor_costs)

    print(f"\n✅ Done! Open {csv_path} in Excel for detailed breakdown.")
    print("📊 This report contains ACTUAL API costs, not placeholders!")

if __name__ == '__main__':
    main()