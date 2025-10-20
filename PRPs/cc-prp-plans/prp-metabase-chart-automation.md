# PRP: Metabase Chart & Filter Automation

**Feature**: Claude-Assisted Chart & Filter Creation System
**Created**: 2025-10-19
**Confidence Score**: 9/10
**Estimated Effort**: 5-7 days (1 developer)
**Priority**: HIGH (Enables all dashboard automation capabilities)

---

## 🔖 Quick Reference

**Archon Project ID:**
```
a3404ec0-5492-494f-9685-7a726a31f41e
```

**Task IDs (Execute in Order):**
```
1. 68329a02-a4f9-43b7-8314-d520deeb4f58  # create_dimension_parameter()
2. 3706096e-87cd-4f86-afed-162a3c229539  # display_type + viz_settings
3. 23cbf60b-9b1a-4690-b614-b9e51566aea9  # _build_template_tags() fix
4. 8d04b27b-fd9a-4466-b201-88fc0f5e8638  # CLI arguments
5. aedb70ba-7f26-4ac6-9df0-2676c8f5f86e  # chart_templates.py
6. e5daf4ef-8ef0-4b37-bad2-b17572468644  # filter_templates.py
7. 545e73e7-3965-48d8-915e-ed82bb6b2010  # config_loader.py
8. 95078079-85c5-4a9b-8503-31bdaa2201f3  # SQL migration
9. 4b8a0e9c-0ad0-44e5-a8dd-a2818bfab3f1  # chart_config.json
10. 5bbc1f1a-7976-4d27-8270-995955ce9d85 # test suite
11. daddc260-a8d4-4ea2-8f83-2d466d7e6ebb # Claude guide
```

**Quick Commands:**
```python
# View project
mcp__archon__find_projects(project_id="a3404ec0-5492-494f-9685-7a726a31f41e")

# List all tasks
mcp__archon__find_tasks(project_id="a3404ec0-5492-494f-9685-7a726a31f41e")

# Start first task
mcp__archon__manage_task("update", task_id="68329a02-a4f9-43b7-8314-d520deeb4f58", status="doing")
```

---

## 📋 Context & Problem Statement

### Current State (LIMITED)

The existing `scripts/metabase/create_dashboards.py` script has **critical limitations** preventing full dashboard automation:

**❌ Current Problems:**
1. **Chart Type Hardcoded** - Line 143: `"display": "table"` → ALL charts render as tables
2. **No Visualization Settings** - Line 144: `"visualization_settings": {}` → No formatting, colors, goals, etc.
3. **Static Parameters Only** - Only supports `"date"/"number"/"text"` types → No dropdown filters
4. **No Field Filters** - Can't create `"dimension"` type parameters → No dynamic database values
5. **resolve_field_id() Unused** - Function exists but never called → Can't map to columns

**Result:**
- Can only create data tables
- No KPI cards, line charts, pie charts, bar charts
- No dropdown filters with database values
- No multi-select filters
- Manual configuration required

### Validated Solution

**After Enhancement:**
- ✅ Support 13 chart types (scalar, line, bar, pie, gauge, combo, area, row, scatter, funnel, waterfall, pivot, table)
- ✅ Support 9 filter types (dropdown, multi-select, search, date range, relative date, number range, static)
- ✅ Claude-assisted workflow (user says "create line chart", Claude generates config and executes)
- ✅ JSON-based configuration system
- ✅ Backward compatible (old commands still work)

---

## 🎯 Goals & Success Criteria

### Primary Goals

1. **Complete Chart Type Support** - All 13 Metabase chart types programmatically creatable
2. **Complete Filter Type Support** - All 9 filter types including field filters with dropdowns
3. **Claude Integration** - Natural conversation interface for dashboard creation
4. **Backward Compatibility** - Existing workflows continue to work unchanged

### Success Metrics

| Metric | Current | Target | Validation |
|--------|---------|--------|------------|
| Chart Types Supported | 1/13 (7.7%) | 13/13 (100%) | Create dashboard with all types |
| Filter Types Supported | 3/9 (33%) | 9/9 (100%) | Test each filter widget |
| Dashboard Creation Time | 30 min | <2 min | Stopwatch from request to URL |
| Claude Understanding Accuracy | N/A | >95% | Test 30+ requests |
| Field Filter Dropdowns Working | 0% | 100% | Verify DB values appear |

### Non-Goals

- ❌ Custom NLP parser (Claude handles language understanding)
- ❌ Metabase UI changes (API-only solution)
- ❌ Real-time dashboard updates (batch creation sufficient)
- ❌ Embedding or public dashboards (internal use only)

---

## 🏗️ Architecture Design

### Enhanced System Architecture

```
User Conversation with Claude
         ↓
┌─────────────────────────────────────────────────────────┐
│ Claude interprets request                               │
│ - Chart type: line, bar, pie, scalar, etc.              │
│ - SQL file: matches from ai_cost/ directory             │
│ - Filters: dropdown, multi-select, search, etc.         │
│ - Settings: goal lines, percentages, formatting         │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ Claude generates configurations                         │
│ - chart_config.json (SQL file → chart type mapping)     │
│ - Field filter specifications (table.column pairs)      │
│ - Uses chart_templates.py as reference                  │
│ - Uses filter_templates.py as reference                 │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ Enhanced create_dashboards.py                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ NEW: create_dimension_parameter()                   │ │
│ │ - Resolves BigQuery field IDs                       │ │
│ │ - Creates field filter parameters                   │ │
│ │ - Supports dropdown, multi-select, search           │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ENHANCED: create_card()                             │ │
│ │ - Accepts display_type parameter                    │ │
│ │ - Accepts viz_settings parameter                    │ │
│ │ - Applies chart-specific configuration              │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ENHANCED: _build_template_tags()                    │ │
│ │ - Handles dimension type parameters                 │ │
│ │ - Sets widget-type correctly                        │ │
│ │ - Includes dimension field mapping                  │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ NEW: load_chart_config()                            │ │
│ │ - Loads chart_config.json                           │ │
│ │ - Merges with template defaults                     │ │
│ │ - Validates configuration structure                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ Metabase REST API                                       │
│ POST /api/card → Creates card with chart type           │
│ PUT /api/dashboard/:id → Adds card with field filters   │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. Keep Script Name: `create_dashboards.py`**
- Backward compatible with existing runbooks
- No documentation updates needed
- Enhanced, not replaced

**2. Configuration-Driven Approach**
- `chart_templates.py` - Reference templates for Claude
- `chart_config.json` - Per-dashboard SQL file → chart type mapping
- `filter_templates.py` - Field filter configuration patterns

**3. Claude as NLP Layer**
- No separate parser needed
- Leverages built-in language understanding
- Can ask clarifying questions
- Zero maintenance overhead

---

## 📊 Detailed Implementation Specifications

### Component 1: Field Filter Support (CRITICAL FIX)

**File:** `scripts/metabase/create_dashboards.py`

**NEW FUNCTION: create_dimension_parameter()**

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
    Create a Field Filter parameter for dropdown/search/date widgets.

    This is THE KEY difference:
    - Static param: type="text" → plain input box
    - Field filter: type="dimension" → dropdown with DB values

    Args:
        sess: Metabase session
        host: Metabase URL
        db_id: BigQuery database ID
        slug: Parameter slug (lowercase, no spaces)
        display_name: User-facing name
        table_name: BigQuery table/view name
        column_name: Column to filter on
        widget_type: "category", "string/=", "date/range", etc.
        multi_select: Enable checkboxes for multiple selection

    Returns:
        Dashboard parameter dictionary

    Raises:
        ValueError: If field ID cannot be resolved

    Example:
        >>> create_dimension_parameter(
        ...     sess, host, db_id,
        ...     slug="provider",
        ...     display_name="Provider",
        ...     table_name="vw_combined_daily_costs",
        ...     column_name="provider",
        ...     widget_type="category"
        ... )
        {
            "id": "mb_param_provider",
            "name": "Provider",
            "slug": "provider",
            "type": "dimension",
            "widget-type": "category",
            "dimension": ["field", 12345, {"base-type": "type/Text"}],
            ...
        }
    """

    # CRITICAL: Resolve field ID from BigQuery metadata
    field_id = resolve_field_id(sess, host, db_id, table_name, column_name)

    if not field_id:
        raise ValueError(
            f"Could not resolve field ID for {table_name}.{column_name}. "
            f"Verify table exists in Metabase metadata."
        )

    # Build base parameter structure
    param = {
        "id": f"mb_param_{slug}",
        "name": display_name,
        "slug": slug,
        "type": "dimension",  # ← Makes it a field filter!
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

**NEW FUNCTION: parse_field_filters()**

```python
def parse_field_filters(
    sess: requests.Session,
    host: str,
    db_id: int,
    field_filter_args: List[str]
) -> List[Dict[str, Any]]:
    """
    Parse --field-filter CLI arguments into field filter parameters.

    Args:
        field_filter_args: List of "table.column=Display Name" strings

    Returns:
        List of field filter parameter dictionaries

    Example:
        >>> parse_field_filters(sess, host, db_id, [
        ...     "vw_combined_daily_costs.provider=Provider",
        ...     "vw_combined_daily_costs.user_email=User Email"
        ... ])
        [
            {"type": "dimension", "slug": "provider", ...},
            {"type": "dimension", "slug": "user_email", ...}
        ]
    """
    params = []

    for ff_arg in field_filter_args:
        # Parse format: "table.column=Display Name"
        if "." not in ff_arg or "=" not in ff_arg:
            print(f"Warning: Invalid field filter format '{ff_arg}'. Expected: table.column=Display Name")
            continue

        table_col, display_name = ff_arg.split("=", 1)

        if "." not in table_col:
            print(f"Warning: Missing table name in '{table_col}'. Expected: table.column")
            continue

        table_name, column_name = table_col.split(".", 1)
        slug = column_name.lower().replace(" ", "_")

        # Determine widget type based on column name patterns
        if "email" in column_name.lower():
            widget_type = "string/="  # Search box for emails (many values)
        elif column_name.lower() in ["provider", "model", "category", "status"]:
            widget_type = "category"  # Dropdown for categorical (few values)
        elif "date" in column_name.lower():
            widget_type = "date/range"  # Date range picker
        else:
            widget_type = "category"  # Default to dropdown

        try:
            param = create_dimension_parameter(
                sess, host, db_id,
                slug=slug,
                display_name=display_name.strip(),
                table_name=table_name.strip(),
                column_name=column_name.strip(),
                widget_type=widget_type,
                multi_select=False  # Can be made configurable later
            )
            params.append(param)
        except ValueError as e:
            print(f"Warning: Skipping field filter '{ff_arg}': {e}")
            continue

    return params
```

### Component 2: Chart Type Support

**ENHANCED FUNCTION: create_card()**

```python
def create_card(
    sess: requests.Session,
    host: str,
    db_id: int,
    title: str,
    sql: str,
    param_index: Dict[str, Dict[str, Any]],
    display_type: str = "table",  # ← NEW PARAMETER
    viz_settings: Optional[Dict[str, Any]] = None  # ← NEW PARAMETER
) -> Tuple[int, List[str]]:
    """
    Create a Metabase card (question) with specified chart type.

    ENHANCED from original to support chart types and visualization settings.

    Args:
        display_type: Chart type - "scalar", "line", "bar", "pie", "gauge",
                      "combo", "area", "row", "scatter", "funnel", "waterfall",
                      "pivot", "table"
        viz_settings: Chart-specific visualization settings

    Returns:
        (card_id, list of used parameter slugs)

    Example:
        >>> create_card(
        ...     sess, host, db_id,
        ...     title="Daily Spending Trend",
        ...     sql="SELECT cost_date, SUM(amount) FROM...",
        ...     param_index={},
        ...     display_type="line",
        ...     viz_settings={
        ...         "graph.dimensions": ["cost_date"],
        ...         "graph.metrics": ["sum"],
        ...         "graph.show_goal": True,
        ...         "graph.goal_value": 793.48
        ...     }
        ... )
        (12345, ['start_date', 'end_date'])
    """
    template_tags, used_slugs = _build_template_tags(sql, param_index)

    # Build card payload
    payload = {
        "name": title,
        "dataset_query": {
            "type": "native",
            "native": {
                "query": sql,
                "template-tags": template_tags  # ← Moved here from below
            },
            "database": db_id,
        },
        "display": display_type,  # ← USE PARAMETER (was hardcoded "table")
        "visualization_settings": viz_settings or {},  # ← USE PARAMETER (was empty {})
        "description": title,
    }

    # Create card via API
    r = sess.post(f"{host.rstrip('/')}/api/card", json=payload)
    r.raise_for_status()

    return r.json()["id"], used_slugs
```

**ENHANCED FUNCTION: _build_template_tags()**

```python
def _build_template_tags(sql: str, param_index: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Build template tags for SQL parameters.

    ENHANCED to support dimension type (field filter) parameters.

    Original: Only handled text/date/number static parameters
    Enhanced: Now handles dimension parameters with widget-type and dimension fields
    """
    tags: Dict[str, Dict[str, Any]] = {}
    used: List[str] = []

    for slug, meta in param_index.items():
        # Check if parameter is used in SQL
        if f"{{{{{slug}" in sql:
            used.append(slug)

            # Build base tag config
            tag_config = {
                "id": meta["id"],
                "name": slug,
                "display-name": meta["name"],
                "type": meta.get("type", "text"),
                "default": meta.get("default"),
                "required": False,
            }

            # ENHANCED: Handle dimension type (field filter) parameters
            if meta.get("type") == "dimension":
                # Field filters need widget-type and dimension mapping
                tag_config["widget-type"] = meta.get("widget-type", "category")
                tag_config["dimension"] = meta.get("dimension")

                # Optional: multi-select configuration
                if meta.get("values_source_type"):
                    tag_config["values_source_type"] = meta["values_source_type"]
                    tag_config["values_source_config"] = meta["values_source_config"]
            else:
                # Static parameters: text, date, number
                tag_config["widget-type"] = meta.get("_widget", meta.get("type", "text"))

            tags[slug] = tag_config

    return tags, used
```

### Component 3: Chart Configuration System

**NEW FILE: scripts/metabase/chart_templates.py**

```python
"""
Chart type templates for Metabase visualization_settings.

Claude uses these as reference when generating chart_config.json files.
Each template defines the display type and required visualization settings.
"""

from typing import Dict, Any

CHART_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "scalar": {
        "display": "scalar",
        "description": "Single KPI number (large, formatted)",
        "viz_settings": {
            "scalar.field": None,  # Will be set to first numeric column
            "number.compact": False,
            "number.format": "$,.2f",  # Currency format
            "number.scale": 1
        },
        "use_cases": ["Total cost", "Average daily spend", "User count"]
    },

    "line": {
        "display": "line",
        "description": "Trend over time (time series)",
        "viz_settings": {
            "graph.dimensions": [],  # e.g., ["cost_date"]
            "graph.metrics": [],  # e.g., ["total_cost_usd"]
            "graph.show_goal": False,
            "graph.goal_value": None,
            "graph.goal_label": "Budget",
            "graph.show_trendline": False,
            "graph.y_axis.auto_range": True,
            "graph.y_axis.scale": "linear",
            "graph.x_axis.scale": "timeseries"
        },
        "use_cases": ["Daily spending trends", "User growth", "Cost over time"]
    },

    "bar": {
        "display": "bar",
        "description": "Comparison across categories",
        "viz_settings": {
            "graph.dimensions": [],  # e.g., ["user_email"]
            "graph.metrics": [],  # e.g., ["total_cost_usd"]
            "graph.y_axis.auto_range": True,
            "graph.show_values": True,  # Show values on bars
            "stackable.stack_type": None,  # or "stacked", "normalized"
            "graph.x_axis.axis_enabled": True,
            "graph.x_axis.labels_enabled": True
        },
        "use_cases": ["Top 15 spenders", "Cost by model", "Team rankings"]
    },

    "pie": {
        "display": "pie",
        "description": "Proportional breakdown (parts of whole)",
        "viz_settings": {
            "pie.dimension": None,  # Auto-detected from query
            "pie.metric": None,  # Auto-detected from query
            "pie.show_legend": True,
            "pie.show_percentages": True,
            "pie.percent_visibility": "inside",  # or "legend", "both"
            "pie.slice_threshold": 2.5,  # Hide slices < 2.5%
            "pie.show_total": True
        },
        "use_cases": ["Tool breakdown", "Cost by provider", "Distribution analysis"]
    },

    "gauge": {
        "display": "gauge",
        "description": "Progress toward goal (percentage meter)",
        "viz_settings": {
            "gauge.show_goal": True,
            "gauge.segments": [
                {"min": 0, "max": 50, "color": "#84BB4C", "label": "Low"},
                {"min": 50, "max": 80, "color": "#F9CF48", "label": "Medium"},
                {"min": 80, "max": 100, "color": "#ED6E6E", "label": "High"}
            ]
        },
        "use_cases": ["Budget utilization", "Goal progress", "Capacity usage"]
    },

    "combo": {
        "display": "combo",
        "description": "Line + Bar combination (dual metrics)",
        "viz_settings": {
            "graph.metrics": [],  # Multiple metrics
            "graph.dimensions": [],
            "graph.series_settings": {},  # Per-series: {"metric_name": {"display": "line|bar"}}
            "graph.y_axis.auto_range": True
        },
        "use_cases": ["Cost + volume", "Actual vs budget", "Dual axis charts"]
    },

    "area": {
        "display": "area",
        "description": "Cumulative trend (stacked areas)",
        "viz_settings": {
            "graph.dimensions": [],
            "graph.metrics": [],
            "stackable.stack_type": "stacked",  # or "normalized"
            "graph.show_trendline": False
        },
        "use_cases": ["Cumulative costs", "Stacked provider trends"]
    },

    "row": {
        "display": "row",
        "description": "Horizontal bars (like bar but horizontal)",
        "viz_settings": {
            "graph.dimensions": [],
            "graph.metrics": [],
            "graph.y_axis.auto_range": True,
            "graph.show_values": True
        },
        "use_cases": ["Rankings", "Horizontal comparisons"]
    },

    "scatter": {
        "display": "scatter",
        "description": "Correlation analysis (X-Y plot)",
        "viz_settings": {
            "scatter.bubble": None,  # Optional bubble size column
            "graph.dimensions": [],  # X-axis
            "graph.metrics": []  # Y-axis
        },
        "use_cases": ["Cost vs productivity", "Correlation analysis"]
    },

    "funnel": {
        "display": "funnel",
        "description": "Step-wise conversion (decreasing stages)",
        "viz_settings": {
            "funnel.dimension": None,
            "funnel.metric": None
        },
        "use_cases": ["User adoption funnel", "Conversion stages"]
    },

    "waterfall": {
        "display": "waterfall",
        "description": "Sequential changes (+ and - contributions)",
        "viz_settings": {
            "waterfall.increase_color": "#84BB4C",
            "waterfall.decrease_color": "#ED6E6E",
            "waterfall.total_color": "#509EE3"
        },
        "use_cases": ["Cost breakdown", "Budget variance analysis"]
    },

    "pivot": {
        "display": "pivot",
        "description": "Multi-dimensional table (crosstab)",
        "viz_settings": {
            "pivot.column": None,
            "pivot.row": None,
            "pivot.value": None
        },
        "use_cases": ["Cross-tabulation", "Multi-dimensional analysis"]
    },

    "table": {
        "display": "table",
        "description": "Detailed data grid (default)",
        "viz_settings": {},
        "use_cases": ["Detailed lists", "Alert tables", "Attribution data"]
    }
}


def get_chart_template(chart_type: str) -> Dict[str, Any]:
    """Get chart template by type with fallback to table."""
    return CHART_TEMPLATES.get(chart_type, CHART_TEMPLATES["table"])


def get_available_chart_types() -> List[str]:
    """Return list of all supported chart types."""
    return list(CHART_TEMPLATES.keys())
```

**NEW FILE: scripts/metabase/filter_templates.py**

```python
"""
Filter type templates for Metabase field filters.

Claude uses these as reference when creating field filter configurations.
"""

from typing import Dict, Any

FILTER_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "dropdown": {
        "type": "dimension",
        "widget_type": "category",
        "multi_select": False,
        "description": "Single-select dropdown with database values",
        "use_cases": ["Provider selection", "Model selection", "Category filter"],
        "value_limit": 100,  # Max distinct values for dropdown
        "example": {
            "slug": "provider",
            "table": "vw_combined_daily_costs",
            "column": "provider",
            "display_name": "Provider"
        }
    },

    "multi_select": {
        "type": "dimension",
        "widget_type": "string/=",
        "multi_select": True,
        "description": "Multi-select dropdown with checkboxes",
        "use_cases": ["Multiple providers", "Multiple users", "Multiple teams"],
        "value_limit": 100,
        "example": {
            "slug": "providers",
            "table": "vw_combined_daily_costs",
            "column": "provider",
            "display_name": "Providers (Multiple)"
        }
    },

    "search": {
        "type": "dimension",
        "widget_type": "string/=",
        "multi_select": False,
        "description": "Search box with autocomplete",
        "use_cases": ["User email search", "Name lookup", "ID search"],
        "value_limit": None,  # Works with any number of values
        "example": {
            "slug": "user_email",
            "table": "vw_combined_daily_costs",
            "column": "user_email",
            "display_name": "User Email"
        }
    },

    "date_range": {
        "type": "dimension",
        "widget_type": "date/range",
        "multi_select": False,
        "description": "Start and end date picker",
        "use_cases": ["Date range selection", "Period filtering"],
        "example": {
            "slug": "date_range",
            "table": "vw_combined_daily_costs",
            "column": "cost_date",
            "display_name": "Date Range"
        }
    },

    "relative_date": {
        "type": "dimension",
        "widget_type": "date/relative",
        "multi_select": False,
        "description": "Relative date picker (Last 7 days, This month, etc.)",
        "use_cases": ["Recent data", "Period comparisons"],
        "example": {
            "slug": "relative_period",
            "table": "vw_combined_daily_costs",
            "column": "cost_date",
            "display_name": "Time Period"
        }
    },

    "number_range": {
        "type": "dimension",
        "widget_type": "number/between",
        "multi_select": False,
        "description": "Min/max number range",
        "use_cases": ["Cost range filter", "Threshold filtering"],
        "example": {
            "slug": "cost_range",
            "table": "vw_combined_daily_costs",
            "column": "amount_usd",
            "display_name": "Cost Range"
        }
    }
}


def get_filter_template(filter_type: str) -> Dict[str, Any]:
    """Get filter template by type."""
    return FILTER_TEMPLATES.get(filter_type, FILTER_TEMPLATES["dropdown"])


def recommend_widget_type(column_name: str, distinct_value_count: int = None) -> str:
    """
    Recommend widget type based on column name and cardinality.

    Logic:
    - email columns → search box (typically >100 values)
    - date columns → date/range
    - <100 distinct values → dropdown
    - >100 distinct values → search box
    """
    column_lower = column_name.lower()

    if "email" in column_lower or "id" in column_lower:
        return "string/="  # Search box
    elif "date" in column_lower:
        return "date/range"  # Date range
    elif distinct_value_count and distinct_value_count > 100:
        return "string/="  # Search box
    else:
        return "category"  # Dropdown
```

**NEW FILE: scripts/metabase/config_loader.py**

```python
"""
Configuration loader and validator for chart configurations.

Loads chart_config.json and merges with templates from chart_templates.py.
"""

import json
import pathlib
from typing import Dict, Any, Optional, Tuple
from chart_templates import CHART_TEMPLATES, get_chart_template


def load_chart_config(config_file: str) -> Dict[str, Dict[str, Any]]:
    """
    Load chart configuration from JSON file.

    Args:
        config_file: Path to chart_config.json

    Returns:
        Dictionary mapping SQL file stems to chart configurations

    Example:
        >>> load_chart_config("chart_config.json")
        {
            "01_kpi_total_cost": {
                "display": "scalar",
                "settings": {"scalar.field": "total_cost_usd", ...}
            },
            "05_daily_spend_trend": {
                "display": "line",
                "settings": {"graph.dimensions": ["cost_date"], ...}
            }
        }
    """
    if not pathlib.Path(config_file).exists():
        print(f"Warning: Chart config file '{config_file}' not found. Using defaults.")
        return {}

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Validate structure
        if not isinstance(config, dict):
            print(f"Warning: Invalid config format in '{config_file}'. Using defaults.")
            return {}

        return config
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{config_file}': {e}")
        return {}


def resolve_chart_type_and_settings(
    sql_file_stem: str,
    chart_config: Dict[str, Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Get display type and visualization settings for a SQL file.

    Merges user configuration with template defaults.

    Args:
        sql_file_stem: SQL filename without extension (e.g., "05_daily_spend_trend")
        chart_config: Loaded chart configuration from JSON

    Returns:
        (display_type, viz_settings) tuple

    Example:
        >>> resolve_chart_type_and_settings("05_daily_spend_trend", chart_config)
        ("line", {"graph.dimensions": ["cost_date"], "graph.metrics": ["total_cost_usd"], ...})
    """
    # Get user configuration for this SQL file
    user_config = chart_config.get(sql_file_stem, {})

    # Get display type (default to table if not specified)
    display_type = user_config.get("display", "table")

    # Get template for this chart type
    template = get_chart_template(display_type)

    # Merge user settings with template defaults
    viz_settings = template.get("viz_settings", {}).copy()

    # Override with user-provided settings
    if "settings" in user_config:
        viz_settings.update(user_config["settings"])

    return display_type, viz_settings


def validate_chart_config(config: Dict[str, Any]) -> bool:
    """
    Validate chart configuration structure.

    Returns:
        True if valid, False otherwise
    """
    required_keys = ["display"]

    for key in required_keys:
        if key not in config:
            print(f"Error: Missing required key '{key}' in chart config")
            return False

    # Validate display type
    valid_displays = list(CHART_TEMPLATES.keys())
    if config["display"] not in valid_displays:
        print(f"Error: Invalid display type '{config['display']}'. Must be one of: {valid_displays}")
        return False

    return True
```

### Component 4: CLI Enhancement

**ENHANCED: main() function in create_dashboards.py**

```python
def main():
    load_dotenv(dotenv_path=os.getenv("MB_ENV_FILE", "./.env"), override=False)

    parser = argparse.ArgumentParser(description="Create Metabase dashboard from SQL files.")
    parser.add_argument("--sql-dir", required=True, help="Directory with *.sql files")
    parser.add_argument("--dashboard-name", required=True, help="Dashboard title")

    # Existing arguments
    _env_collection = os.getenv("MB_COLLECTION_ID")
    parser.add_argument("--collection-id", type=int,
                       default=(int(_env_collection) if _env_collection and _env_collection.isdigit() else None))
    parser.add_argument("--db-id", default=os.getenv("MB_DB_ID"))
    parser.add_argument("--db-name", default=os.getenv("MB_DB_NAME"))
    parser.add_argument("--param", action="append", default=[],
                       help="Add dashboard parameter (deprecated, use specific types)")
    parser.add_argument("--date", action="append", default=[],
                       help="Date params as name=value (e.g., start_date=2025-10-01)")
    parser.add_argument("--number", action="append", default=[],
                       help="Number params as name=value (e.g., budget_usd=1000)")
    parser.add_argument("--out", default="dashboards.json")

    # ✨ NEW ARGUMENTS
    parser.add_argument("--chart-config", default=None,
                       help="Path to chart_config.json for chart type mappings")
    parser.add_argument("--field-filter", action="append", default=[],
                       help="Field filter as table.column=Display Name (e.g., vw_combined_daily_costs.provider=Provider)")

    args = parser.parse_args()

    # ... existing login and db resolution code ...

    sess = login(host, user, pwd)
    db_id = resolve_db_id(sess, host, args.db_name, args.db_id)
    sql_files = read_sql_files(args.sql_dir)

    # ✨ Load chart configuration
    chart_config = {}
    if args.chart_config:
        chart_config = load_chart_config(args.chart_config)

    # Build dashboard parameters
    params: List[Dict[str, Any]] = []

    # Add static date/number parameters (existing logic)
    params.extend(parse_date_kv(args.date))
    params.extend(parse_number_kv(args.number))

    # ✨ NEW: Add field filter parameters
    field_filter_params = parse_field_filters(sess, host, db_id, args.field_filter)
    params.extend(field_filter_params)

    # Add legacy params (for backward compatibility)
    for p in args.param:
        slug = p.strip()
        # ... existing param handling ...

    param_index = {p["slug"]: p for p in params}

    # Create dashboard
    dash_id = create_dashboard(sess, host, args.dashboard_name, args.collection_id, params)

    # ✨ ENHANCED: Create cards with chart types
    created = []
    dashcards_payload: List[Dict[str, Any]] = []
    col = 0
    row = 0

    for f in sql_files:
        # ✨ Resolve chart type and viz settings from config
        display_type, viz_settings = resolve_chart_type_and_settings(
            f["file"].stem,
            chart_config
        )

        # ✨ Create card with chart type
        card_id, used_slugs = create_card(
            sess, host, db_id, f["name"], f["sql"], param_index,
            display_type=display_type,  # ← NEW
            viz_settings=viz_settings    # ← NEW
        )

        created.append({
            "card_id": card_id,
            "name": f["name"],
            "file": f["file"],
            "display_type": display_type  # ← Track chart type
        })

        # Build dashboard card layout (existing logic)
        dashcards_payload.append({
            "id": -(len(dashcards_payload) + 1),
            "card_id": card_id,
            "row": row,
            "col": col,
            "size_x": 8,
            "size_y": 6,
            "series": [],
            "visualization_settings": {},  # Can override card settings here if needed
            "parameter_mappings": [
                {
                    "parameter_id": param_index[slug]["id"],
                    "card_id": card_id,
                    "target": ["variable", ["template-tag", slug]],
                }
                for slug in used_slugs
            ],
            "dashboard_tab_id": None,
        })

        # Layout: 3 columns (24-col grid → 8 units each)
        col += 8
        if col >= 24:
            col = 0
            row += 6

    # Update dashboard layout (existing logic)
    update_dashboard_layout(sess, host, dash_id, args.dashboard_name, params,
                           dashcards_payload, args.collection_id)

    # Output result
    result = {
        "dashboard_id": dash_id,
        "dashboard_url": f"{host.rstrip('/')}/dashboard/{dash_id}",
        "database_id": db_id,
        "cards": created,
        "created_at": int(time.time()),
    }

    pathlib.Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Created dashboard: {result['dashboard_url']}")
    print(f"Wrote: {args.out}")
```

### Component 5: SQL File Updates

**PATTERN: Field Filter Syntax**

**❌ OLD (Static Parameter):**
```sql
-- Creates plain text input box
WHERE provider = {{provider}}
```

**✅ NEW (Field Filter):**
```sql
-- Creates dropdown with database values!
WHERE {{provider}}
```

**Example: sql/dashboard/ai_cost/06_tool_breakdown.sql (UPDATED)**

```sql
-- AI Cost Dashboard: Tool Breakdown Pie
SELECT
  provider,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND {{provider}}  -- ← UPDATED: Field filter syntax (no `=` operator)
GROUP BY provider
ORDER BY total_cost_usd DESC;
```

**Example: sql/dashboard/ai_cost/07_top15_spenders.sql (UPDATED)**

```sql
-- AI Cost Dashboard: Top 15 Spenders by User
SELECT
  user_email,
  provider,
  ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND {{provider}}    -- ← Field filter for provider dropdown
  AND {{user_email}}  -- ← Field filter for user search box
GROUP BY user_email, provider
ORDER BY total_cost_usd DESC
LIMIT 15;
```

---

## 🔧 Implementation Tasks (Step-by-Step)

### Task 1: Enhance create_dashboards.py for Field Filters (4 hours)

**Subtasks:**
1. Add `create_dimension_parameter()` function (1 hour)
2. Add `parse_field_filters()` function (30 min)
3. Update `_build_template_tags()` to handle dimension type (1 hour)
4. Update `create_card()` signature with display_type and viz_settings (30 min)
5. Update `main()` to parse --field-filter argument (30 min)
6. Add imports for new modules (15 min)
7. Test field filter creation with provider column (45 min)

**Implementation Order:**
```python
# Step 1: Add create_dimension_parameter() after resolve_field_id()
# Step 2: Add parse_field_filters() after parse_date_kv()
# Step 3: Update _build_template_tags() (lines 105-124)
# Step 4: Update create_card() signature (lines 127-150)
# Step 5: Update main() to add --field-filter arg and parse it
# Step 6: Test execution
```

**Validation:**
```bash
# Test field filter creation
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Test Field Filter" \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31

# Verify: Open Metabase, check that Provider filter shows dropdown with values
```

### Task 2: Create chart_templates.py (2 hours)

**Implementation:**
1. Create new file `scripts/metabase/chart_templates.py`
2. Define CHART_TEMPLATES dictionary with all 13 types (see Component 3)
3. Add get_chart_template() helper function
4. Add get_available_chart_types() helper
5. Document each template with use cases and examples

**Validation:**
```python
# Test in Python REPL
>>> from chart_templates import CHART_TEMPLATES, get_chart_template
>>> assert len(CHART_TEMPLATES) == 13
>>> assert "scalar" in CHART_TEMPLATES
>>> line_template = get_chart_template("line")
>>> assert line_template["display"] == "line"
>>> assert "graph.dimensions" in line_template["viz_settings"]
```

### Task 3: Create filter_templates.py (1.5 hours)

**Implementation:**
1. Create new file `scripts/metabase/filter_templates.py`
2. Define FILTER_TEMPLATES dictionary with all 6 field filter types
3. Add get_filter_template() helper
4. Add recommend_widget_type() helper for auto-selection
5. Document with examples

**Validation:**
```python
# Test in Python REPL
>>> from filter_templates import FILTER_TEMPLATES, recommend_widget_type
>>> assert len(FILTER_TEMPLATES) == 6
>>> assert recommend_widget_type("user_email") == "string/="  # Search box
>>> assert recommend_widget_type("provider") == "category"  # Dropdown
```

### Task 4: Create config_loader.py (1.5 hours)

**Implementation:**
1. Create new file `scripts/metabase/config_loader.py`
2. Implement load_chart_config()
3. Implement resolve_chart_type_and_settings()
4. Implement validate_chart_config()
5. Add error handling for missing/invalid configs

**Validation:**
```python
# Test with sample config
>>> from config_loader import load_chart_config, resolve_chart_type_and_settings
>>> config = load_chart_config("test_config.json")
>>> display, settings = resolve_chart_type_and_settings("05_daily_spend_trend", config)
>>> assert display == "line"
>>> assert "graph.dimensions" in settings
```

### Task 5: Create chart_config.json for All 14 SQL Files (2 hours)

**Implementation:**

Create `scripts/metabase/chart_config.json` with this structure:

```json
{
  "01_kpi_total_cost": {
    "display": "scalar",
    "settings": {
      "scalar.field": "total_cost_usd",
      "number.format": "$,.2f"
    },
    "description": "Q4 Total Cost KPI"
  },
  "02_kpi_daily_average": {
    "display": "scalar",
    "settings": {
      "scalar.field": "avg_daily_cost_usd",
      "number.format": "$,.2f"
    },
    "description": "Average Daily Cost KPI"
  },
  "03_kpi_cost_per_user": {
    "display": "scalar",
    "settings": {
      "scalar.field": "cost_per_user_usd",
      "number.format": "$,.2f"
    },
    "description": "Cost Per User KPI"
  },
  "04_kpi_budget_variance": {
    "display": "scalar",
    "settings": {
      "scalar.field": "variance_pct",
      "number.format": "+,.1f",
      "number.suffix": "%"
    },
    "description": "Budget Variance KPI"
  },
  "05_daily_spend_trend": {
    "display": "line",
    "settings": {
      "graph.dimensions": ["cost_date"],
      "graph.metrics": ["total_cost_usd"],
      "graph.show_goal": true,
      "graph.goal_value": null,
      "graph.goal_label": "Daily Budget",
      "graph.y_axis.auto_range": true,
      "graph.x_axis.scale": "timeseries"
    },
    "description": "Daily Spending Trend with Budget Line"
  },
  "06_tool_breakdown": {
    "display": "pie",
    "settings": {
      "pie.show_legend": true,
      "pie.show_percentages": true,
      "pie.percent_visibility": "inside",
      "pie.slice_threshold": 2.5
    },
    "description": "Provider Cost Distribution"
  },
  "07_top15_spenders": {
    "display": "bar",
    "settings": {
      "graph.dimensions": ["user_email"],
      "graph.metrics": ["total_cost_usd"],
      "graph.y_axis.auto_range": true,
      "graph.show_values": true
    },
    "description": "Top 15 Users by Spend"
  },
  "08_user_distribution_histogram": {
    "display": "bar",
    "settings": {
      "graph.dimensions": ["cost_bucket"],
      "graph.metrics": ["user_count"],
      "graph.y_axis.auto_range": true,
      "graph.show_values": true
    },
    "description": "User Distribution by Cost Range"
  },
  "09_cost_by_model": {
    "display": "bar",
    "settings": {
      "graph.dimensions": ["model"],
      "graph.metrics": ["total_cost_usd"],
      "graph.y_axis.auto_range": true,
      "graph.show_values": true,
      "graph.x_axis.labels_enabled": true
    },
    "description": "Cost Breakdown by AI Model"
  },
  "10_cost_by_token_type": {
    "display": "pie",
    "settings": {
      "pie.show_legend": true,
      "pie.show_percentages": true,
      "pie.percent_visibility": "legend"
    },
    "description": "Cost Distribution by Token Type"
  },
  "11_team_attribution_table": {
    "display": "table",
    "settings": {},
    "description": "Detailed Team Attribution Data"
  },
  "12_alert_budget": {
    "display": "table",
    "settings": {},
    "description": "Budget Alert Table"
  },
  "13_alert_efficiency": {
    "display": "table",
    "settings": {},
    "description": "Efficiency Alert Table"
  },
  "14_alert_utilization": {
    "display": "table",
    "settings": {},
    "description": "Utilization Alert Table"
  }
}
```

**Validation:**
```bash
# Validate JSON syntax
python3 -m json.tool scripts/metabase/chart_config.json > /dev/null && echo "Valid JSON"

# Load in config_loader
python3 -c "from scripts.metabase.config_loader import load_chart_config; print(len(load_chart_config('scripts/metabase/chart_config.json')))"
# Should print: 14
```

### Task 6: Update SQL Files for Field Filters (1.5 hours)

**Files to Update:**
1. `sql/dashboard/ai_cost/05_daily_spend_trend.sql`
2. `sql/dashboard/ai_cost/06_tool_breakdown.sql`
3. `sql/dashboard/ai_cost/07_top15_spenders.sql`
4. `sql/dashboard/ai_cost/09_cost_by_model.sql`
5. `sql/dashboard/ai_cost/11_team_attribution_table.sql`

**For Each File:**
1. Read current SQL
2. Identify WHERE clauses with `{{parameter}}`
3. Update to field filter syntax: `WHERE {{parameter}}`
4. Test SQL in BigQuery first (dry run)
5. Save updated file

**Example Update (06_tool_breakdown.sql):**

```sql
-- BEFORE
SELECT provider, ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
GROUP BY provider ORDER BY total_cost_usd DESC;

-- AFTER (add field filter support)
SELECT provider, ROUND(SUM(amount_usd), 2) AS total_cost_usd
FROM `ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date >= CAST({{start_date}} AS DATE)
  AND cost_date <= CAST({{end_date}} AS DATE)
  AND {{provider}}  -- ← ADDED: Field filter for dropdown
GROUP BY provider ORDER BY total_cost_usd DESC;
```

**Validation:**
```bash
# Test SQL syntax with BigQuery
bq query --dry_run --use_legacy_sql=false < sql/dashboard/ai_cost/06_tool_breakdown.sql

# Expected: Syntax valid (parameter references OK in dry run)
```

### Task 7: Create Test Suite (3 hours)

**Create test files:**

**tests/metabase/test_chart_templates.py:**
```python
import pytest
from scripts.metabase.chart_templates import (
    CHART_TEMPLATES,
    get_chart_template,
    get_available_chart_types
)


def test_all_chart_types_defined():
    """Ensure all 13 chart types have templates."""
    expected_types = [
        "scalar", "line", "bar", "pie", "gauge", "combo",
        "area", "row", "scatter", "funnel", "waterfall", "pivot", "table"
    ]
    assert len(CHART_TEMPLATES) == 13
    for chart_type in expected_types:
        assert chart_type in CHART_TEMPLATES


def test_chart_template_structure():
    """Validate each template has required fields."""
    for chart_type, template in CHART_TEMPLATES.items():
        assert "display" in template
        assert template["display"] == chart_type
        assert "viz_settings" in template
        assert "description" in template
        assert isinstance(template["viz_settings"], dict)


def test_get_chart_template():
    """Test template retrieval with fallback."""
    line_template = get_chart_template("line")
    assert line_template["display"] == "line"

    # Test fallback to table for invalid type
    invalid_template = get_chart_template("nonexistent")
    assert invalid_template["display"] == "table"


def test_get_available_chart_types():
    """Test chart types list."""
    types = get_available_chart_types()
    assert isinstance(types, list)
    assert len(types) == 13
    assert "line" in types
    assert "pie" in types
```

**tests/metabase/test_filter_templates.py:**
```python
import pytest
from scripts.metabase.filter_templates import (
    FILTER_TEMPLATES,
    get_filter_template,
    recommend_widget_type
)


def test_all_filter_types_defined():
    """Ensure all 6 filter types have templates."""
    expected_types = [
        "dropdown", "multi_select", "search",
        "date_range", "relative_date", "number_range"
    ]
    assert len(FILTER_TEMPLATES) == 6
    for filter_type in expected_types:
        assert filter_type in FILTER_TEMPLATES


def test_filter_template_structure():
    """Validate each template has required fields."""
    for filter_type, template in FILTER_TEMPLATES.items():
        assert "type" in template
        assert template["type"] == "dimension"
        assert "widget_type" in template
        assert "multi_select" in template
        assert "description" in template


def test_recommend_widget_type():
    """Test widget type recommendation logic."""
    assert recommend_widget_type("user_email") == "string/="  # Search
    assert recommend_widget_type("provider") == "category"  # Dropdown
    assert recommend_widget_type("cost_date") == "date/range"  # Date

    # Test with cardinality
    assert recommend_widget_type("category", distinct_value_count=50) == "category"
    assert recommend_widget_type("user_id", distinct_value_count=500) == "string/="
```

**tests/metabase/test_config_loader.py:**
```python
import pytest
import json
import tempfile
from pathlib import Path
from scripts.metabase.config_loader import (
    load_chart_config,
    resolve_chart_type_and_settings,
    validate_chart_config
)


def test_load_chart_config():
    """Test loading chart configuration from JSON file."""
    # Create temp config file
    config = {
        "01_kpi_total_cost": {
            "display": "scalar",
            "settings": {"scalar.field": "total_cost_usd"}
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name

    loaded = load_chart_config(temp_path)
    assert "01_kpi_total_cost" in loaded
    assert loaded["01_kpi_total_cost"]["display"] == "scalar"

    Path(temp_path).unlink()


def test_load_chart_config_missing_file():
    """Test fallback when config file doesn't exist."""
    config = load_chart_config("nonexistent.json")
    assert config == {}


def test_resolve_chart_type_and_settings():
    """Test chart type resolution with config merging."""
    config = {
        "05_daily_spend_trend": {
            "display": "line",
            "settings": {
                "graph.show_goal": True,
                "graph.goal_value": 793.48
            }
        }
    }

    display, settings = resolve_chart_type_and_settings("05_daily_spend_trend", config)
    assert display == "line"
    assert "graph.dimensions" in settings  # From template
    assert settings["graph.show_goal"] == True  # From config
    assert settings["graph.goal_value"] == 793.48  # From config


def test_resolve_chart_type_default_fallback():
    """Test fallback to table when SQL file not in config."""
    config = {}
    display, settings = resolve_chart_type_and_settings("unknown_file", config)
    assert display == "table"


def test_validate_chart_config():
    """Test configuration validation."""
    valid_config = {"display": "line", "settings": {}}
    assert validate_chart_config(valid_config) == True

    invalid_config = {"settings": {}}  # Missing display
    assert validate_chart_config(invalid_config) == False

    invalid_display = {"display": "invalid_type"}
    assert validate_chart_config(invalid_display) == False
```

### Task 8: Create Claude Usage Guide (2 hours)

**File:** `docs/claude-dashboard-guide.md`

```markdown
# Claude Dashboard Creation Guide

## Quick Start

Tell Claude what you want, and it will create the dashboard for you:

```
User: "Create a line chart for daily spending trends"
Claude: [Generates config, executes script, provides dashboard URL]
```

## Chart Types

### KPI Cards (Scalar Charts)

**User Request:**
"Create a KPI card for total cost"
"Show me the average daily spend as a big number"

**Claude Creates:**
- Chart type: scalar
- SQL file: 01_kpi_total_cost.sql or 02_kpi_daily_average.sql
- Formatting: Currency ($XX,XXX.XX)

### Line Charts (Trends)

**User Request:**
"Create a line chart for daily spending"
"Show me the cost trend over time with a goal line"

**Claude Creates:**
- Chart type: line
- SQL file: 05_daily_spend_trend.sql
- Optional: Goal line at daily budget

### Pie Charts (Breakdowns)

**User Request:**
"Show me a pie chart of tool breakdown"
"Create a pie chart showing cost distribution by provider"

**Claude Creates:**
- Chart type: pie
- SQL file: 06_tool_breakdown.sql
- Settings: Show percentages, legend

### Bar Charts (Rankings)

**User Request:**
"Create a bar chart of top 15 spenders"
"Show me cost by model as a bar chart"

**Claude Creates:**
- Chart type: bar
- SQL file: 07_top15_spenders.sql or 09_cost_by_model.sql
- Settings: Show values on bars

## Filter Types

### Dropdown Filters

**User Request:**
"Add a dropdown filter for providers"
"Include a provider selection dropdown"

**Claude Creates:**
- Field filter on: vw_combined_daily_costs.provider
- Widget: Dropdown with 3 values (claude_api, claude_code, cursor)
- SQL update: Changes `WHERE provider = {{provider}}` to `WHERE {{provider}}`

### Multi-Select Filters

**User Request:**
"Add a multi-select filter for providers"
"Let users select multiple providers"

**Claude Creates:**
- Field filter with multi_select=True
- Widget: Checkboxes for each provider
- Allows selecting multiple values

### Search Box Filters

**User Request:**
"Add a searchable filter for user emails"
"Include a user search box"

**Claude Creates:**
- Field filter on: vw_combined_daily_costs.user_email
- Widget: Search box with autocomplete
- Best for columns with >100 distinct values

### Date Range Filters

**User Request:**
"Add a date range filter"
"Let users pick start and end dates"

**Claude Creates:**
- Field filter on: vw_combined_daily_costs.cost_date
- Widget: Start date + End date pickers

## Complex Examples

### Multi-Chart Dashboard

**User Request:**
"Create a dashboard with:
 - KPI for total cost
 - Line chart for daily trends with goal line
 - Pie chart for tool breakdown
 - Bar chart for top 15 spenders
 - Dropdown filter for providers"

**Claude Actions:**
1. Generates chart_config.json with 4 chart configurations
2. Creates field filter for provider
3. Executes create_dashboards.py with all configs
4. Provides dashboard URL

### Chart with Multiple Filters

**User Request:**
"Create a bar chart of top spenders with:
 - Dropdown for provider
 - Multi-select for users
 - Date range filter"

**Claude Actions:**
1. Updates 07_top15_spenders.sql with field filter syntax
2. Creates 3 field filters (provider dropdown, user multi-select, date range)
3. Executes script
4. Verifies all filters appear and work

## SQL File Reference

Claude knows about these SQL files:

| File | Best For | Chart Type |
|------|----------|------------|
| 01_kpi_total_cost.sql | Total cost KPI | scalar |
| 02_kpi_daily_average.sql | Daily average KPI | scalar |
| 03_kpi_cost_per_user.sql | Per-user KPI | scalar |
| 04_kpi_budget_variance.sql | Variance KPI | scalar |
| 05_daily_spend_trend.sql | Time trends | line |
| 06_tool_breakdown.sql | Provider split | pie |
| 07_top15_spenders.sql | User rankings | bar |
| 08_user_distribution_histogram.sql | Distribution | bar |
| 09_cost_by_model.sql | Model comparison | bar |
| 10_cost_by_token_type.sql | Token breakdown | pie |
| 11-14_alert_*.sql | Detailed data | table |

## Troubleshooting

**Issue: Filter doesn't show dropdown**
- Check if SQL file uses field filter syntax: `WHERE {{filter}}` not `WHERE col = {{filter}}`
- Verify field filter was added with --field-filter argument
- Check Metabase Table Metadata (Admin settings) - field type should be "Category"

**Issue: Chart displays as table**
- Check if chart_config.json exists and is loaded (--chart-config argument)
- Verify SQL file stem matches config key exactly
- Check config_loader loaded successfully (no JSON errors)

**Issue: Goal line doesn't appear**
- Check if graph.show_goal is true in settings
- Verify graph.goal_value is set (or parameter mapped correctly)
- Ensure chart type is "line" or "combo"
```

### Task 9: Integration Testing (2 hours)

**Test Plan:**

1. **Test Each Chart Type:**
   - Create dashboard with all 13 chart types
   - Verify visual display in Metabase UI
   - Check viz_settings applied correctly

2. **Test Each Filter Type:**
   - Create dashboard with all 6 field filter types
   - Verify dropdown shows database values
   - Test multi-select checkboxes work
   - Verify search box autocomplete works
   - Test date range picker

3. **Test Backward Compatibility:**
   - Run old command without new arguments
   - Verify tables still created
   - Ensure no breaking changes

**Test Script:**
```bash
#!/bin/bash
# tests/metabase/integration_test.sh

set -e

# Test 1: Create dashboard with all chart types
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "All Chart Types Test" \
  --chart-config scripts/metabase/chart_config.json \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31 \
  --number daily_budget_usd=793.48

echo "✅ Test 1 passed: All chart types created"

# Test 2: Create dashboard with field filters
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Field Filters Test" \
  --chart-config scripts/metabase/chart_config.json \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --field-filter vw_combined_daily_costs.user_email="User Email" \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31

echo "✅ Test 2 passed: Field filters created"

# Test 3: Backward compatibility (old command)
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Backward Compatibility Test" \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31

echo "✅ Test 3 passed: Backward compatibility maintained"

echo "🎉 All integration tests passed!"
```

### Task 10: Documentation & Examples (1.5 hours)

**Update:** `docs/runbooks/metabase-dashboard-automation.md`

Add new section:

```markdown
## Enhanced Features (NEW)

### Chart Type Configuration

Create dashboards with all chart types using `--chart-config`:

```bash
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Enhanced Dashboard" \
  --chart-config scripts/metabase/chart_config.json \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31
```

This applies chart types and visualization settings from chart_config.json.

### Field Filter Configuration

Add dropdown/search filters with `--field-filter`:

```bash
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Dashboard with Filters" \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --field-filter vw_combined_daily_costs.user_email="User Email" \
  --date start_date=2025-10-01
```

### Combined Usage

Use both chart config and field filters together:

```bash
python3 scripts/metabase/create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Complete Dashboard" \
  --chart-config scripts/metabase/chart_config.json \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31 \
  --number daily_budget_usd=793.48
```
```

**Create:** `examples/chart_configs/`

```
examples/chart_configs/
├── example_line_chart.json
├── example_pie_chart.json
├── example_multi_chart.json
├── example_with_filters.json
└── README.md
```

---

## 📝 Validation Gates

### Pre-Implementation Checks

```bash
# 1. Verify Metabase connectivity
curl -X POST http://127.0.0.1:3000/api/session \
  -H "Content-Type: application/json" \
  -d '{"username":"'"$MB_USER"'","password":"'"$MB_PASS"'"}' 2>&1 | grep -q '"id"' \
  && echo "✅ Metabase connection OK" || echo "❌ Metabase connection failed"

# 2. Verify BigQuery access
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM ai_usage_analytics.vw_combined_daily_costs" \
  && echo "✅ BigQuery access OK" || echo "❌ BigQuery access failed"

# 3. Check Python environment
python3 --version | grep "3.13" && echo "✅ Python 3.13 OK"

# 4. Verify existing script works
python3 scripts/metabase/create_dashboards.py --help | grep -q "sql-dir" \
  && echo "✅ Existing script OK"
```

### Post-Implementation Validation

```bash
# After each task, run these checks:

# 1. Unit tests
python -m pytest tests/metabase/test_chart_templates.py -v
python -m pytest tests/metabase/test_filter_templates.py -v
python -m pytest tests/metabase/test_config_loader.py -v

# 2. Integration test
bash tests/metabase/integration_test.sh

# 3. Manual verification
# - Open Metabase at http://127.0.0.1:3000
# - Navigate to created dashboard
# - Verify chart types display correctly
# - Test filter widgets (dropdown, multi-select, search)
# - Verify filters apply to charts

# 4. SQL validation
for sql_file in sql/dashboard/ai_cost/*.sql; do
  echo "Validating $sql_file"
  bq query --dry_run --use_legacy_sql=false < "$sql_file" || echo "❌ Failed: $sql_file"
done
```

### Final Acceptance Criteria

**ALL must pass:**
- [ ] All 13 chart types render correctly in Metabase
- [ ] Scalar charts show currency formatting ($X,XXX.XX)
- [ ] Line charts display goal lines when configured
- [ ] Pie charts show percentages inside slices
- [ ] Bar charts show values on bars
- [ ] Field filters show dropdown with database values
- [ ] Multi-select filters show checkboxes
- [ ] Search box filters show autocomplete
- [ ] Date range filters show start/end pickers
- [ ] Old commands still work (backward compatibility)
- [ ] All SQL files execute without errors
- [ ] Unit tests pass (100% success rate)
- [ ] Integration tests pass
- [ ] Dashboard creation completes in <2 minutes
- [ ] Claude can interpret 95%+ of user requests correctly

---

## 🔗 External Resources & Documentation

### Metabase API Documentation

**Primary Resources:**
- **Official API Docs**: https://www.metabase.com/docs/latest/api
- **API Reference**: https://www.metabase.com/learn/metabase-basics/administration/administration-and-operation/metabase-api
- **Visualization Overview**: https://www.metabase.com/docs/latest/questions/visualizations/visualizing-results
- **Dashboard Filters**: https://www.metabase.com/docs/latest/dashboards/filters
- **Field Filters Tutorial**: https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/sql-in-metabase/field-filters
- **SQL Parameters**: https://www.metabase.com/docs/latest/questions/native-editor/sql-parameters

**Visualization-Specific Docs:**
- **Line/Bar/Area Charts**: https://www.metabase.com/docs/latest/questions/visualizations/line-bar-and-area-charts
- **Pie Charts**: https://www.metabase.com/docs/latest/questions/visualizations/pie-or-donut-chart
- **Gauge Charts**: https://www.metabase.com/docs/latest/questions/visualizations/gauge
- **Combo Charts**: https://www.metabase.com/docs/latest/questions/visualizations/combo-chart

### Community Resources

**GitHub Examples:**
- **Metabase Python API Wrapper**: https://github.com/vvaezian/metabase_api_python
- **API Usage Discussions**: https://discourse.metabase.com/t/how-to-use-visualization-settings-to-create-new-graph-via-api/11740

### Project-Specific Documentation

**Internal Docs:**
- `docs/api-reference/metabase-architecture.md` - Architecture overview
- `docs/runbooks/metabase-dashboard-automation.md` - Current automation guide
- `docs/BIGQUERY_SCHEMA_WITH_REAL_DATA.md` - Available data for charts

**Existing Scripts:**
- `scripts/metabase/create_dashboards.py` - Script to enhance
- `scripts/metabase/create_single_card.py` - Single card creation pattern

---

## 🎯 Archon Task Tracking

**Archon Project:**
- **Project ID**: `a3404ec0-5492-494f-9685-7a726a31f41e`
- **Project Name**: Metabase Chart & Filter Automation
- **GitHub Repo**: https://github.com/the-sid-dani/samba-ai-usage-stats

### Implementation Tasks (11 total)

**Execute in this order (by priority):**

**Phase 1: Core Field Filter & Chart Support**

1. **Add create_dimension_parameter() function** (HIGHEST PRIORITY)
   - **Task ID**: `68329a02-a4f9-43b7-8314-d520deeb4f58`
   - **Feature**: core-implementation
   - **Task Order**: 110
   - **Description**: Create field filter parameters with dropdown/search capabilities

2. **Add display_type and viz_settings to create_card()**
   - **Task ID**: `3706096e-87cd-4f86-afed-162a3c229539`
   - **Feature**: core-implementation
   - **Task Order**: 104
   - **Description**: Enable chart type specification and visualization settings

3. **Fix _build_template_tags() for dimension parameters**
   - **Task ID**: `23cbf60b-9b1a-4690-b614-b9e51566aea9`
   - **Feature**: core-implementation
   - **Task Order**: 98
   - **Description**: Handle field filter template tags with dimension type

4. **Add --field-filter and --chart-config CLI arguments**
   - **Task ID**: `8d04b27b-fd9a-4466-b201-88fc0f5e8638`
   - **Feature**: core-implementation
   - **Task Order**: 92
   - **Description**: CLI interface for field filters and chart configurations

**Phase 2: Configuration System**

5. **Create chart_templates.py**
   - **Task ID**: `aedb70ba-7f26-4ac6-9df0-2676c8f5f86e`
   - **Feature**: configuration-system
   - **Task Order**: 86
   - **Description**: Define visualization_settings templates for all 13 chart types

6. **Create filter_templates.py**
   - **Task ID**: `e5daf4ef-8ef0-4b37-bad2-b17572468644`
   - **Feature**: configuration-system
   - **Task Order**: 80
   - **Description**: Define field filter configurations for all 9 filter types

7. **Create config_loader.py**
   - **Task ID**: `545e73e7-3965-48d8-915e-ed82bb6b2010`
   - **Feature**: configuration-system
   - **Task Order**: 74
   - **Description**: Configuration loading, validation, and merging

**Phase 3: SQL Migration & Configuration**

8. **Update SQL files to field filter syntax**
   - **Task ID**: `95078079-85c5-4a9b-8503-31bdaa2201f3`
   - **Feature**: sql-migration
   - **Task Order**: 68
   - **Description**: Update 5 SQL files to use WHERE {{filter}} syntax

9. **Create chart_config.json for all 14 SQL files**
   - **Task ID**: `4b8a0e9c-0ad0-44e5-a8dd-a2818bfab3f1`
   - **Feature**: configuration-system
   - **Task Order**: 62
   - **Description**: Map each SQL file to appropriate chart type

**Phase 4: Testing & Documentation**

10. **Create comprehensive test suite**
    - **Task ID**: `5bbc1f1a-7976-4d27-8270-995955ce9d85`
    - **Feature**: testing
    - **Task Order**: 56
    - **Description**: Unit and integration tests for all components

11. **Create Claude usage guide**
    - **Task ID**: `daddc260-a8d4-4ea2-8f83-2d466d7e6ebb`
    - **Feature**: documentation
    - **Task Order**: 50
    - **Description**: Complete guide with 20+ example conversations

### Quick Task Management Commands

**View All Tasks:**
```python
mcp__archon__find_tasks(project_id="a3404ec0-5492-494f-9685-7a726a31f41e")
```

**Start Task 1 (create_dimension_parameter):**
```python
mcp__archon__manage_task(
    "update",
    task_id="68329a02-a4f9-43b7-8314-d520deeb4f58",
    status="doing"
)
```

**Complete Task 1:**
```python
mcp__archon__manage_task(
    "update",
    task_id="68329a02-a4f9-43b7-8314-d520deeb4f58",
    status="done"
)
```

**Start Next Task (display_type/viz_settings):**
```python
mcp__archon__manage_task(
    "update",
    task_id="3706096e-87cd-4f86-afed-162a3c229539",
    status="doing"
)
```

---

## 🚀 Implementation Sequence

### Week 1: Core Implementation

**Day 1-2: Field Filter Support**
1. Add `create_dimension_parameter()` to create_dashboards.py
2. Add `parse_field_filters()` function
3. Update `_build_template_tags()` for dimension support
4. Add --field-filter CLI argument
5. Test with provider dropdown filter

**Day 3: Chart Type Support**
6. Update `create_card()` with display_type and viz_settings
7. Add --chart-config CLI argument
8. Create chart_templates.py
9. Create config_loader.py
10. Test with line chart

**Day 4-5: Configuration System**
11. Create filter_templates.py
12. Create chart_config.json for all 14 SQL files
13. Integrate config_loader into main()
14. Test all 13 chart types

**Day 6: SQL Migration**
15. Update 5 SQL files to field filter syntax
16. Validate SQL with BigQuery dry run
17. Test field filters end-to-end

**Day 7: Testing & Documentation**
18. Create complete test suite
19. Run integration tests
20. Create Claude usage guide
21. Update runbook documentation

### Execution Checklist

- [ ] **Task 1-3**: Field filter functions added and tested
- [ ] **Task 4**: CLI arguments working
- [ ] **Task 5**: chart_templates.py created
- [ ] **Task 6**: filter_templates.py created
- [ ] **Task 7**: config_loader.py created
- [ ] **Task 8**: SQL files updated
- [ ] **Task 9**: chart_config.json created
- [ ] **Task 10**: Test suite complete
- [ ] **Task 11**: Documentation complete
- [ ] **Final**: All validation gates pass

---

## ⚠️ Common Pitfalls & Solutions

### Pitfall 1: Field Filter SQL Syntax Errors

**Problem:** Using `WHERE col = {{filter}}` with field filters
**Solution:** Use `WHERE {{filter}}` (field filters inject the WHERE clause)

**Example:**
```sql
-- ❌ WRONG
WHERE provider = {{provider}}

-- ✅ CORRECT
WHERE {{provider}}
```

### Pitfall 2: Field ID Resolution Failures

**Problem:** `resolve_field_id()` returns None
**Causes:**
- Table not synced in Metabase metadata
- Column name mismatch (case-sensitive)
- BigQuery permission issues

**Solution:**
```python
# Add fallback to static parameter
field_id = resolve_field_id(sess, host, db_id, table, column)
if not field_id:
    logger.warning(f"Field ID not found, falling back to static parameter")
    return create_static_text_parameter(slug, display_name)
```

### Pitfall 3: Dropdown Doesn't Show Values

**Problem:** Dropdown filter appears but is empty
**Causes:**
- Field type not set to "Category" in Table Metadata
- Column has >1,000 distinct values (Metabase limit)
- Values contain >100kB total text

**Solution:**
- Set field type in Metabase: Admin > Table Metadata > Set field to "Category"
- For >1,000 values, use search box instead of dropdown
- Check column cardinality first:
  ```sql
  SELECT COUNT(DISTINCT provider) FROM vw_combined_daily_costs;
  ```

### Pitfall 4: Chart Displays Wrong Columns

**Problem:** Graph shows wrong data on axes
**Causes:**
- `graph.dimensions` / `graph.metrics` not set
- Column names don't match SQL result

**Solution:**
```python
# Auto-detect from SQL query results
# Or explicitly set in chart_config.json:
{
  "05_daily_spend_trend": {
    "display": "line",
    "settings": {
      "graph.dimensions": ["cost_date"],  # ← Must match SELECT clause
      "graph.metrics": ["total_cost_usd"]  # ← Must match SELECT clause
    }
  }
}
```

### Pitfall 5: Goal Line Doesn't Appear

**Problem:** Goal line configured but not visible
**Causes:**
- `graph.show_goal` is false
- `graph.goal_value` is null or not set
- Chart type isn't "line" or "combo"

**Solution:**
```python
# In chart_config.json
{
  "05_daily_spend_trend": {
    "display": "line",
    "settings": {
      "graph.show_goal": true,  # ← Must be true
      "graph.goal_value": 793.48,  # ← Must be numeric (or {{parameter}})
      "graph.goal_label": "Daily Budget"
    }
  }
}
```

---

## 🎨 Example Configurations

### Example 1: Simple Scalar KPI

**chart_config.json:**
```json
{
  "01_kpi_total_cost": {
    "display": "scalar",
    "settings": {
      "scalar.field": "total_cost_usd",
      "number.format": "$,.2f"
    }
  }
}
```

**Execution:**
```bash
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Total Cost KPI" \
  --chart-config chart_config.json \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31
```

**Result:** Big number showing "$45,234.67"

### Example 2: Line Chart with Goal Line

**chart_config.json:**
```json
{
  "05_daily_spend_trend": {
    "display": "line",
    "settings": {
      "graph.dimensions": ["cost_date"],
      "graph.metrics": ["total_cost_usd"],
      "graph.show_goal": true,
      "graph.goal_value": 793.48,
      "graph.goal_label": "Daily Budget"
    }
  }
}
```

**Result:** Line chart with horizontal goal line at $793.48

### Example 3: Pie Chart with Percentages

**chart_config.json:**
```json
{
  "06_tool_breakdown": {
    "display": "pie",
    "settings": {
      "pie.show_legend": true,
      "pie.show_percentages": true,
      "pie.percent_visibility": "inside"
    }
  }
}
```

**Result:** Pie chart with percentages inside each slice

### Example 4: Dashboard with All Features

**chart_config.json:**
```json
{
  "01_kpi_total_cost": {"display": "scalar", "settings": {"scalar.field": "total_cost_usd", "number.format": "$,.2f"}},
  "05_daily_spend_trend": {"display": "line", "settings": {"graph.show_goal": true}},
  "06_tool_breakdown": {"display": "pie", "settings": {"pie.show_percentages": true}},
  "07_top15_spenders": {"display": "bar", "settings": {"graph.show_values": true}}
}
```

**Execution:**
```bash
python3 create_dashboards.py \
  --sql-dir sql/dashboard/ai_cost \
  --dashboard-name "Executive Dashboard" \
  --chart-config chart_config.json \
  --field-filter vw_combined_daily_costs.provider="Provider" \
  --date start_date=2025-10-01 \
  --date end_date=2025-10-31 \
  --number daily_budget_usd=793.48
```

**Result:**
- 4 cards with different chart types
- Provider dropdown filter
- All filters linked to all cards

---

## 🧪 Testing Protocol

### Unit Test Coverage Requirements

**Minimum coverage: 80%**

```bash
# Run with coverage
pytest tests/metabase/ --cov=scripts.metabase --cov-report=html

# Check coverage
# - chart_templates.py: 100% (pure data)
# - filter_templates.py: 100% (pure data)
# - config_loader.py: 90%+ (test all paths)
# - create_dashboards.py: 70%+ (enhanced functions only)
```

### Manual Testing Checklist

**For Each Chart Type:**
- [ ] Create dashboard with chart type via CLI
- [ ] Open in Metabase UI
- [ ] Verify visual appearance matches type
- [ ] Check viz_settings applied (colors, labels, formatting)
- [ ] Test interactivity (hover, click)

**For Each Filter Type:**
- [ ] Create dashboard with filter type
- [ ] Verify widget appears at top of dashboard
- [ ] For dropdown: Verify shows database values
- [ ] For multi-select: Verify checkboxes work
- [ ] For search: Verify autocomplete works
- [ ] For date range: Verify both pickers work
- [ ] Apply filter and verify charts update

**Claude Integration:**
- [ ] Test 10+ different user requests
- [ ] Verify Claude generates correct configs
- [ ] Test ambiguous requests (Claude asks questions)
- [ ] Test complex multi-chart requests
- [ ] Verify error handling when things go wrong

---

## 📊 Success Metrics Dashboard

**After Implementation, Create This Dashboard:**

```
Dashboard Name: "Chart Automation System Metrics"

Cards:
1. Chart Types Implemented (scalar) - Shows: 13/13
2. Filter Types Implemented (scalar) - Shows: 9/9
3. Dashboards Created (line chart) - Over time
4. Chart Type Usage (pie chart) - Distribution
5. Average Creation Time (scalar) - Shows: <2 min
6. Success Rate (gauge) - Shows: >95%
```

---

## 🎯 Confidence Assessment

### Implementation Confidence: **9/10** (Very High)

**Strengths:**
- ✅ Clear enhancement points (specific line numbers)
- ✅ Working foundation (existing script solid)
- ✅ Well-documented API (Metabase)
- ✅ Comprehensive research completed
- ✅ Phased approach (can test incrementally)
- ✅ Backward compatible (low risk)

**Risks (Mitigated):**
- ⚠️ Field ID resolution (test thoroughly, add fallback)
- ⚠️ SQL syntax migration (test with BigQuery first)
- ⚠️ Visualization settings (reference Metabase docs)

### One-Pass Implementation Score: **9/10**

**Why High Confidence:**
- PRP includes complete code examples
- All functions fully specified with docstrings
- Step-by-step task sequence
- Validation at each step
- Fallback strategies for errors
- Comprehensive testing plan
- External documentation linked

**What Could Go Wrong:**
- Metabase API changes (unlikely, stable API)
- BigQuery metadata issues (add fallback)
- Unexpected field filter behavior (extensive testing mitigates)

### Estimated Timeline

**Optimistic:** 5 days (if no blockers)
**Realistic:** 7 days (with testing and refinement)
**Pessimistic:** 10 days (if field ID issues arise)

**Recommendation:** Plan for 7 days with buffer

---

## 📚 Appendix: Metabase API Reference

### POST /api/card Payload Structure

**Complete Example:**
```json
{
  "name": "Daily Spending Trend",
  "display": "line",
  "description": "Shows daily AI cost trends with goal line",
  "visualization_settings": {
    "graph.dimensions": ["cost_date"],
    "graph.metrics": ["total_cost_usd"],
    "graph.show_goal": true,
    "graph.goal_value": 793.48,
    "graph.goal_label": "Daily Budget",
    "graph.y_axis.auto_range": true,
    "graph.y_axis.title": "Cost (USD)",
    "graph.x_axis.title": "Date"
  },
  "dataset_query": {
    "type": "native",
    "database": 1,
    "native": {
      "query": "SELECT cost_date, SUM(amount_usd) AS total_cost_usd FROM vw_combined_daily_costs WHERE cost_date >= {{start_date}} GROUP BY cost_date",
      "template-tags": {
        "start_date": {
          "id": "abc-123",
          "name": "start_date",
          "display-name": "Start Date",
          "type": "date",
          "widget-type": "date",
          "default": "2025-10-01",
          "required": false
        }
      }
    }
  }
}
```

### Field Filter Parameter Structure

**Example: Provider Dropdown**
```json
{
  "id": "mb_param_provider",
  "name": "Provider",
  "slug": "provider",
  "type": "dimension",
  "widget-type": "category",
  "default": null,
  "required": false,
  "dimension": ["field", 12345, {"base-type": "type/Text"}]
}
```

**Example: User Email Search Box**
```json
{
  "id": "mb_param_user_email",
  "name": "User Email",
  "slug": "user_email",
  "type": "dimension",
  "widget-type": "string/=",
  "default": null,
  "required": false,
  "dimension": ["field", 12346, {"base-type": "type/Text"}]
}
```

**Example: Date Range Picker**
```json
{
  "id": "mb_param_date_range",
  "name": "Date Range",
  "slug": "date_range",
  "type": "dimension",
  "widget-type": "date/range",
  "default": null,
  "required": false,
  "dimension": ["field", 12347, {"base-type": "type/Date"}]
}
```

### Template Tag for Field Filter

**In SQL:**
```sql
WHERE {{provider}}
```

**In template-tags:**
```json
{
  "provider": {
    "id": "mb_param_provider",
    "name": "provider",
    "display-name": "Provider",
    "type": "dimension",
    "widget-type": "category",
    "dimension": ["field", 12345, {"base-type": "type/Text"}],
    "default": null,
    "required": false
  }
}
```

### Parameter Mapping Structure

**Dashboard to Card Mapping:**
```json
{
  "parameter_id": "mb_param_provider",
  "card_id": 123,
  "target": ["dimension", ["template-tag", "provider"]]
}
```

**For static parameters:**
```json
{
  "parameter_id": "mb_param_start_date",
  "card_id": 123,
  "target": ["variable", ["template-tag", "start_date"]]
}
```

**Key Difference:**
- Field filters: `["dimension", ["template-tag", "slug"]]`
- Static params: `["variable", ["template-tag", "slug"]]`

---

## 🎓 Claude Implementation Guide

### How Claude Should Use This PRP

**Step 1: Read Full Context**
- Review all code examples in this PRP
- Understand field filter vs static parameter difference
- Review SQL file patterns
- Check existing script structure

**Step 2: Execute Tasks in Order**
1. Start with field filter support (critical foundation)
2. Then add chart type support
3. Then configuration system
4. Then SQL migration
5. Finally testing and docs

**Step 3: Validate Each Step**
- Run unit tests after each module
- Test with real Metabase after each enhancement
- Verify backward compatibility throughout

**Step 4: Generate Configurations**
- When user requests chart, generate chart_config.json
- Use templates from chart_templates.py as reference
- Execute create_dashboards.py with generated config

**Step 5: Handle Errors Gracefully**
- If field ID resolution fails, fall back to static param
- If config invalid, use template defaults
- If API call fails, clean up partial state

### Example User Interaction Flow

**User:** "Create a line chart for daily spending with provider dropdown"

**Claude Actions:**
1. Identifies: chart=line, sql=05_daily_spend_trend.sql, filter=provider (dropdown)
2. Generates chart_config.json: `{"05_daily_spend_trend": {"display": "line", ...}}`
3. Checks if 05_daily_spend_trend.sql supports field filters (reviews SQL)
4. If not, updates SQL to add `AND {{provider}}`
5. Executes:
   ```bash
   python3 create_dashboards.py \
     --chart-config chart_config.json \
     --field-filter vw_combined_daily_costs.provider="Provider" \
     --date start_date=2025-10-01 --date end_date=2025-10-31 \
     --number daily_budget_usd=793.48
   ```
6. Reports dashboard URL and confirms creation

---

## 📅 Timeline & Milestones

**Total Duration:** 7 days

| Day | Milestone | Deliverable | Validation |
|-----|-----------|-------------|------------|
| 1-2 | Field filter support | create_dimension_parameter() + tests | Provider dropdown works |
| 3 | Chart type support | display_type + viz_settings | Line chart displays |
| 4 | Configuration system | chart_templates.py + config_loader.py | Loads configs correctly |
| 5 | Chart configs created | chart_config.json for 14 files | All charts render |
| 6 | SQL migration | 5 SQL files updated | Field filters work end-to-end |
| 7 | Testing & docs | Test suite + guide | All tests pass, docs complete |

**Critical Path:**
1. Field filter support (blocking all dropdown filters)
2. Chart type support (blocking all non-table visualizations)
3. Configuration system (enables systematic mapping)
4. SQL updates (enables field filter usage)

**Parallel Work Opportunities:**
- Create chart_templates.py while working on create_dashboards.py
- Create test files while implementing functions
- Write documentation while testing

---

## 🏁 Definition of Done

**Feature is complete when:**
- [ ] All 13 chart types can be created programmatically
- [ ] All 9 filter types can be created programmatically
- [ ] chart_config.json maps all 14 SQL files to chart types
- [ ] All SQL files support field filter syntax where appropriate
- [ ] Claude can interpret and execute 95%+ of user requests
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Backward compatibility verified (old commands work)
- [ ] Documentation complete with 20+ examples
- [ ] Dashboard creation time <2 minutes
- [ ] Field filter dropdowns show database values
- [ ] Multi-select filters show checkboxes
- [ ] Goal lines appear on line charts
- [ ] Pie chart percentages display correctly
- [ ] Currency formatting works on scalar charts

**Deployment Checklist:**
- [ ] Code reviewed
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Runbook validated
- [ ] Example configurations tested
- [ ] Claude guide tested with real requests

---

## 🎯 PRP Quality Score

### Self-Assessment: **9/10** (Excellent)

**Completeness:**
- ✅ Full code implementations provided
- ✅ All functions documented with docstrings
- ✅ Complete examples for all features
- ✅ Step-by-step task sequence
- ✅ Validation at each step
- ✅ External resources linked
- ✅ Common pitfalls documented
- ✅ Archon project/tasks created

**Executability:**
- ✅ AI agent can follow linearly
- ✅ All code is copy-paste ready
- ✅ Validation commands executable
- ✅ Clear success criteria
- ✅ Fallback strategies defined

**Missing (0.5 points):**
- Actual Metabase API responses (would need live instance)
- Performance benchmarks (need real data)

**Missing (0.5 points):**
- Advanced chart configurations (combo charts, waterfall)
- Full integration test coverage (would expand testing time)

**Recommendation:** Implement as specified, confident in one-pass success with this PRP.

---

**END OF PRP**

---

## 📌 Implementation Quick Start

**Next Step:** Begin implementation with Task 1

**Archon Project:**
- Project ID: `a3404ec0-5492-494f-9685-7a726a31f41e`
- First Task ID: `68329a02-a4f9-43b7-8314-d520deeb4f58`

**Implementation Branch:** `feature/metabase-chart-automation` (recommended)

**Start Implementation:**
```bash
# Create feature branch
git checkout -b feature/metabase-chart-automation

# Start Task 1 in Archon
mcp__archon__manage_task("update", task_id="68329a02-a4f9-43b7-8314-d520deeb4f58", status="doing")

# Begin coding (see Task 1 in Implementation Tasks section)
```

**All Task IDs Listed in "Quick Reference" section at top of document for easy copy-paste.**
