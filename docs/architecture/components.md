# Components

## Data Ingestion Components

### Anthropic API Client
**Responsibility:** Fetch usage and cost data from Anthropic Claude APIs with robust error handling and retry logic

**Key Interfaces:**
- `fetch_daily_usage(date: str) -> Dict` - Get usage data for specific date
- `fetch_daily_costs(date: str) -> Dict` - Get cost breakdown for date range
- `validate_response(data: Dict) -> bool` - Schema validation before processing

**Dependencies:** Secret Manager (API keys), Cloud Logging (error tracking)

**Technology Stack:** Python requests library, exponential backoff, JSON schema validation

### Cursor API Client
**Responsibility:** Extract team usage data including developer productivity metrics and code acceptance rates

**Key Interfaces:**
- `fetch_team_usage(start_date: str, end_date: str) -> List[Dict]` - Team usage data with date range
- `normalize_timestamps(data: List[Dict]) -> List[Dict]` - Convert Unix timestamps to ISO format
- `validate_email_attribution(data: List[Dict]) -> List[Dict]` - Ensure email format consistency

**Dependencies:** Secret Manager (API keys), Cloud Logging (audit trail)

**Technology Stack:** Python requests, date/time utilities, email validation

## Data Processing Components

### Data Transformation Engine
**Responsibility:** Normalize raw API data into consistent fact table format across all platforms

**Key Interfaces:**
- `transform_anthropic_usage(raw_data: Dict) -> List[Dict]` - Usage fact normalization
- `transform_cursor_metrics(raw_data: List[Dict]) -> List[Dict]` - Productivity metric processing
- `apply_user_attribution(facts: List[Dict], mappings: List[Dict]) -> List[Dict]` - Cost allocation logic

**Dependencies:** dim_api_keys, dim_users tables for lookups

**Technology Stack:** Python pandas for data manipulation, custom transformation logic

## Data Storage Components

### BigQuery Data Warehouse
**Responsibility:** Scalable analytics storage with partitioned tables optimized for time-series analysis

**Key Interfaces:**
- `load_raw_data(table: str, data: List[Dict])` - Bulk insert with partition management
- `refresh_curated_views()` - Update aggregated reporting views
- `execute_quality_checks() -> Dict` - Run automated data quality queries

**Dependencies:** Google Cloud IAM for access control, Cloud Logging for audit

**Technology Stack:** BigQuery Python client, SQL for view definitions, partitioning/clustering optimization

## Dashboard Automation Components

### Metabase Chart Builder
**Responsibility:** Programmatic creation of all chart types (13 types) with visualization settings via Metabase API

**Key Interfaces:**
- `create_card(display_type, viz_settings)` - Create chart with specific type and formatting
- `create_dimension_parameter(table, column)` - Create field filter with dropdown/search widgets
- `load_chart_config(config_file)` - Load chart type mappings from JSON
- `resolve_field_id(table, column)` - Resolve BigQuery field IDs for filters

**Dependencies:** Metabase REST API, BigQuery metadata API, chart_templates.py reference

**Technology Stack:** Python requests, JSON configuration, chart/filter template system

**Supported Chart Types:**
- scalar (KPI cards), line (trends), bar (comparisons), pie (breakdowns)
- gauge (progress), combo (dual-axis), area (cumulative)
- row (horizontal bars), scatter (correlation), funnel (conversion)
- waterfall (sequential), pivot (multi-dimensional), table (detailed data)

### Metabase Filter Manager
**Responsibility:** Field filter creation with dropdown/multi-select/search widgets using BigQuery metadata

**Key Interfaces:**
- `create_dimension_parameter(slug, table, column, widget_type)` - Field filter with dynamic values
- `parse_field_filters(cli_args)` - Parse command-line filter specifications
- `recommend_widget_type(column_name, cardinality)` - Auto-select dropdown vs search

**Dependencies:** BigQuery metadata API, filter_templates.py reference

**Technology Stack:** Python requests, Metabase field filter API

**Supported Filter Types:**
- Field Filters: dropdown (single-select), multi-select (checkboxes), search (autocomplete)
- Date Filters: date range (start+end), relative date (last 30 days)
- Number Filters: number range (min+max)
- Static Filters: date (single), number (input), text (input)

### Dashboard Configuration Manager
**Responsibility:** Load, validate, and merge chart/filter configurations for systematic dashboard generation

**Key Interfaces:**
- `load_chart_config(file)` - Load JSON chart type mappings
- `resolve_chart_type_and_settings(sql_file, config)` - Get chart type + viz_settings
- `validate_chart_config(config)` - Validate configuration structure

**Dependencies:** chart_templates.py, filter_templates.py, jsonschema validation

**Technology Stack:** Python JSON parsing, pydantic validation, template merging

---
