# Initial Plan: Metabase Chart & Filter Automation

**Feature Name:** Claude-Assisted Chart & Filter Creation System
**Created:** October 19, 2025
**Status:** Initial Planning
**Complexity:** Medium (API Integration + Configuration Management)
**Script Name:** `create_dashboards.py` (enhanced, backward compatible)

---

## 1. Feature Purpose & User Goals

### What Users Should Accomplish

**Primary Goal:** Enable users to create comprehensive Metabase dashboards through natural conversation with Claude:
- User: "Create a line chart showing daily spending trends"
- User: "Add a dropdown filter for providers"
- User: "Show me a pie chart of tool breakdown"
- User: "Add a KPI card for total cost with currency formatting"
- User: "Create a bar chart of top 15 spenders with multi-select user filter"

**Secondary Goals:**
- Support ALL Metabase visualization types (15+ chart types)
- Support ALL filter types (dropdown, multi-select, date range, search box, etc.)
- Maintain backward compatibility with existing dashboard creation workflow
- Enable rapid dashboard prototyping and iteration
- Reduce dashboard creation time from hours to minutes
- Leverage Claude's natural language understanding (no separate parser needed)

### Core User Experience Flow

```
User Request → Claude Understanding → Config Generation → Script Execution → Dashboard
     ↓                  ↓                    ↓                    ↓              ↓
"Add line        Identifies:          chart_config.json    create_dashboards.py   Live
 chart"          chart=line           + filter_config      with generated config  Dashboard
                 sql=05_daily*
                 filters=provider
```

---

## 2. Current State Analysis

### Existing Infrastructure (Strengths)

**✅ Working Components:**
1. **Metabase Integration:**
   - Self-hosted on GCP VM (e2-medium, us-central1)
   - REST API fully operational
   - BigQuery connection established
   - Session authentication working
   - Script: `scripts/metabase/create_dashboards.py`

2. **SQL Query Library:**
   - 14 production SQL files in `sql/dashboard/ai_cost/`
   - Organized naming convention (01_kpi_*, 05_daily_*, etc.)
   - Parameter syntax already established (`{{parameter_name}}`)
   - BigQuery view: `vw_combined_daily_costs` aggregates all data

3. **BigQuery Data Pipeline:**
   - Claude & Cursor data ingestion operational
   - Daily automated updates via Cloud Scheduler
   - Data validation scripts: `scripts/validation/run_validation.py`

4. **Documentation:**
   - Runbooks in `docs/runbooks/metabase-*.md`
   - Architecture docs in `docs/api-reference/metabase-architecture.md`
   - API investigation scripts in `scripts/api_investigation/`

### Critical Limitations (Must Fix)

**❌ Current Problems:**
1. **Chart Type Limitation:**
   - Line 143: `"display": "table"` hardcoded
   - NO support for scalar, line, bar, pie, gauge, combo, area, etc.
   - NO `visualization_settings` configuration
   - ALL dashboards render as data tables

2. **Filter Type Limitation:**
   - Only static parameters: `"date"`, `"number"`, `"text"`
   - NO field filters (`"dimension"` type)
   - NO dropdown filters with dynamic database values
   - NO multi-select capability
   - NO search box autocomplete

3. **No Conversational Interface:**
   - CLI requires exact syntax knowledge
   - Manual configuration only
   - Cannot interpret user intent
   - **Solution:** Claude will interpret requests and generate configurations

4. **Missing Field ID Resolution:**
   - Function exists (line 77: `resolve_field_id`) but never used
   - Field filters need BigQuery field IDs to work
   - No automated column-to-field mapping

---

## 3. Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Conversation Layer                  │
├─────────────────────────────────────────────────────────────┤
│  User: "Create a line chart for daily spending"              │
│  Claude: Understands intent, identifies components           │
│  - Chart type: line                                          │
│  - SQL file: 05_daily_spend_trend.sql                        │
│  - Filters needed: provider (dropdown)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Configuration Generation (Claude)                │
├─────────────────────────────────────────────────────────────┤
│  Chart Config Builder                                        │
│  ├── chart_templates.py (viz settings per chart type)        │
│  ├── filter_templates.py (field filter configurations)       │
│  └── config_validator.py                                     │
│  Claude generates chart_config.json + filter_config.json     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Metabase API Integration Layer                 │
├─────────────────────────────────────────────────────────────┤
│  Enhanced create_dashboards.py (Existing, Enhanced)          │
│  ├── create_card() + display_type + viz_settings             │
│  ├── create_dimension_parameter() (field filters)            │
│  ├── resolve_field_id() (BigQuery metadata)                  │
│  └── parameter_mappings (dashboard filters)                  │
│  Claude executes script with generated configurations        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Metabase REST API                          │
│  POST /api/card, POST /api/dashboard, PUT /api/dashboard/:id │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow for User Request

**Example: "Create a line chart for daily spending with provider filter"**

1. **Claude Understanding:**
   ```
   Chart Type: line (detected from "line chart")
   Data: daily spending (matches 05_daily_spend_trend.sql)
   Filter: provider (field filter, dropdown)
   Additional: show goal line at daily budget
   ```

2. **Configuration Generation (by Claude):**
   ```json
   {
     "chart": {
       "display": "line",
       "sql_file": "05_daily_spend_trend.sql",
       "viz_settings": {
         "graph.dimensions": ["cost_date"],
         "graph.metrics": ["total_cost_usd"],
         "graph.show_goal": true,
         "graph.goal_value": "{{daily_budget_usd}}"
       }
     },
     "filters": [
       {
         "type": "dimension",
         "slug": "provider",
         "table": "vw_combined_daily_costs",
         "column": "provider",
         "widget_type": "category"
       }
     ]
   }
   ```

3. **Script Execution (by Claude):**
   ```bash
   # Claude writes chart_config.json
   # Claude executes:
   python3 create_dashboards.py \
     --sql-dir sql/dashboard/ai_cost \
     --dashboard-name "Daily Spending Analysis" \
     --chart-config chart_config.json \
     --field-filter vw_combined_daily_costs.provider="Provider" \
     --date start_date=2025-10-01 \
     --number daily_budget_usd=793.48
   ```

4. **Metabase API Calls:**
   - Resolve field ID: `GET /api/database/1/metadata`
   - Create card: `POST /api/card` with display + viz_settings
   - Add to dashboard: `PUT /api/dashboard/123` with field filter

---

## 4. Claude-Assisted Workflow

### How Claude Processes User Requests

**User Request → Claude Actions:**

```
Step 1: Understanding
User: "Create a line chart for daily spending with provider dropdown"
Claude:
  - Identifies chart type: line
  - Matches SQL file: 05_daily_spend_trend.sql (contains "daily" + "spend")
  - Identifies filter need: provider (dropdown, field filter)
  - Determines settings: goal line at daily budget

Step 2: Configuration Generation
Claude creates chart_config.json:
  {
    "05_daily_spend_trend": {
      "display": "line",
      "settings": {
        "graph.dimensions": ["cost_date"],
        "graph.metrics": ["total_cost_usd"],
        "graph.show_goal": true,
        "graph.goal_value": "{{daily_budget_usd}}"
      }
    }
  }

Step 3: Script Execution
Claude runs:
  python3 scripts/metabase/create_dashboards.py \
    --sql-dir sql/dashboard/ai_cost \
    --dashboard-name "Daily Spending Trends" \
    --chart-config chart_config.json \
    --field-filter vw_combined_daily_costs.provider="Provider" \
    --date start_date=2025-10-01 \
    --date end_date=2025-10-31 \
    --number daily_budget_usd=793.48

Step 4: Verification
Claude reports dashboard URL and verifies creation succeeded
```

### SQL File Matching Logic

**Claude uses pattern matching to find appropriate SQL files:**

| User Keywords | Matched SQL File | Reasoning |
|---------------|------------------|-----------|
| "total cost", "overall", "KPI total" | `01_kpi_total_cost.sql` | Contains "total" + "cost" |
| "daily spending", "daily trend", "over time" | `05_daily_spend_trend.sql` | Contains "daily" + "spend" |
| "tool breakdown", "provider split" | `06_tool_breakdown.sql` | Contains "tool" |
| "top users", "biggest spenders", "top 15" | `07_top15_spenders.sql` | Contains "top" |
| "by model", "model costs" | `09_cost_by_model.sql` | Contains "model" |

**Ambiguity Handling:**
- If unclear, Claude asks: "Did you mean daily trend (05) or cost per user (03)?"
- Claude can list available SQL files for user to choose
- Claude can create new SQL files if needed

### Filter Column Matching Logic

**Claude knows which columns support dropdown filters:**

| User Filter Request | Table.Column | Widget Type |
|---------------------|-------------|-------------|
| "provider filter" | `vw_combined_daily_costs.provider` | dropdown (3 values: claude_api, claude_code, cursor) |
| "user filter" | `vw_combined_daily_costs.user_email` | search (250+ values) |
| "model filter" | `vw_combined_daily_costs.model` | dropdown (~10 models) |
| "date range" | `vw_combined_daily_costs.cost_date` | date/range |

**Note:** Claude automatically chooses:
- **Dropdown** for <100 distinct values
- **Search box** for >100 distinct values
- **Multi-select** when user says "multiple" or "several"

### Example Conversations

**Example 1: Simple Chart**
```
User: "Show me a pie chart of tool breakdown"

Claude: "I'll create a pie chart using 06_tool_breakdown.sql.
         This will show the cost distribution across claude_api,
         claude_code, and cursor with percentages."

[Generates config, executes script]

Claude: "Dashboard created: http://127.0.0.1:3000/dashboard/5
         The pie chart shows provider breakdown with percentages."
```

**Example 2: Chart with Filters**
```
User: "Create a bar chart of top spenders with a dropdown to filter by provider"

Claude: "I'll create a bar chart using 07_top15_spenders.sql with a
         dropdown filter for providers. The SQL file needs a small update
         to support field filters. Should I update it?"

User: "Yes"

Claude: [Updates SQL file, generates config, executes]
        "Dashboard created with bar chart + provider dropdown filter.
         You can now select claude_api, claude_code, or cursor to filter."
```

**Example 3: Multiple Charts**
```
User: "Create a dashboard with:
       - KPI for total cost
       - Line chart for daily trends
       - Pie chart for tool breakdown"

Claude: "I'll create a dashboard with 3 cards:
         1. Scalar chart from 01_kpi_total_cost.sql
         2. Line chart from 05_daily_spend_trend.sql
         3. Pie chart from 06_tool_breakdown.sql

         All will use the same date range. Proceed?"

User: "Yes"

Claude: [Generates multi-chart config, executes]
```

### Claude's Knowledge Base

**Claude has access to:**
- All chart type templates (chart_templates.py)
- All filter type templates (filter_templates.py)
- Complete list of SQL files in sql/dashboard/ai_cost/
- BigQuery schema (vw_combined_daily_costs columns)
- Metabase API documentation (via Archon RAG)

**Claude can:**
- Generate chart_config.json files
- Generate filter configurations
- Execute create_dashboards.py with correct parameters
- Update SQL files to support field filters
- Validate configurations before execution
- Debug errors and retry with fixes

---

## 5. Why Claude Instead of Custom NLP Parser

### Architecture Decision: Claude as NLP Layer

**Rejected Approach:**
```
❌ Build separate NLP parser (spaCy + pattern matching)
   - 4+ hours development time
   - Maintenance overhead
   - Limited to predefined patterns
   - Can't handle edge cases well
   - Additional dependencies
```

**Chosen Approach:**
```
✅ Leverage Claude's natural language understanding
   - Zero development time for NLP
   - Handles edge cases naturally
   - Understands context and nuance
   - Can ask clarifying questions
   - Already available
```

### Benefits of Claude-Assisted Approach

**1. Superior Understanding:**
- Claude understands synonyms ("spending" = "cost" = "expenses")
- Handles typos and informal language
- Interprets context (knows "daily" implies time series → line chart)
- Understands complex multi-part requests

**2. Flexible Interaction:**
- Can ask clarifying questions when ambiguous
- Can suggest improvements ("Would you like a goal line?")
- Can explain what it's about to do
- Can iterate based on user feedback

**3. No Maintenance Burden:**
- No need to update pattern rules
- No need to train models
- Works out of the box
- Improves with Claude model updates

**4. Faster Implementation:**
- Skip 1 week of NLP development
- Focus on core functionality (charts + filters)
- Simpler architecture
- Fewer dependencies

### What Claude Needs to Succeed

**Required Components:**
1. **chart_templates.py** - Reference for generating viz_settings
2. **filter_templates.py** - Reference for generating field filters
3. **SQL file catalog** - Know what queries exist
4. **BigQuery schema** - Know available columns for filters
5. **Example configurations** - Patterns to follow

**Claude's Workflow:**
```python
# When user says: "Create a line chart for daily spending"

# Step 1: Claude identifies components
chart_type = "line"  # from "line chart"
sql_file = "05_daily_spend_trend.sql"  # from "daily spending"
viz_template = CHART_TEMPLATES["line"]  # loads template

# Step 2: Claude generates config
chart_config = {
    "05_daily_spend_trend": {
        "display": "line",
        "settings": {
            "graph.dimensions": ["cost_date"],
            "graph.metrics": ["total_cost_usd"],
            "graph.show_goal": true
        }
    }
}

# Step 3: Claude writes config file
write_file("chart_config.json", chart_config)

# Step 4: Claude executes script
execute("python3 create_dashboards.py --chart-config chart_config.json ...")
```

---

## 6. Chart Type Implementation

### All Supported Visualization Types

| Chart Type | Display Value | Use Case | Priority | Viz Settings Required |
|------------|---------------|----------|----------|----------------------|
| **scalar** | `"scalar"` | Single KPI number | HIGH | `scalar.field`, `number.format` |
| **line** | `"line"` | Trends over time | HIGH | `graph.dimensions`, `graph.metrics`, `graph.show_goal` |
| **bar** | `"bar"` | Category comparisons | HIGH | `graph.y_axis.auto_range`, `graph.show_values` |
| **pie** | `"pie"` | Proportional breakdown | HIGH | `pie.show_legend`, `pie.show_percentages` |
| **gauge** | `"gauge"` | Progress toward goal | MEDIUM | `gauge.segments`, `gauge.show_goal` |
| **combo** | `"combo"` | Line + Bar hybrid | MEDIUM | `graph.series_settings` (per series) |
| **area** | `"area"` | Cumulative trends | MEDIUM | `stackable.stack_type` |
| **row** | `"row"` | Horizontal bars | LOW | Similar to bar |
| **scatter** | `"scatter"` | Correlation analysis | LOW | `scatter.bubble` |
| **funnel** | `"funnel"` | Conversion steps | LOW | `funnel.dimension`, `funnel.metric` |
| **waterfall** | `"waterfall"` | Sequential changes | LOW | `waterfall.increase_color` |
| **pivot** | `"pivot"` | Multi-dimensional | LOW | `pivot.column`, `pivot.row` |
| **table** | `"table"` | Detailed data grid | ✅ DONE | None (already works) |

### Chart Configuration Templates

**File:** `scripts/metabase/chart_templates.py` (NEW)

**Purpose:** Claude uses these templates to generate chart_config.json files

```python
CHART_TEMPLATES = {
    "scalar": {
        "display": "scalar",
        "viz_settings": {
            "scalar.field": "{{field_name}}",
            "number.compact": False,
            "number.format": "$,.2f"  # Default currency
        }
    },
    "line": {
        "display": "line",
        "viz_settings": {
            "graph.dimensions": ["{{x_axis}}"],
            "graph.metrics": ["{{y_axis}}"],
            "graph.show_goal": False,
            "graph.show_trendline": False,
            "graph.y_axis.auto_range": True
        }
    },
    "bar": {
        "display": "bar",
        "viz_settings": {
            "graph.y_axis.auto_range": True,
            "graph.show_values": True,
            "stackable.stack_type": None  # or "stacked", "normalized"
        }
    },
    "pie": {
        "display": "pie",
        "viz_settings": {
            "pie.show_legend": True,
            "pie.show_percentages": True,
            "pie.percent_visibility": "inside",
            "pie.slice_threshold": 2.5  # Hide slices < 2.5%
        }
    },
    "gauge": {
        "display": "gauge",
        "viz_settings": {
            "gauge.show_goal": True,
            "gauge.segments": [
                {"min": 0, "max": 50, "color": "#84BB4C", "label": "Low"},
                {"min": 50, "max": 80, "color": "#F9CF48", "label": "Medium"},
                {"min": 80, "max": 100, "color": "#ED6E6E", "label": "High"}
            ]
        }
    },
    # ... More templates for combo, area, row, scatter, funnel, waterfall, pivot
}
```

### Chart Type Reference for Claude

**Claude's Internal Understanding:**

When user says:
- "line chart", "trend", "over time" → `line`
- "bar chart", "comparison", "top 15" → `bar`
- "pie chart", "breakdown", "distribution" → `pie`
- "KPI", "total", "single number" → `scalar`
- "gauge", "progress meter" → `gauge`
- "combo chart", "line and bar" → `combo`

Claude uses these mappings to generate appropriate chart_config.json

---

## 5. Filter Type Implementation

### All Supported Filter Types

| Filter Type | Parameter Type | Widget Type | SQL Syntax | Use Case |
|-------------|---------------|-------------|------------|----------|
| **Field Filter - Dropdown** | `"dimension"` | `"category"` or `"string/="` | `WHERE {{filter}}` | Provider, model, category selection |
| **Field Filter - Multi-Select** | `"dimension"` | `"string/="` + multi-select | `WHERE {{filter}}` | Multiple users, multiple providers |
| **Field Filter - Search Box** | `"dimension"` | `"string/="` | `WHERE {{filter}}` | User email search with autocomplete |
| **Field Filter - Date Range** | `"dimension"` | `"date/range"` | `WHERE {{date_range}}` | Start & end date picker |
| **Field Filter - Relative Date** | `"dimension"` | `"date/relative"` | `WHERE {{relative_date}}` | "Last 30 days", "This month" |
| **Field Filter - Number Range** | `"dimension"` | `"number/between"` | `WHERE {{cost_range}}` | Min/max cost threshold |
| **Static Date** | `"date"` | `"date"` | `WHERE date = {{date}}` | Single date picker |
| **Static Number** | `"number"` | `"number"` | `WHERE cost > {{threshold}}` | Numeric input |
| **Static Text** | `"text"` | `"text"` | `WHERE name LIKE {{search}}` | Free text search |

### Field Filter Architecture (Critical Fix)

**Current Problem:** Script creates static parameters, not field filters.

**Solution:** Add dimension parameter creation

**File:** `scripts/metabase/create_dashboards.py` (ENHANCEMENT)

```python
def create_dimension_parameter(
    sess: requests.Session,
    host: str,
    db_id: int,
    slug: str,
    display_name: str,
    table_name: str,
    column_name: str,
    widget_type: str = "category",
    multi_select: bool = False
) -> Dict[str, Any]:
    """
    Create a Field Filter parameter with dropdown/search/date capabilities.

    This is THE KEY difference between static filters and dynamic filters:
    - Static: type="text/date/number" → plain input box
    - Field Filter: type="dimension" → dropdown with DB values
    """

    # CRITICAL: Resolve field ID from BigQuery metadata
    field_id = resolve_field_id(sess, host, db_id, table_name, column_name)

    if not field_id:
        raise ValueError(f"Could not resolve field ID for {table_name}.{column_name}")

    param = {
        "id": f"mb_param_{slug}",
        "name": display_name,
        "slug": slug,
        "type": "dimension",  # ← KEY: Makes it a field filter!
        "widget-type": widget_type,
        "default": None,
        "required": False,

        # ← CRITICAL: Maps to database column
        "dimension": ["field", field_id, {"base-type": "type/Text"}]
    }

    # Enable multi-select for category filters
    if multi_select and widget_type in ["category", "string/="]:
        param["values_source_type"] = "card"
        param["values_source_config"] = {
            "card_id": None,  # null = use connected field values
            "value_field": None
        }

    return param
```

### Filter Configuration Templates

**File:** `scripts/metabase/filter_templates.py` (NEW)

```python
FILTER_TEMPLATES = {
    "dropdown": {
        "type": "dimension",
        "widget_type": "category",
        "multi_select": False,
        "description": "Single-select dropdown with database values"
    },
    "multi_select": {
        "type": "dimension",
        "widget_type": "string/=",
        "multi_select": True,
        "description": "Multi-select dropdown (checkboxes)"
    },
    "search": {
        "type": "dimension",
        "widget_type": "string/=",
        "multi_select": False,
        "description": "Search box with autocomplete"
    },
    "date_range": {
        "type": "dimension",
        "widget_type": "date/range",
        "multi_select": False,
        "description": "Start & end date picker"
    },
    "relative_date": {
        "type": "dimension",
        "widget_type": "date/relative",
        "multi_select": False,
        "description": "Last 7/30 days, this month, etc."
    },
    "number_range": {
        "type": "dimension",
        "widget_type": "number/between",
        "multi_select": False,
        "description": "Min/max numeric range"
    }
}
```

### Filter Type Reference for Claude

**Claude's Internal Understanding:**

When user says:
- "dropdown", "select", "filter by" → `dropdown` (single-select)
- "multi-select", "multiple providers" → `multi_select` (checkboxes)
- "search box", "searchable" → `search` (autocomplete)
- "date range", "from X to Y" → `date_range` (start + end picker)
- "last 30 days", "this month" → `relative_date` (relative picker)

Claude uses these mappings to generate appropriate field filter configurations

---

## 7. SQL File Updates Required

### Field Filter Syntax Change

**CRITICAL:** SQL files must use field filter syntax for dropdown/dynamic filters.

**Current (Static):**
```sql
-- sql/dashboard/ai_cost/06_tool_breakdown.sql
WHERE provider = {{provider}}  -- ❌ Creates text input
```

**Required (Field Filter):**
```sql
-- sql/dashboard/ai_cost/06_tool_breakdown.sql
WHERE {{provider}}  -- ✅ Creates dropdown filter!
```

### SQL Files to Update

**High Priority (Add Field Filters):**
1. `05_daily_spend_trend.sql` → Add `WHERE {{provider}}` for provider dropdown
2. `06_tool_breakdown.sql` → Add `WHERE {{provider}}` for provider dropdown
3. `07_top15_spenders.sql` → Add `WHERE {{provider}} AND {{user_email}}`
4. `09_cost_by_model.sql` → Add `WHERE {{provider}}` for provider dropdown
5. `11_team_attribution_table.sql` → Add `WHERE {{user_email}}` for user search

**SQL Template for New Queries:**
```sql
-- Supports both static parameters AND field filters
SELECT
  cost_date,
  provider,
  user_email,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)  -- Static parameter
  AND cost_date <= CAST({{end_date}} AS DATE)    -- Static parameter
  AND {{provider}}                                -- Field filter (dropdown)
  AND {{user_email}}                              -- Field filter (search)
GROUP BY cost_date, provider, user_email
ORDER BY cost_date DESC, total_cost_usd DESC;
```

---

## 8. Implementation Phases

### Phase 1: Core Chart & Filter Support (Days 1-3)

**Goal:** Enable programmatic creation of all chart types and filter types.

**Tasks:**
1. **Enhance create_dashboards.py (4 hours)**
   - Add `create_dimension_parameter()` function
   - Add `display_type` parameter to `create_card()`
   - Add `viz_settings` parameter to `create_card()`
   - Fix `_build_template_tags()` for dimension types
   - Add `--field-filter` CLI argument
   - Add `--chart-config` CLI argument

2. **Create chart_templates.py (2 hours)**
   - Define viz_settings for all 13 chart types
   - Include configurable parameters (colors, labels, goals)
   - Add template validation

3. **Create filter_templates.py (2 hours)**
   - Define configurations for 6 filter types
   - Include widget-type mappings
   - Add multi-select support

4. **Update SQL files (1 hour)**
   - Convert 5 high-priority SQL files to field filter syntax
   - Test with BigQuery to ensure compatibility
   - Document field filter syntax rules

**Deliverable:** CLI that supports:
```bash
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Enhanced Dashboard" \
  --chart-config chart_config.json \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --field-filter vw_combined_daily_costs.user_email="User Email" \
  --date start_date=2025-10-01 \
  --number daily_budget_usd=793.48
```

**Validation:**
- [ ] Creates scalar charts with currency formatting
- [ ] Creates line charts with goal lines
- [ ] Creates bar charts with value labels
- [ ] Creates pie charts with percentages
- [ ] Creates dropdown filter with database values
- [ ] Creates multi-select filter
- [ ] Creates search box filter with autocomplete
- [ ] All filters properly map to cards

### Phase 2: Chart Configuration System (Days 4-5)

**Goal:** JSON-based configuration for mapping SQL files to chart types.

**Tasks:**
1. **Create chart_config.json schema (1 hour)**
   ```json
   {
     "01_kpi_total_cost": {
       "display": "scalar",
       "settings": {
         "scalar.field": "total_cost_usd",
         "number.format": "$,.2f"
       }
     },
     "05_daily_spend_trend": {
       "display": "line",
       "settings": {
         "graph.dimensions": ["cost_date"],
         "graph.metrics": ["total_cost_usd"],
         "graph.show_goal": true,
         "graph.goal_value": "{{daily_budget_usd}}"
       }
     },
     "06_tool_breakdown": {
       "display": "pie",
       "settings": {
         "pie.show_legend": true,
         "pie.show_percentages": true
       }
     }
   }
   ```

2. **Add config_loader.py (1 hour)**
   - Load and validate chart_config.json
   - Merge with templates from chart_templates.py
   - Handle missing/invalid configurations

3. **Update create_dashboards.py (2 hours)**
   - Integrate config_loader
   - Apply chart type + viz_settings per SQL file
   - Fallback to table if config missing

4. **Create 14 chart configurations (2 hours)**
   - Map all 14 existing SQL files to appropriate chart types
   - Test each visualization type
   - Document configuration format

**Deliverable:**
- `scripts/metabase/chart_config.json` with 14 configurations
- Automatic chart type application based on SQL filename

**Validation:**
- [ ] All 14 SQL files render with correct chart types
- [ ] Scalar charts show formatted numbers
- [ ] Line charts display goal lines
- [ ] Pie charts show percentages
- [ ] Bar charts display value labels

### Phase 3: Claude Integration & Documentation (Days 6-7)

**Goal:** Enable Claude to understand user requests and generate configurations.

**Tasks:**
1. **Create configuration templates (2 hours)**
   - Document chart_config.json format for Claude
   - Document filter_config.json format for Claude
   - Create 10+ example configurations
   - Document SQL file matching patterns

2. **Create Claude usage guide (1 hour)**
   - Document how to request charts from Claude
   - Document how to request filters from Claude
   - Include 20+ example conversations
   - Document common patterns and shortcuts

3. **Test Claude understanding (2 hours)**
   - Test with 30+ different user requests
   - Verify Claude generates correct configurations
   - Test edge cases and ambiguous requests
   - Document any patterns that need clarification

4. **Create validation helpers (1 hour)**
   - Script to validate chart_config.json
   - Script to validate filter_config.json
   - Error messages for common mistakes

**Example User → Claude Interactions:**
```
User: "Create a line chart showing daily spending trends"
Claude: [Generates chart_config.json with display="line"]
Claude: [Executes create_dashboards.py with config]

User: "Add a dropdown filter for providers"
Claude: [Generates field filter config]
Claude: [Executes with --field-filter flag]

User: "Show me a bar chart of top 15 spenders with multi-select user filter"
Claude: [Generates bar chart config + multi-select filter]
Claude: [Executes with both configurations]
```

**Deliverable:**
- Documentation: `docs/claude-dashboard-guide.md`
- Configuration validator: `scripts/metabase/validate_config.py`
- Example configurations: `examples/chart_configs/`

**Validation:**
- [ ] Claude correctly interprets 30+ different requests
- [ ] Generated configurations are valid
- [ ] Scripts execute successfully
- [ ] Dashboards display correctly in Metabase
- [ ] User can iterate and refine dashboards conversationally

**Tasks:**
1. **Add validation & error handling (2 hours)**
   - Validate field IDs exist
   - Check SQL syntax compatibility
   - Verify Metabase connection
   - Handle API errors gracefully

2. **Create comprehensive documentation (2 hours)**
   - Update `docs/runbooks/metabase-dashboard-automation.md`
   - Document chart configuration format
   - Document filter configuration format
   - Include troubleshooting guide

3. **Create examples & templates (1 hour)**
   - 20+ example dashboard configurations
   - Common chart+filter combinations
   - Best practices guide
   - SQL file reference guide

**Deliverable:**
- Complete documentation with 50+ examples
- Validation scripts for configurations
- Error handling in create_dashboards.py

**Validation:**
- [ ] Validation catches configuration errors before API calls
- [ ] Error messages are clear and actionable
- [ ] Documentation covers all features
- [ ] Examples work without modification

---

## 9. File Organization & Structure

### New Files to Create

```
samba-ai-usage-stats/
├── scripts/
│   └── metabase/
│       ├── create_dashboards.py        # ✏️ ENHANCED
│       ├── create_single_card.py       # (existing, unchanged)
│       ├── chart_templates.py          # ✨ NEW - Chart viz settings
│       ├── filter_templates.py         # ✨ NEW - Filter configurations
│       ├── config_loader.py           # ✨ NEW - Config validation
│       ├── validate_config.py         # ✨ NEW - Validate chart/filter configs
│       ├── chart_config.json          # ✨ NEW - Chart type mappings
│       └── filter_config.json         # ✨ NEW - Filter presets
├── examples/
│   └── chart_configs/
│       ├── example_line_chart.json    # ✨ NEW - Example configurations
│       ├── example_pie_chart.json     # ✨ NEW
│       └── example_with_filters.json  # ✨ NEW
├── sql/
│   └── dashboard/
│       └── ai_cost/
│           ├── 01_kpi_total_cost.sql  # ✏️ UPDATE (field filter syntax)
│           ├── 05_daily_spend_trend.sql # ✏️ UPDATE
│           ├── 06_tool_breakdown.sql  # ✏️ UPDATE
│           ├── 07_top15_spenders.sql  # ✏️ UPDATE
│           ├── 09_cost_by_model.sql   # ✏️ UPDATE
│           └── ... (9 more files)
├── docs/
│   └── runbooks/
│       ├── metabase-dashboard-automation.md  # ✏️ UPDATE
│       └── claude-dashboard-guide.md         # ✨ NEW - How to use Claude for dashboards
└── tests/
    └── metabase/
        ├── test_chart_templates.py    # ✨ NEW
        ├── test_filter_templates.py   # ✨ NEW
        ├── test_config_loader.py      # ✨ NEW
        └── test_create_dashboards.py  # ✨ NEW - Integration tests
```

### Configuration File Formats

**chart_config.json:**
```json
{
  "sql_file_stem": {
    "display": "chart_type",
    "settings": {
      "key": "value"
    },
    "description": "What this chart shows"
  }
}
```

**filter_config.json:**
```json
{
  "filter_preset_name": {
    "type": "dimension",
    "table": "vw_combined_daily_costs",
    "column": "provider",
    "widget_type": "category",
    "multi_select": false,
    "display_name": "Provider"
  }
}
```

---

## 10. Technology Stack & Dependencies

### Python Libraries

**Core Dependencies (Existing):**
- `requests` - HTTP client for Metabase API
- `python-dotenv` - Environment variable management
- `pathlib` - File path operations

**New Dependencies:**
```bash
# requirements-metabase.txt
jsonschema>=4.20.0          # JSON configuration validation
pydantic>=2.5.0             # Data validation
```

**Installation:**
```bash
pip install -r requirements-metabase.txt
```

**Note:** No NLP library needed - Claude handles natural language understanding

### Metabase API Endpoints Used

```python
# Existing (Already Used)
POST   /api/session                    # Authentication
GET    /api/database                   # List databases
GET    /api/database/{id}/metadata     # Field IDs
POST   /api/card                       # Create card
POST   /api/dashboard                  # Create dashboard
PUT    /api/dashboard/{id}             # Update dashboard layout

# New (To Be Used)
GET    /api/card/{id}                  # Verify card creation
GET    /api/dashboard/{id}             # Verify dashboard
DELETE /api/card/{id}                  # Cleanup on error
```

### External Resources

**Metabase API Documentation:**
- Official docs: https://www.metabase.com/docs/latest/api
- Visualization settings reference
- Filter widget configuration

**Similar Approaches:**
- Metabot AI: Built-in Metabase NLP (Pro/Enterprise only, we're using free version)
- Our approach: Leverage Claude's language understanding instead of building custom parser

---

## 11. Security & Performance Considerations

### Security

**API Key Management:**
- Metabase credentials stored in `.env` (not committed)
- VM-local environment variables only
- No credentials in code or configuration files

**Input Validation:**
- Validate generated configurations before execution
- Validate field IDs before API calls
- Whitelist allowed SQL files
- Escape special characters in SQL parameters

**Access Control:**
- Script runs with service account permissions only
- Read-only BigQuery access
- Metabase admin credentials required
- No public API exposure

### Performance

**BigQuery Query Optimization:**
- Use `vw_combined_daily_costs` (pre-aggregated view)
- Limit result sets with TOP/LIMIT
- Partition filtering on `cost_date`
- Avoid SELECT * in production

**Metabase Performance:**
- Cache dashboard results (1-hour cache for current data)
- Batch card creation (create all, then update dashboard once)
- Field ID caching (avoid repeated metadata calls)
- Async API calls for large dashboards

**NLP Processing:**
- Load spaCy model once (singleton pattern)
- Cache parsed command patterns
- Timeout for long-running parses (5 seconds max)

### Error Handling

**Graceful Degradation:**
```python
# Example error handling pattern
try:
    field_id = resolve_field_id(sess, host, db_id, table, column)
    if not field_id:
        # Fall back to static parameter
        logger.warning(f"Field ID not found for {table}.{column}, using static filter")
        return create_static_parameter(slug, display_name)
except Exception as e:
    logger.error(f"Field resolution failed: {e}")
    # Continue with best effort
```

**API Error Recovery:**
- Retry failed requests (3 attempts with exponential backoff)
- Clean up partial creations on failure
- Log all API calls for debugging
- Return user-friendly error messages

---

## 12. Testing Strategy

### Unit Tests

**test_chart_templates.py:**
```python
def test_all_chart_types_defined():
    """Ensure all 13 chart types have templates"""
    assert len(CHART_TEMPLATES) == 13
    assert "scalar" in CHART_TEMPLATES
    assert "line" in CHART_TEMPLATES
    # ... etc

def test_visualization_settings_valid():
    """Validate viz_settings structure for each chart"""
    for chart_type, template in CHART_TEMPLATES.items():
        assert "display" in template
        assert "viz_settings" in template
        # Type-specific validations
```

**test_filter_templates.py:**
```python
def test_field_filter_structure():
    """Validate field filter configuration structure"""
    filter_config = create_dimension_parameter(...)
    assert filter_config["type"] == "dimension"
    assert "dimension" in filter_config
    assert isinstance(filter_config["dimension"], list)
    assert len(filter_config["dimension"]) == 3  # ["field", ID, metadata]
```

**test_config_loader.py:**
```python
def test_load_chart_config():
    """Test loading and validating chart configuration"""
    config = load_chart_config("test_config.json")
    assert "01_kpi_total_cost" in config
    assert config["01_kpi_total_cost"]["display"] == "scalar"

def test_validate_chart_config():
    """Test configuration validation"""
    valid_config = {"display": "line", "settings": {...}}
    assert validate_chart_config(valid_config) == True

    invalid_config = {"display": "invalid_type"}
    assert validate_chart_config(invalid_config) == False
```

### Integration Tests

**test_metabase_integration.py:**
```python
def test_create_dashboard_with_all_chart_types():
    """End-to-end test: Create dashboard with all chart types"""
    # Uses test Metabase instance
    dashboard_id = create_test_dashboard()
    # Verify all cards created correctly
    # Verify chart types match configuration
    # Cleanup test dashboard

def test_field_filter_dropdown_creation():
    """Test field filter creates dropdown with database values"""
    # Create field filter for provider column
    # Verify dropdown appears in Metabase UI
    # Verify values match database query results
    # Test filter application
```

### Manual Validation Checklist

**After Each Phase:**
- [ ] Run unit tests: `pytest tests/metabase/`
- [ ] Test with real Metabase instance
- [ ] Verify in Metabase UI (visual inspection)
- [ ] Test all filter widgets interactively
- [ ] Check BigQuery query execution
- [ ] Verify parameter mapping to cards
- [ ] Test error handling (invalid inputs)
- [ ] Performance test (large dashboards)

### Test Data

**Use existing production data:**
- `vw_combined_daily_costs` (already has real data)
- Date range: 2025-10-01 to 2025-10-31
- 3 providers: claude_api, claude_code, cursor
- ~250 unique user_email values

**Test SQL file:**
```sql
-- tests/test_query.sql
SELECT
  cost_date,
  provider,
  COUNT(DISTINCT user_email) as user_count,
  ROUND(SUM(amount_usd), 2) as total_cost
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= '2025-10-01'
  AND cost_date <= '2025-10-31'
  AND {{provider}}
GROUP BY cost_date, provider
ORDER BY cost_date DESC;
```

---

## 13. Success Metrics

### Quantitative Metrics

**Dashboard Creation Speed:**
- Current: ~30 minutes manual creation
- Target: <2 minutes with NLP commands
- Measurement: Time from command to live dashboard

**Chart Type Coverage:**
- Current: 1/13 types (7.7%)
- Target: 13/13 types (100%)
- Measurement: Number of chart types programmatically created

**Filter Type Coverage:**
- Current: 3/9 types (33%)
- Target: 9/9 types (100%)
- Measurement: Number of filter types supported

**Claude Understanding Accuracy:**
- Target: >95% correct intent interpretation
- Measurement: % of user requests that generate correct config

### Qualitative Success Criteria

- [ ] User can create line chart without reading documentation
- [ ] Dropdown filters show actual database values
- [ ] Multi-select filters allow multiple selections
- [ ] Date range filters work with all date columns
- [ ] Chart visualizations display correctly in Metabase
- [ ] Goal lines appear on line charts
- [ ] Pie chart percentages sum to 100%
- [ ] KPI cards format currency correctly
- [ ] Filters apply to all connected cards
- [ ] Error messages are actionable

---

## 14. Risks & Mitigations

### Technical Risks

**Risk 1: Field ID Resolution Failures**
- **Impact:** Dropdown filters won't work
- **Likelihood:** Medium
- **Mitigation:**
  - Extensive testing with BigQuery metadata API
  - Fallback to static parameters if resolution fails
  - Cache field IDs to reduce API calls
  - Add manual field ID override option

**Risk 2: User Request Ambiguity**
- **Impact:** Wrong chart type or filter created
- **Likelihood:** Medium
- **Mitigation:**
  - Claude asks clarifying questions
  - Show generated configuration before execution
  - Allow user to review and modify
  - Learn from user corrections

**Risk 3: Metabase API Rate Limits**
- **Impact:** Slow dashboard creation or API failures
- **Likelihood:** Low
- **Mitigation:**
  - Batch API calls where possible
  - Implement exponential backoff
  - Cache metadata responses
  - Add progress indicators for long operations

**Risk 4: BigQuery Query Incompatibility**
- **Impact:** SQL syntax errors with field filters
- **Likelihood:** Medium
- **Mitigation:**
  - Extensive SQL testing before deployment
  - Update all SQL files systematically
  - Provide SQL syntax migration guide
  - Test with actual BigQuery before Metabase

### Project Risks

**Risk 5: Scope Creep**
- **Impact:** Project takes longer than 1 week
- **Likelihood:** Medium
- **Mitigation:**
  - Focus on 4 primary chart types first (scalar, line, bar, pie)
  - Phase other chart types as Phase 4
  - No separate NLP parser needed (Claude handles it)
  - Time-box each phase to 1-2 days

**Risk 6: Backward Compatibility**
- **Impact:** Existing dashboards break
- **Likelihood:** Low
- **Mitigation:**
  - Maintain default behavior (display="table")
  - Only apply new features with explicit flags
  - Test with existing dashboards
  - Create migration path for old dashboards

---

## 15. Dependencies & Prerequisites

### Infrastructure Prerequisites

**Required (Already Operational):**
- ✅ Metabase VM running at http://127.0.0.1:3000
- ✅ BigQuery database: `ai_usage_analytics`
- ✅ BigQuery view: `vw_combined_daily_costs`
- ✅ Service account with BigQuery read access
- ✅ Metabase admin credentials
- ✅ Python 3.13 environment

**Validation Commands:**
```bash
# Check Metabase connectivity
curl -X POST http://127.0.0.1:3000/api/session \
  -H "Content-Type: application/json" \
  -d '{"username":"$MB_USER","password":"$MB_PASS"}'

# Check BigQuery access
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM ai_usage_analytics.vw_combined_daily_costs"

# Check Python version
python3 --version  # Should be 3.13

# Check existing script
python3 scripts/metabase/create_dashboards.py --help
```

### New Dependencies

**Python Packages:**
```bash
pip install jsonschema>=4.20.0 pydantic>=2.5.0
```

**Metabase Configuration:**
- Admin access to Table Metadata settings
- Field type set to "Category" for dropdown filters
- "Filtering on this field" = "A list of all values"

---

## 16. Next Steps & PRP Generation

### Immediate Next Actions

**1. Review & Approve Initial Plan (You)**
- Confirm scope aligns with expectations
- Approve 2-week timeline
- Confirm all chart types needed
- Confirm all filter types needed

**2. Generate PRP (Next Command)**
```bash
/generate-prp initial-nlp-dashboard-automation.md
```

**3. Begin Phase 1 Implementation**
- Start with `create_dimension_parameter()` function
- Add CLI support for `--field-filter`
- Test with 1 dropdown filter first
- Expand to all filter types

### Post-Implementation Validation

**After Phase 3 Complete:**
```bash
# Full system test - User asks Claude:
"Create a dashboard with:
 - Line chart for daily spending with goal line
 - Pie chart for tool breakdown
 - Bar chart for top 15 spenders
 - Dropdown filter for providers
 - Multi-select filter for users"

# Claude generates configurations and executes:
# 1. Writes chart_config.json
# 2. Executes create_dashboards.py with all configs
# 3. Provides dashboard URL

# Then verify in Metabase UI at http://127.0.0.1:3000
# Test all filter interactions
# Verify all chart types display correctly
```

---

## 17. Open Questions for PRP

**Questions to Address in PRP:**

1. **Chart Type Priority:** Focus on 4 primary types first (scalar, line, bar, pie) or implement all 13 simultaneously?

2. **Configuration Format:** JSON files vs. Python dictionaries vs. YAML?

3. **Error Handling:** Strict validation (fail fast) vs. best-effort fallback?

4. **Multi-Dashboard Support:** Single dashboard per request or support adding to existing dashboards?

5. **Filter Linking:** Should filters be automatically linked across all cards or require explicit mapping?

6. **Goal Line Configuration:** Static values vs. dynamic parameters vs. calculated from data?

7. **SQL File Auto-Update:** Automatic migration vs. manual update with validation?

8. **Testing Scope:** Unit tests only vs. integration tests vs. end-to-end tests?

9. **Claude Workflow:** Should Claude show preview before execution or execute directly?

10. **Configuration Storage:** Generate temporary configs or save for reuse?

---

## 18. Confidence Assessment

### Feature Complexity Score: **6/10** (Medium)

**Complexity Factors:**
- ~~Natural language processing~~ (not needed - Claude handles it)
- Metabase API integration (well-documented but extensive)
- Field filter implementation (critical, high risk)
- Chart configuration system (moderate complexity)
- SQL syntax migration (moderate risk)
- Claude integration (low complexity)

### Completeness Score: **9/10** (Very Complete)

**This initial plan provides:**
- ✅ Clear feature purpose and user goals
- ✅ Comprehensive current state analysis
- ✅ Detailed technical architecture
- ✅ Complete chart type coverage (13 types)
- ✅ Complete filter type coverage (9 types)
- ✅ Phased implementation plan (4 phases)
- ✅ Specific file structure and organization
- ✅ Testing strategy with examples
- ✅ Security and performance considerations
- ✅ Risk analysis with mitigations
- ✅ Technology stack and dependencies
- ✅ Validation commands and success metrics

**Missing (Intentionally Deferred to PRP):**
- Specific code implementations (will be in PRP)
- Detailed API payload examples (will be in PRP)
- Example Claude conversations (will be in PRP)

### Implementation Feasibility Score: **9/10** (Highly Feasible)

**Strong Foundation:**
- Existing working script to enhance (not building from scratch)
- Metabase API well-documented
- BigQuery data already available
- Python environment ready
- Clear extension points identified

**Challenges:**
- Field ID resolution (medium risk, solvable)
- ~~NLP ambiguity~~ (not a concern - Claude handles understanding)
- SQL syntax migration (requires careful testing)
- Claude configuration generation (low risk, well-defined templates)

### PRP Generation Readiness: **10/10** (Fully Ready)

**This document provides everything needed for PRP generation:**
- Complete feature scope and requirements
- Specific file locations and naming conventions
- Integration points with existing systems
- Technology choices and dependencies
- Phased implementation breakdown
- Testing and validation approach
- Success criteria and metrics
- Risk mitigation strategies

---

## 19. Document Metadata

**Creation Date:** October 19, 2025
**Author:** AI Architect (Claude)
**Project:** samba-ai-usage-stats
**Feature:** Metabase Chart & Filter Automation
**Document Type:** Initial Plan (Pre-PRP)
**Document File:** `initial-metabase-chart-automation.md`
**Script File:** `scripts/metabase/create_dashboards.py` (enhanced)
**Next Step:** Generate PRP via `/generate-prp initial-metabase-chart-automation.md`

**Research Sources:**
- Codebase analysis: `scripts/metabase/create_dashboards.py`
- Metabase documentation: `docs/api-reference/metabase-architecture.md`
- Filter investigation report (conducted today)
- Primer analysis report (conducted today)
- Web research: Metabase API, conversational dashboard generation
- BigQuery schema documentation
- Existing SQL file patterns
- Claude capabilities and tool usage patterns

**Validation:**
- [x] Deep codebase analysis completed
- [x] Web research on relevant technologies completed
- [x] Feature goals clearly defined
- [x] Integration strategy aligns with project architecture
- [x] Implementation approach based on existing conventions
- [x] File organization follows discovered patterns
- [x] Security considerations address project requirements
- [x] Testing strategy uses project infrastructure
- [x] All necessary context included for PRP generation

---

## Summary

This initial plan defines a comprehensive Metabase Chart & Filter Automation System that will transform the existing dashboard creation workflow from manual CLI configuration to natural conversation with Claude. The enhanced `create_dashboards.py` script will support:

- **13 chart types** (scalar, line, bar, pie, gauge, combo, area, row, scatter, funnel, waterfall, pivot, table)
- **9 filter types** (dropdown, multi-select, search, date range, relative date, number range, static date/number/text)
- **Conversational interface** - User tells Claude what they want, Claude generates config and executes
- **JSON-based configuration** for systematic chart and filter management
- **Backward compatibility** with existing dashboard creation workflow

The implementation is phased over 1 week (3 phases) with clear deliverables, validation criteria, and success metrics. The architecture leverages existing infrastructure (Metabase API, BigQuery, Python scripts) plus Claude's natural language understanding, eliminating the need for a separate NLP parser.

**Confidence Level: 9/10** - This plan provides a solid, comprehensive foundation for successful PRP generation and implementation.

---

## 20. Key Naming Decisions

### Script Name: `create_dashboards.py` (KEPT UNCHANGED)

**Rationale:**
- ✅ **Backward Compatible:** Existing runbooks reference this name
- ✅ **No Doc Updates:** `docs/runbooks/metabase-dashboard-automation.md` still valid
- ✅ **Enhanced Not Replaced:** Same interface, more capabilities
- ✅ **Familiar to Team:** No retraining needed

**What Changes:**
- Internal functionality enhanced (chart types, field filters)
- New CLI parameters added (`--chart-config`, `--field-filter`)
- Default behavior unchanged (still creates tables if no config)

**Backward Compatibility:**
```bash
# Old command still works exactly the same:
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Old Style Dashboard"
# → Creates tables (as before)

# New command with enhanced features:
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Enhanced Dashboard" \
  --chart-config chart_config.json \
  --field-filter vw_combined_daily_costs.provider="Provider"
# → Creates charts with filters (new capability)
```

### Document Name: `initial-metabase-chart-automation.md` (RENAMED)

**Old:** `initial-nlp-dashboard-automation.md`
**New:** `initial-metabase-chart-automation.md`

**Rationale:**
- ✅ **More Accurate:** Focus is charts + filters, not generic "dashboards"
- ✅ **No NLP Confusion:** Claude handles understanding, not a separate NLP parser
- ✅ **Clearer Scope:** Emphasizes automation of chart/filter creation
- ✅ **Better Alignment:** Matches actual implementation focus

**Future PRP File:**
```
PRPs/cc-prp-plans/prp-metabase-chart-automation.md
```
