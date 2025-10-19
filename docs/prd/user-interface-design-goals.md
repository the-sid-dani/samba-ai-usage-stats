# User Interface Design Goals

## Dashboard Strategy

**Platform:** Self-hosted Metabase on GCP Compute Engine
**Architecture:** See `/docs/api-reference/metabase-architecture.md`
**Cost:** ~$25/month VM + $0 licensing

## Core Dashboards (4 Required)

### 1. Executive Summary Dashboard
**Target Users:** Finance Team, C-Suite
**Data Sources:** All expense tables aggregated
**Key Metrics:**
- Total monthly AI spend across all platforms
- Month-over-month growth rate
- Platform cost distribution (pie chart)
- Top 5 users by spend
- Budget vs actual variance

**Visualizations:**
- KPI cards (total spend, growth %)
- Line chart (monthly trends)
- Pie chart (platform distribution)
- Bar chart (user ranking)

### 2. Cost Allocation Workbench
**Target Users:** Finance Team, Department Heads
**Data Sources:** All expense tables + user mapping
**Key Metrics:**
- User-level cost breakdown
- Team/department aggregations
- Platform-by-user spend matrix
- Cost per productivity ratios

**Visualizations:**
- Detailed cost tables (sortable, filterable)
- Heatmap (user × platform spending)
- Export-friendly format for budget reviews

### 3. Productivity Analytics Dashboard
**Target Users:** Engineering Managers, Team Leads
**Data Sources:** `claude_code_usage_stats`, `cursor_usage_stats`
**Key Metrics:**
- Lines of code accepted (acceptance rate)
- Commits and PRs generated with AI
- Developer efficiency rankings
- Tool effectiveness comparison (Claude Code vs Cursor)

**Visualizations:**
- Acceptance rate trends (line chart)
- Productivity heatmap (team performance)
- Tool comparison (side-by-side metrics)

### 4. Platform ROI Analysis
**Target Users:** Technical Architects, Finance
**Data Sources:** All tables (usage + expenses)
**Key Metrics:**
- Cost per line of code
- Cost per accepted suggestion
- Platform efficiency scores
- ROI by user and platform

**Visualizations:**
- Scatter plots (cost vs productivity)
- ROI trend lines
- Efficiency comparison charts
- Platform recommendation insights

## Accessibility & Usability

- **WCAG AA Compliance:** Full keyboard navigation, screen reader support
- **Color Scheme:** Color-blind friendly (blue/orange, not red/green)
- **Responsive Design:** Desktop-optimized with tablet support
- **Export Options:** CSV, XLSX, JSON, PNG for all dashboards

---
