#!/usr/bin/env python3
"""Verify development environment setup."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def verify_python_version():
    """Verify Python version is 3.11+."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (meets requirement ≥3.11)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires ≥3.11)")
        return False

def verify_dependencies():
    """Verify core dependencies are installed."""
    dependencies = [
        "google.cloud.bigquery",
        "google.cloud.secretmanager",
        "google.cloud.logging",
        "pandas",
        "requests"
    ]

    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep}")
        except ImportError:
            print(f"✗ {dep}")
            missing.append(dep)

    return len(missing) == 0

def verify_project_structure():
    """Verify project directories exist."""
    required_dirs = [
        "src/ingestion",
        "src/processing",
        "src/storage",
        "src/shared",
        "src/orchestration",
        "sql/tables",
        "sql/views",
        "tests/unit",
        "tests/integration"
    ]

    base_dir = os.path.dirname(os.path.dirname(__file__))
    missing = []

    for dir_path in required_dirs:
        full_path = os.path.join(base_dir, dir_path)
        if os.path.exists(full_path):
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path}")
            missing.append(dir_path)

    return len(missing) == 0

def verify_config():
    """Verify configuration can be loaded."""
    try:
        from shared.config import config
        print(f"✓ Configuration loaded (project: {config.project_id}, dataset: {config.dataset})")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def main():
    """Run all verification checks."""
    print("AI Usage Analytics Dashboard - Environment Verification")
    print("=" * 60)

    checks = [
        ("Python Version", verify_python_version),
        ("Dependencies", verify_dependencies),
        ("Project Structure", verify_project_structure),
        ("Configuration", verify_config)
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Error running {name}: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    if all(results):
        print("✓ All checks passed! Development environment is ready.")
        sys.exit(0)
    else:
        print("✗ Some checks failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()