---
description: "Generate comprehensive initial plan document for feature development with autonomous research"
argument-hint: "[feature-description]"
---

# Create Initial Plan

## Feature: $ARGUMENTS

Generate a comprehensive initial plan document through autonomous research and codebase analysis. This command creates the foundational document that defines feature goals, scope, and integration requirements - serving as the essential blueprint for subsequent PRP generation.

**CRITICAL: This command is self-contained and performs its own research. No prior primer context required.**

**IMPORTANT: Do NOT get stuck in analysis loops. Complete research efficiently and generate the initial document.**

The AI agent executing the eventual PRP will only get the context you provide in this initial document. Make this initial plan comprehensive and project-aware through extensive research and codebase analysis.

## Research & Analysis Process

### 1. **Deep Codebase Analysis Using Serena MCP Server (CRITICAL)**
- Use `mcp__serena__get_symbols_overview` to understand project structure and patterns
- Use `mcp__serena__find_symbol` to locate similar features and implementations
- Use `mcp__serena__search_for_pattern` to discover existing architectural patterns
- Use `mcp__serena__find_referencing_symbols` to understand component relationships
- Use `mcp__serena__list_dir` recursively to map project organization
- Identify existing components, hooks, and patterns to leverage
- Analyze current test patterns and validation approaches
- Review database schema and repository patterns

### 2. **Technology Context Research (EXTENSIVE)**
- **Web search for feature-relevant technologies** extensively
- Study existing implementations and best practices online
- Research UI/UX patterns for similar features
- Identify common architectural approaches and gotchas
- Find established design patterns and component libraries
- Look for performance optimization strategies
- Research accessibility requirements and compliance patterns

### 3. **Project-Specific Integration Analysis**
- **BigQuery Integration**: Analyze existing views, tables, and query patterns
- **Python Script Patterns**: Review data pipeline scripts and API integrations
- **GCP Infrastructure**: Understand Cloud Functions, Cloud Run, and Scheduler patterns
- **Metabase Integration**: Review dashboard creation and SQL card patterns
- **Data Validation**: Analyze validation scripts and data quality checks
- **API Integrations**: Review Claude Admin API and Cursor API integration patterns

### 4. **Feature Scope & Goals Definition**
- Translate user description into specific functionality requirements
- Define core UI components and user interactions needed
- Identify integration points with existing systems
- Determine technical complexity level and development approach
- Plan user experience flows and interface requirements

## Initial Document Generation

Using `PRPs/templates/initial-template.md` as **DIRECTIONAL REFERENCE** (not rigid template):

### Critical Sections to Research & Define

**Feature Purpose & Core Components:**
- Clear statement of what users should accomplish with this feature
- Essential UI elements and interactions required
- Core functionality scope and user experience goals
- Integration requirements with existing components found via Serena analysis

**Architecture Integration Strategy:**
- Specific integration points with BigQuery datasets and views
- Python script integration needs (data pipelines, API calls)
- GCP service requirements (Cloud Functions, Cloud Run, Scheduler)
- BigQuery schema changes and view definitions
- Metabase dashboard and visualization requirements

**Development Patterns & Implementation Approach:**
- Script architecture following discovered Python conventions
- SQL query patterns consistent with existing BigQuery views
- Data pipeline approach matching existing ETL patterns
- API integration patterns for Claude Admin and Cursor APIs
- Performance optimization following BigQuery best practices

**File Organization & Project Structure:**
- Specific file placement following discovered directory conventions
- Script organization matching existing Python patterns
- SQL file structure based on current BigQuery organization
- GCP deployment configuration using established patterns
- Test file organization following pytest patterns

**Security & Access Control:**
- API key management using Google Secret Manager patterns
- Service account permissions following GCP IAM patterns
- Data validation and sanitization approaches
- Security considerations specific to data pipelines

### Implementation Blueprint & Task Breakdown
- Reference specific files and patterns discovered via Serena research
- Create prioritized task list for development phases
- Include error handling strategy based on existing patterns
- Plan testing approach using discovered test infrastructure
- Define validation gates using project-specific commands

### Technology Context & Best Practices
- Include relevant documentation URLs and resources from web research
- Reference successful implementation examples found online
- Document common gotchas and edge cases discovered
- Include performance considerations and optimization strategies
- Note accessibility requirements and compliance approaches

## Quality Research Checklist

**Before Writing the Initial Document:**
- [ ] Extensive Serena MCP exploration of codebase completed
- [ ] Project structure and patterns thoroughly analyzed
- [ ] Similar features and implementations identified in codebase
- [ ] Web research on relevant technologies and best practices completed
- [ ] Integration points with BigQuery/GCP/Metabase systems analyzed
- [ ] Existing Python script patterns and conventions documented
- [ ] BigQuery schema and view patterns reviewed
- [ ] Test patterns and validation approaches identified
- [ ] File organization and naming conventions discovered
- [ ] Security and performance patterns analyzed

**Critical Context to Include:**
- Specific script files and patterns to reference (from Serena analysis)
- Integration requirements with discovered project systems
- Development workflow based on existing project conventions
- Testing approach using established project infrastructure
- Deployment and validation commands specific to samba-ai-usage-stats

## Validation Requirements (Samba-AI-Usage-Stats Specific)

```bash
# Project Health Checks
python -m pytest                    # Python unit tests
python scripts/validation/run_validation.py  # Data validation
bq query --use_legacy_sql=false "SELECT 1"  # BigQuery connection

# Feature-Specific Validation (adapt based on feature analysis)
python scripts/validation/run_data_validation.py  # Data integrity
gcloud scheduler jobs list          # Cloud Scheduler jobs
gcloud run jobs list               # Cloud Run jobs

# System Integration Validation (if relevant)
# Add based on discovered integration requirements
```

## Output Location

Save as: `PRPs/cc-prp-initials/initial-{feature-name}.md`

**Naming Convention:**
- Use kebab-case for feature name derived from user description
- Keep name descriptive but concise
- Example: `initial-multi-canvas-system.md`, `initial-agent-workflow-builder.md`

## Ultra-Think Before Writing

**After completing all research, before writing the initial document:**

1. **Feature Goals Clarity**: Is the intended functionality crystal clear and well-defined?
2. **Integration Strategy**: How does this feature align with discovered project architecture?
3. **Implementation Feasibility**: Is the scope realistic given existing patterns and infrastructure?
4. **Context Completeness**: Have I included all necessary project context for future PRP generation?
5. **Template Adaptation**: Which template sections are relevant vs. which should be customized for this specific feature?

### Critical Success Factors
- **Autonomous Research**: All necessary context gathered through independent analysis
- **Project Awareness**: Feature design aligns with discovered architectural patterns
- **Implementation Ready**: Clear path forward based on existing project conventions
- **Context Rich**: Future PRP generation has all necessary background information
- **Goal Focused**: User intentions and feature purpose clearly articulated

**Remember**: This initial document serves as the foundation for all subsequent development. It must be comprehensive, project-aware, and implementation-focused based on thorough research rather than assumptions.

*** CRITICAL: Complete focused research (maximum 10 tool calls) then IMMEDIATELY write the initial document ***
*** Do NOT get stuck in endless analysis - research efficiently then create the document ***
*** The quality of this initial document directly impacts PRP generation and implementation success ***

## Quality Validation Checklist

- [ ] Deep codebase analysis completed using Serena MCP tools extensively
- [ ] Web research on relevant technologies and patterns completed
- [ ] Feature goals clearly defined and user-focused
- [ ] Integration strategy aligns with discovered project architecture
- [ ] Implementation approach based on existing project conventions
- [ ] File organization follows discovered directory patterns
- [ ] Security considerations address project-specific requirements
- [ ] Testing strategy uses established project infrastructure
- [ ] Template used as directional guidance, not rigid structure
- [ ] All necessary context included for future PRP generation

Score the Initial Plan on a scale of 1-10 (confidence level that this document provides a solid foundation for successful PRP generation and eventual feature implementation).