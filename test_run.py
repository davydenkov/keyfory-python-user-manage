#!/usr/bin/env python3
"""
Test runner script for User Management API.

Provides convenient commands to run different types of tests with appropriate
configurations and reporting.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """Run a command and return the exit code."""
    print(f"\n🧪 {description}")
    print(f"📋 Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Test run interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return 1


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for User Management API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_run.py                    # Run all available tests
  python test_run.py --basic           # Run basic unit tests (no deps)
  python test_run.py --api             # Run API tests only
  python test_run.py --unit            # Run unit tests only
  python test_run.py --integration     # Run integration tests
  python test_run.py --performance     # Run performance tests
  python test_run.py --coverage        # Run with coverage report
  python test_run.py --verbose         # Run with verbose output
        """
    )

    parser.add_argument(
        "--basic",
        action="store_true",
        help="Run basic tests that don't require external dependencies"
    )

    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="Run API tests only"
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )

    parser.add_argument(
        "--validation",
        action="store_true",
        help="Run validation tests only"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests only"
    )

    parser.add_argument(
        "--middleware",
        action="store_true",
        help="Run middleware tests only"
    )

    parser.add_argument(
        "--models",
        action="store_true",
        help="Run model tests only"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run mock-based tests only"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report (requires dependencies)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )

    parser.add_argument(
        "--no-slow",
        action="store_true",
        help="Skip slow tests"
    )

    args = parser.parse_args()

    # Check if dependencies are available
    try:
        import litestar
        dependencies_available = True
    except ImportError:
        dependencies_available = False

    if args.basic:
        # Run basic tests directly without pytest
        return run_basic_tests()
    elif not dependencies_available and not args.mock:
        print("⚠️  External dependencies not available.")
        print("💡 Try running with --basic for tests that don't require dependencies,")
        print("   or --mock for mock-based tests.")
        return 1

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add specific test files/markers based on arguments
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.api:
        cmd.extend(["-m", "api"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.validation:
        cmd.extend(["-m", "validation"])
    elif args.performance:
        cmd.extend(["-m", "performance"])
    elif args.middleware:
        cmd.extend(["-m", "middleware"])
    elif args.models:
        cmd.extend(["-m", "models"])
    elif args.mock:
        cmd.extend(["-m", "mock"])
    else:
        # Default: run all available tests
        if dependencies_available:
            cmd.extend(["-m", "not slow"])
        else:
            # Run mock tests if no dependencies
            cmd.extend(["-m", "mock"])

    # Add coverage if requested (only works with dependencies)
    if args.coverage:
        if not dependencies_available:
            print("⚠️  Coverage requires dependencies to be installed.")
            return 1
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80"
        ])

    # Add verbose output
    if args.verbose:
        cmd.append("-v")

    # Add fail fast
    if args.fail_fast:
        cmd.append("--tb=short")

    # Skip slow tests
    if args.no_slow:
        cmd.extend(["-m", "not slow"])

    # Run the tests
    description = "Running tests"
    if args.basic:
        description = "Running basic unit tests"
    elif args.unit:
        description = "Running unit tests"
    elif args.api:
        description = "Running API tests"
    elif args.integration:
        description = "Running integration tests"
    elif args.validation:
        description = "Running validation tests"
    elif args.performance:
        description = "Running performance tests"
    elif args.middleware:
        description = "Running middleware tests"
    elif args.models:
        description = "Running model tests"
    elif args.mock:
        description = "Running mock-based tests"

    exit_code = run_command(cmd, description)

    # Print summary
    print("\n" + "="*60)
    if exit_code == 0:
        print("✅ All tests passed!")
        if args.coverage and dependencies_available:
            print("📊 Coverage report available in: htmlcov/index.html")
        if not dependencies_available:
            print("📝 Note: Running in mock mode (dependencies not available)")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        if not dependencies_available:
            print("💡 Tip: Try --basic for tests that don't require dependencies")
    print("="*60)

    return exit_code


def run_basic_tests():
    """Run basic tests that don't require external dependencies."""
    import sys
    import inspect

    print("🧪 Running basic unit tests (no external dependencies required)")
    print("-" * 50)

    # Import and run basic tests
    try:
        import tests.test_basic
        import tests.test_api_mock
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        return 1

    test_modules = [tests.test_basic, tests.test_api_mock]
    total_passed = 0
    total_failed = 0

    for module in test_modules:
        module_name = module.__name__.split('.')[-1]
        print(f"\n📋 Running {module_name}...")

        # Get all test functions and test class methods
        test_items = []

        # Get standalone test functions
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and name.startswith('test_'):
                test_items.append((name, obj, None))

        # Get test methods from test classes
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.startswith('Test'):
                for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if method_name.startswith('test_'):
                        test_items.append((f"{name}.{method_name}", method_obj, obj))

        passed = 0
        failed = 0

        for test_name, test_func, test_class in test_items:
            try:
                print(f"  Running {test_name}...", end=' ')
                if test_class:
                    # Instantiate the test class and call the method
                    instance = test_class()
                    test_func(instance)
                else:
                    # Call the standalone function
                    test_func()
                print("PASSED")
                passed += 1
                total_passed += 1
            except Exception as e:
                print(f"FAILED: {e}")
                failed += 1
                total_failed += 1

        print(f"  {module_name}: {passed} passed, {failed} failed")

    print("\n📊 Basic Test Results:")
    print(f"  ✅ Passed: {total_passed}")
    print(f"  ❌ Failed: {total_failed}")
    if (total_passed + total_failed) > 0:
        success_rate = (total_passed / (total_passed + total_failed) * 100)
        print(f"  📈 Success Rate: {success_rate:.1f}%")
    else:
        print("  📈 Success Rate: No tests run")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
