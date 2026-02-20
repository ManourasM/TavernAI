#!/usr/bin/env python3
"""
Quick test runner for TavernAI backend.
Usage: python run_tests.py [command]

Commands:
  install  - Install test dependencies
  run      - Run all tests
  coverage - Run tests with coverage report
  fast     - Run tests without slow tests
  watch    - Run tests in watch mode (requires pytest-watch)
"""

import subprocess
import sys
import os


def run_cmd(cmd, description=""):
    """Run a command and exit on failure."""
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n❌ Failed: {description}")
        sys.exit(1)
    print(f"\n✅ Success: {description}")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    
    if command == "install":
        run_cmd("pip install -r requirements-test.txt", "Installing test dependencies")
    
    elif command == "run":
        run_cmd("pytest tests -v", "Running all tests")
    
    elif command == "coverage":
        run_cmd("pytest tests -v --cov=app --cov-report=html --cov-report=term", 
                "Running tests with coverage")
        print("\n📊 HTML coverage report generated: htmlcov/index.html")
    
    elif command == "fast":
        run_cmd("pytest tests -v -m 'not slow'", "Running fast tests only")
    
    elif command == "watch":
        run_cmd("pytest-watch tests -v", "Running tests in watch mode")
    
    elif command == "quick":
        run_cmd("pytest tests -x -v", "Running tests (stop on first failure)")
    
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
