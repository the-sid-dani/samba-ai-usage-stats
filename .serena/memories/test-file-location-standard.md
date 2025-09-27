# Test File Location Standard

## CRITICAL RULE: Test File Placement
- ALL new tests MUST be created in the `tests/` folder, NOT in the root directory
- Follow existing test structure:
  - Unit tests: `tests/unit/`
  - Integration tests: `tests/integration/`
  - End-to-end tests: `tests/e2e/`

## Existing Structure
```
tests/
├── unit/
│   ├── test_cursor_client.py
│   ├── test_anthropic_client.py
│   ├── test_bigquery_client.py
│   └── ...
├── integration/
│   └── test_multi_platform_pipeline.py
└── e2e/
    └── __init__.py
```

## Why This Matters
- Maintains clean project structure
- Follows Python testing conventions
- Keeps test files organized and discoverable
- Prevents cluttering the root directory

## Developer Reminder
When creating ANY new test file, always place it in the appropriate subdirectory under `tests/` based on the test type.