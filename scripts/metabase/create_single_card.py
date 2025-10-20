#!/usr/bin/env python3
"""
Create a single test card with Field Filter to validate the approach.
"""
import os, requests, sys
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('MB_HOST', 'http://127.0.0.1:3000')
user = os.getenv('MB_USER')
pwd = os.getenv('MB_PASS')

if not user or not pwd:
    sys.exit("Missing MB_USER or MB_PASS environment variables")

# Login
s = requests.Session()
r = s.post(f"{host}/api/session", json={"username": user, "password": pwd})
r.raise_for_status()
print("✅ Logged in successfully")

# Get database ID
r = s.get(f"{host}/api/database")
r.raise_for_status()
dbs = r.json() if isinstance(r.json(), list) else r.json().get('data', [])
db_id = None
for db in dbs:
    if db.get('engine') == 'bigquery':
        db_id = db['id']
        print(f"✅ Found BigQuery database ID: {db_id}")
        break

if not db_id:
    sys.exit("❌ No BigQuery database found")

# Get metadata to find cost_date field ID
r = s.get(f"{host}/api/database/{db_id}/metadata")
r.raise_for_status()
metadata = r.json()

field_id = None
for table in metadata.get('tables', []):
    if 'vw_combined_daily_costs' in table.get('name', '').lower():
        print(f"✅ Found table: {table['name']}")
        for field in table.get('fields', []):
            if field.get('name') == 'cost_date':
                field_id = field['id']
                print(f"✅ Found cost_date field ID: {field_id}")
                break
        break

if not field_id:
    sys.exit("❌ Could not find cost_date field")

# Create a simple test card
sql = """-- Test Card: Total Cost
SELECT
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
[[WHERE {{cost_date_filter}}]];
"""

payload = {
    "name": "TEST - Total Cost with Field Filter",
    "dataset_query": {
        "type": "native",
        "native": {
            "query": sql,
            "template-tags": {
                "cost_date_filter": {
                    "id": "cost_date_filter_tag",
                    "name": "cost_date_filter",
                    "display-name": "Cost Date Filter",
                    "type": "dimension",
                    "dimension": ["dimension", ["field", field_id, None]],
                    "widget-type": "date/all-options",
                    "default": None
                }
            }
        },
        "database": db_id,
    },
    "display": "scalar",
    "visualization_settings": {},
}

r = s.post(f"{host}/api/card", json=payload)
r.raise_for_status()
card = r.json()
card_id = card['id']

print(f"\n🎉 SUCCESS! Created test card #{card_id}")
print(f"📊 View at: {host}/question/{card_id}")
print(f"\nNext: Open this card in Metabase and verify:")
print(f"  1. Card displays a number (total cost)")
print(f"  2. You can see the 'Cost Date Filter' parameter")
print(f"  3. Changing the date filter updates the result")
