# Execute PRP Implementation

Execute a comprehensive PRP (Project Requirements Plan) to implement features systematically using context engineering principles and Samba-AI-Usage-Stats architectural patterns. This command ensures robust implementation with comprehensive validation, error handling, and quality assurance.

## PRP File: $ARGUMENTS

## Execution Process

### 1. **Enhanced System Health Check** (Samba-AI-Usage-Stats Specific)

   **Critical Infrastructure Validation:**
   - **REQUIRED**: BigQuery connection: `bq query --use_legacy_sql=false "SELECT 1"`
   - **REQUIRED**: GCP authentication: `gcloud auth application-default print-access-token`
   - **Database**: BigQuery datasets and tables validation
   - **Build System**: Python 3.11+ and pip version compatibility
   - **Development Environment**: Environment variables and API keys

   **Context-Specific System Checks:**
   - If BigQuery work: `bq ls ai-workflows-459123:ai_usage` + verify view definitions
   - If Metabase work: Test dashboard API connection and card creation
   - If API work: Verify Claude Admin API and Cursor API access
   - If Pipeline work: Test Cloud Scheduler and Cloud Run jobs
   - If Validation work: Run data integrity checks

   **Pre-Implementation Validation:**
   ```bash
   # Core system validation
   python --version
   python -m pytest --version
   bq version
   gcloud version
   ```

### 2. **Comprehensive PRP Analysis & Context Loading**

   **PRP Structure Validation:**
   - Read PRP file: `$ARGUMENTS`
   - Validate PRP completeness and structure
   - Extract implementation requirements and success criteria
   - Identify project-specific integration points
   - Map to existing architectural patterns

   **Deep Context Research:**
   - Follow all PRP instructions and extend research as needed
   - Perform targeted web searches for technical patterns
   - Explore codebase using Serena MCP tools for relevant patterns
   - Use Archon MCP for project context and task management
   - Leverage Context-7 MCP for library documentation
   - Ensure comprehensive understanding before implementation

   **Architecture Pattern Identification:**
   - Verify BigQuery view and stored procedure patterns
   - Check Python script integration requirements
   - Identify GCP service integration needs
   - Review Metabase dashboard patterns
   - Map data validation requirements

### 3. **ULTRATHINK - Comprehensive Implementation Planning**

   **Strategic Planning:**
   - Create comprehensive plan addressing ALL PRP requirements
   - Break down complex tasks into atomic, manageable steps
   - **MANDATORY**: Use TodoWrite tool for implementation tracking
   - Identify implementation patterns from existing project code
   - Plan validation strategy and testing approach
   - Consider performance, security, and maintainability impacts

   **Risk Assessment:**
   - Identify potential breaking changes and mitigation strategies
   - Plan backward compatibility considerations
   - Assess impact on BigQuery views and dashboards
   - Consider data integrity and validation implications
   - Plan rollback scenarios if needed

### 4. **Systematic Implementation**

   **Code Implementation Phase:**
   - Execute the PRP systematically following the planned approach
   - Implement all code changes following Python/BigQuery patterns
   - Use established Python script patterns for data pipelines
   - Follow BigQuery SQL patterns for analytics queries
   - Implement proper GCP service integration if needed
   - Ensure data validation and quality checks

   **Implementation Standards:**
   - Follow Python PEP 8 style guide and project conventions
   - Use consistent SQL formatting for BigQuery queries
   - Implement proper error handling and edge cases
   - Add comprehensive logging and monitoring
   - Follow GCP security best practices

### 5. **Multi-Layer Validation Framework**

   **Structure Validation:**
   ```bash
   # Verify file structure and imports
   find scripts -name "*.py" | head -20 | xargs ls -la
   find sql -name "*.sql" | head -10 | xargs ls -la
   ```

   **Content Validation:**
   ```bash
   # Check for incomplete implementations
   grep -r "TODO\|PLACEHOLDER\|FIXME" scripts/ sql/ || echo "✅ No incomplete markers"
   grep -r "print(" scripts/ && echo "⚠️ Remove debug prints" || echo "✅ Clean logging"
   ```

   **Functionality Validation:**
   ```bash
   # Core system checks
   python -m pytest
   python scripts/validation/run_validation.py
   bq query --dry_run --use_legacy_sql=false < sql/views/latest_view.sql
   ```

   **Samba-AI-Usage-Stats Specific Validation:**
   ```bash
   # BigQuery dataset check
   bq ls ai-workflows-459123:ai_usage || echo "Dataset verification"

   # API integration check (if applicable)
   python scripts/api_investigation/test_claude_admin_api.py --dry-run || echo "API verification"

   # Data validation check
   python scripts/validation/run_data_validation.py

   # Metabase dashboard check (if applicable)
   python scripts/metabase/create_dashboards.py --dry-run || echo "Dashboard verification"
   ```

### 6. **Quality Assurance Process**

   **Code Quality Verification:**
   - [ ] Follows Python best practices and PEP 8 standards
   - [ ] Uses established BigQuery SQL patterns (if applicable)
   - [ ] Implements proper GCP service integration (if applicable)
   - [ ] Includes comprehensive error handling and edge cases
   - [ ] Maintains project architectural conventions
   - [ ] Implements proper data validation and quality checks

   **Integration Testing:**
   - [ ] Manual testing of all implemented features
   - [ ] Cross-system integration testing (BigQuery, GCP, Metabase)
   - [ ] Performance impact assessment on BigQuery queries
   - [ ] Security considerations reviewed and implemented
   - [ ] Data integrity verified across pipelines

   **System Compatibility:**
   - [ ] No breaking changes to existing functionality
   - [ ] Backward compatibility maintained where possible
   - [ ] BigQuery schema changes properly implemented (if needed)
   - [ ] Environment configuration updated (if needed)

### 7. **Documentation and Knowledge Management**

   **Required Documentation Updates:**
   - [ ] Update relevant CLAUDE.md sections if architectural patterns change
   - [ ] Update script documentation and code comments
   - [ ] Add/update API documentation for new data pipelines
   - [ ] Update .claude/commands if new patterns emerge
   - [ ] Document new BigQuery views and procedures
   - [ ] Update Metabase dashboard documentation if modified
   - [ ] Create/update PRP documentation for future reference

   **Knowledge Preservation:**
   - [ ] Use Serena memory system to document new patterns
   - [ ] Update Archon project management with implementation notes
   - [ ] Document any architectural decisions or trade-offs made

### 8. **Final Verification & Completion**

   **Comprehensive Final Check:**
   - Re-read the original PRP to ensure 100% requirement coverage
   - Verify all success criteria from PRP are met
   - Run complete validation suite one final time
   - Test end-to-end functionality in development environment
   - Verify observability and monitoring are functioning

   **Completion Report:**
   - Document implementation status and any deviations from PRP
   - Note any follow-up items or recommendations
   - Confirm system health and stability
   - Provide clear handoff documentation if needed

## Success Criteria

The implementation is complete when ALL of the following criteria are met:

- [ ] **PRP Requirements**: All requirements from the PRP document are fully implemented
- [ ] **Code Quality**: Python code passes all PEP 8 checks and tests
- [ ] **Testing**: All pytest unit tests pass without failures
- [ ] **SQL Validation**: BigQuery SQL queries pass dry-run validation
- [ ] **Build**: Docker build completes successfully (if applicable)
- [ ] **System Health**: All GCP and BigQuery health checks pass
- [ ] **Data Integrity**: Data validation scripts pass all checks
- [ ] **API Integration**: Claude Admin and Cursor APIs accessible (if applicable)
- [ ] **Metabase Integration**: Dashboard cards and visualizations work (if applicable)
- [ ] **GCP Services**: Cloud Functions/Run/Scheduler configured correctly (if applicable)
- [ ] **Performance**: BigQuery query performance meets requirements
- [ ] **Security**: GCP security best practices followed and API keys secured
- [ ] **Documentation**: All relevant documentation updated and accurate
- [ ] **Backward Compatibility**: No breaking changes to existing functionality
- [ ] **Manual Testing**: End-to-end manual testing passes
- [ ] **PRP Verification**: Final review confirms 100% PRP requirement coverage

## Error Handling & Retry Logic

### Systematic Error Resolution Process

**When Validation Fails:**
1. **Error Analysis**: Identify root cause from logs, output, and error messages
2. **Pattern Recognition**: Match error to common project patterns
3. **Targeted Fix**: Address specific issue without affecting working components
4. **Incremental Validation**: Test fix in isolation before full validation
5. **Re-validation**: Run complete validation suite
6. **Maximum 3 Retry Cycles**: Escalate or seek help if still failing

### Common Error Patterns & Solutions

**Python Execution Errors:**
- Check import statements and module dependencies
- Verify Python version compatibility
- Check API client initialization patterns
- Review data type handling and conversions

**BigQuery Failures:**
- Verify dataset and table permissions
- Check SQL syntax and BigQuery-specific functions
- Review view dependencies and references
- Validate schema compatibility

**Test Failures:**
- Update test cases to match new implementation
- Mock API responses appropriately
- Check test data fixtures
- Verify async patterns in data pipelines

**Samba-AI-Usage-Stats Specific Issues:**
- **API Problems**: Check API keys in Secret Manager and authentication
- **GCP Issues**: Verify service account permissions and project access
- **Pipeline Problems**: Check Cloud Scheduler cron expressions and job configurations
- **Data Issues**: Verify data validation rules and integrity checks

**Performance Issues:**
- Check BigQuery query complexity and partitioning
- Review Python script memory usage
- Validate batch processing sizes
- Monitor API rate limits

### Escalation Process

**If 3 retry cycles fail:**
1. Document all error patterns encountered
2. Capture full logs and system state
3. Create detailed issue report with reproduction steps
4. Seek architectural guidance or external review
5. Consider alternative implementation approaches

## Validation Commands Reference

### Core System Validation
```bash
# Essential checks that must always pass
python -m pytest                    # Python unit tests
python -m pylint scripts/           # Code quality and style
bq query --dry_run --use_legacy_sql=false < query.sql  # SQL validation
docker build -t test-build .       # Container build test (if applicable)
```

### Samba-AI-Usage-Stats Health Checks
```bash
# System health validation
bq query --use_legacy_sql=false "SELECT 1"  # BigQuery connection
gcloud auth application-default print-access-token  # GCP auth check
python --version && pip --version  # Version compatibility check
```

### Feature-Specific Validation
```bash
# BigQuery system (if applicable)
bq ls ai-workflows-459123:ai_usage | head -5  # Dataset tables
bq show ai-workflows-459123:ai_usage.view_name  # View definition

# API integration (if applicable)
python scripts/api_investigation/test_claude_admin_api.py --dry-run
python scripts/api_investigation/test_cursor_admin_api.py --dry-run

# Metabase system (if applicable)
python scripts/metabase/create_dashboards.py --list  # Dashboard verification
python scripts/metabase/create_single_card.py --dry-run  # Card creation test
```

## Reference Notes

**PRP Re-Reference**: Always available to reference the original PRP document at any stage if clarification is needed on requirements, context, or success criteria.

**Architecture Patterns**: Leverage existing Python script patterns for data pipelines, BigQuery SQL patterns for analytics, GCP service integration, and Metabase dashboard creation.

**System Constraints**: Remember GCP project ID (ai-workflows-459123), BigQuery dataset requirements, and specific integration patterns for Claude Admin API and Cursor API.

**Quality Standards**: Maintain high code quality standards with comprehensive testing, proper error handling, and full data validation throughout the implementation process.