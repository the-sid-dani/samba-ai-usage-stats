# File Organization Standards

## CRITICAL RULE: NO FILES IN ROOT DIRECTORY

**NEVER** leave temporary files, test scripts, or documentation in the root directory. Every file must have a proper home.

## Root Directory - ONLY These Files Allowed

- `README.md` - Project overview
- `CLAUDE.md` - Project configuration for Claude Code
- `requirements.txt` - Python dependencies
- `package.json` - Node.js dependencies (if applicable)
- `Dockerfile` - Container configuration
- `cloudbuild.yaml` - CI/CD configuration
- `.env*` files - Environment configurations
- `.gitignore` - Git ignore rules

## Proper Directory Structure

### Scripts and Tools
```
scripts/
├── test/           # All test scripts (test_*.py)
├── debug/          # Debug scripts (debug_*.py)
├── pipeline/       # Pipeline scripts (run_*, *_pipeline.py)
├── data/           # Data processing scripts (get_*, load_*, query_*)
└── deploy/         # Deployment scripts
```

### Documentation
```
docs/
├── deployment/     # Deployment guides and setup docs
├── queries/        # SQL queries and database documentation
├── architecture/   # System architecture documents
├── prd/           # Product requirements
└── stories/       # User stories
```

### Data and Logs
```
data/
├── mappings/      # JSON mapping files
├── temp/          # Temporary data (gitignored)
└── cache/         # Cached data (gitignored)

logs/              # All log files (*.log)
```

### Temporary Files
```
temp/              # All temporary files (gitignored)
├── debug/         # Debug outputs
└── test/          # Test outputs
```

## File Naming Conventions

### Scripts
- Test scripts: `test_*.py` → `scripts/test/`
- Debug scripts: `debug_*.py` → `scripts/debug/`
- Pipeline scripts: `*_pipeline.py`, `run_*.py` → `scripts/pipeline/`
- Data scripts: `get_*.py`, `load_*.py`, `query_*.py` → `scripts/data/`

### Documentation
- Deployment docs: `*_DEPLOYMENT.md`, `*_SETUP.md` → `docs/deployment/`
- Query docs: `*_QUERIES.md` → `docs/queries/`

### Data Files
- Mapping files: `*.json` → `data/mappings/`
- Log files: `*.log` → `logs/`

## Enforcement

The `.gitignore` file is configured to block common temporary file patterns from being committed to the root directory. This prevents the mess from happening again.

## Consequences of Violating Standards

- **Immediate**: Files will be moved to proper locations
- **Review**: Pull requests with root directory clutter will be rejected
- **Process**: This cleanup process will be repeated if violations occur

## Quick Reference Commands

```bash
# Move test scripts
mv test_*.py scripts/test/

# Move debug scripts
mv debug_*.py scripts/debug/

# Move pipeline scripts
mv *_pipeline.py run_*.py scripts/pipeline/

# Move data scripts
mv get_*.py load_*.py query_*.py scripts/data/

# Move deployment docs
mv *_DEPLOYMENT.md *_SETUP.md docs/deployment/

# Move query docs
mv *_QUERIES.md docs/queries/

# Move logs
mv *.log logs/

# Move data files
mv *.json data/mappings/
```

## Memory Integration

This standard is stored in Serena memory as `file-organization-standards` for future reference and enforcement.