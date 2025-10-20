---
description: "Generate comprehensive PRP for feature implementation with thorough research"
argument-hint: "[feature-file-path]"
---
# Create PRP

## Feature file: $ARGUMENTS

Generate a complete PRP for general feature implementation with thorough research. Ensure context is passed to the AI agent to enable self-validation and iterative refinement. Read the feature file first to understand what needs to be created, how the examples provided help, and any other considerations.

The AI agent only gets the context you are appending to the PRP and training data. Assume the AI agent has access to the codebase and the same knowledge cutoff as you, so it's important that your research findings are included or referenced in the PRP. The Agent has WebSearch capabilities and Serena MCP server access, so pass URLs to documentation and examples.

**CRITICAL: Web search and Serena MCP server exploration are your best friends. Use them extensively throughout this process.**

## Research Process

1. **Codebase Analysis Using Serena MCP Server (CRITICAL)**

   - Use `mcp__serena/dev__get_symbols_overview` to understand file structures
   - Use `mcp__serena__find_symbol` to locate similar features/patterns
   - Use `mcp__serena__search_for_pattern` to find existing implementations
   - Use `mcp__serena__find_referencing_symbols` to understand relationships
   - Identify files to reference in PRP using `mcp__serena__list_dir` recursively
   - Note existing conventions to follow from real code examples
   - Check test patterns for validation approach using Serena tools
2. **External Research (EXTENSIVE - CRITICAL)**

   - **Web search the target technology extensively** - this is essential
   - Study official documentation, APIs, and getting started guides
   - Research best practices and common architectural patterns
   - Find real-world implementation examples and tutorials
   - Identify common gotchas, pitfalls, and edge cases
   - Look for established project structure conventions
3. **Technology Pattern Analysis**

   - Examine successful implementations found through web research
   - Identify project structure and file organization patterns using Serena
   - Extract reusable code patterns and configuration templates
   - Document framework-specific development workflows
   - Note testing frameworks and validation approaches
4. **User Clarification** (if needed)

   - Specific patterns to mirror and where to find them?
   - Integration requirements and where to find them?

## PRP Generation

Using PRPs/templates/prp_base.md as template:

### Critical Context to Include and pass to the AI agent as part of the PRP

**Technology Documentation (from web search)**:

- Official framework documentation URLs with specific sections
- Getting started guides and tutorials
- API references and best practices guides
- Community resources and example repositories

**Implementation Patterns (from Serena research)**:

- Framework-specific project structures and conventions
- Configuration management approaches from codebase analysis
- Development workflow patterns found in existing code
- Testing and validation approaches from current test files

**Real-World Examples**:

- Links to successful implementations found online
- Code snippets and configuration examples from Serena exploration
- Common integration patterns discovered in current codebase
- Deployment and setup procedures

**Project-Specific Context**:

- **BigQuery Patterns**: Reference existing views, stored procedures, and query patterns
- **Python Script Patterns**: Reference data pipeline scripts and API integration approaches
- **GCP Integration**: Reference Cloud Functions, Cloud Run, and Scheduler patterns
- **Metabase Integration**: Include dashboard creation and SQL card patterns
- **API Integration**: Reference Claude Admin API and Cursor API patterns
- **Data Validation**: Reference existing validation scripts and data quality approaches

### Implementation Blueprint

- Start with pseudocode showing approach
- Reference real files for patterns
- Include error handling strategy
- list tasks to be completed to fullfill the PRP in the order they should be completed
- MAKE SURE TO CREATE A NEW PROJECT(IF NEEDED) AND ALL THE TASKS IN ARCHON AS WELL.

### Validation Gates (Must be Executable - Samba-AI-Usage-Stats Specific)

```bash
# Project Health Check
python -m pytest                    # Python unit tests
python scripts/validation/run_validation.py  # Data validation
bq query --use_legacy_sql=false "SELECT 1"  # BigQuery connection

# Project-Specific Validation
python scripts/validation/run_data_validation.py  # Data integrity
gcloud scheduler jobs list          # Cloud Scheduler validation
gcloud run jobs list               # Cloud Run validation

# BigQuery/Metabase specific (if relevant to feature)
bq ls ai-workflows-459123:ai_usage  # Dataset validation
bq query --dry_run --use_legacy_sql=false < sql_file.sql  # SQL validation
python scripts/metabase/create_dashboards.py --dry-run  # Dashboard validation
```

***CRITICAL: Do extensive web research AND Serena MCP exploration before writing the PRP***
***Use WebSearch tool and Serena MCP server extensively to understand the technology and codebase deeply***
***The AI agent executing this PRP will ONLY have the context you provide***

***CRITICAL AFTER YOU ARE DONE RESEARCHING AND EXPLORING THE CODEBASE BEFORE YOU START WRITING THE PRP***

***ULTRATHINK ABOUT THE PRP AND PLAN YOUR APPROACH THEN START WRITING THE PRP***

## Output

Save as: `PRPs/cc-prp-plans/prp-{feature-name}.md` (following naming conventions)

## Quality Checklist

- [ ] Extensive web research completed on target technology/feature
- [ ] Serena MCP server used extensively for codebase analysis
- [ ] Official documentation thoroughly reviewed and URLs included
- [ ] Real-world examples and patterns identified from web search
- [ ] All necessary project context included (BigQuery, GCP, Python, Metabase)
- [ ] Validation gates are executable and project-specific
- [ ] References existing project patterns and conventions via Serena
- [ ] Clear implementation path with step-by-step tasks
- [ ] New project(if needed) and tasks created in Archon as well.
- [ ] Error handling and edge cases documented
- [ ] Integration points with BigQuery/GCP/Metabase identified (if relevant)
- [ ] Code examples extracted from codebase using Serena tools

Score the PRP on a scale of 1-10 (confidence level to succeed in one-pass implementation using claude codes)

Remember: The goal is one-pass implementation success through comprehensive context from both web research and deep codebase understanding via Serena MCP server.
