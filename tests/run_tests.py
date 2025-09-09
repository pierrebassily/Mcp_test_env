"""
Test runner for MCP Test Environment
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.framework import MCPTestFramework, TestSuite
from tests.test_integration import (
    create_integration_test_suite,
    create_performance_test_suite,
    create_stress_test_suite,
)
from tests.mocks import MockMCPEnvironment
from config.config import load_config
from utils.logging import setup_logging, get_logger
from utils.metrics import get_metrics_collector


class MCPTestRunner:
    """Main test runner for MCP Test Environment"""

    def __init__(self, config_env: str = "test"):
        self.config = load_config()
        self.config.environment = config_env

        # Setup logging
        setup_logging(self.config.logging)
        self.logger = get_logger(__name__)

        # Initialize components
        self.framework = MCPTestFramework()
        self.metrics = get_metrics_collector()
        self.mock_env = (
            MockMCPEnvironment() if self.config.test.mock_responses else None
        )

        # Test suites
        self.available_suites = {
            "integration": create_integration_test_suite,
            "performance": create_performance_test_suite,
            "stress": create_stress_test_suite,
        }

    async def run_test_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        """Run a specific test suite"""
        if suite_name not in self.available_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")

        self.logger.info(f"Running test suite: {suite_name}")

        # Create test suite
        suite_factory = self.available_suites[suite_name]
        test_suite = suite_factory()

        # Run tests
        results = await self.framework.run_test_suite(test_suite)

        # Log results
        passed = sum(1 for r in results if r.success)
        total = len(results)
        self.logger.info(f"Test suite {suite_name} completed: {passed}/{total} passed")

        return [
            {
                "test_name": r.test_name,
                "success": r.success,
                "duration": r.duration,
                "error": r.error_message,
                "suite": suite_name,
            }
            for r in results
        ]

    async def run_all_suites(self) -> Dict[str, List[Dict[str, Any]]]:
        """Run all available test suites"""
        all_results = {}

        for suite_name in self.available_suites:
            try:
                results = await self.run_test_suite(suite_name)
                all_results[suite_name] = results
            except Exception as e:
                self.logger.error(f"Failed to run test suite {suite_name}: {e}")
                all_results[suite_name] = []

        return all_results

    async def run_with_mocks(
        self, suite_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Run tests with mock environment"""
        if not self.mock_env:
            self.logger.warning("Mock environment not enabled")
            return {}

        results = {}

        try:
            # Start mock environment
            await self.mock_env.start()
            self.logger.info("Mock environment started")

            # Run specified test suites
            for suite_name in suite_names:
                if suite_name in self.available_suites:
                    suite_results = await self.run_test_suite(suite_name)
                    results[suite_name] = suite_results
                else:
                    self.logger.warning(f"Unknown test suite: {suite_name}")

            # Get mock environment stats
            mock_stats = self.mock_env.get_stats()
            self.logger.info(f"Mock environment stats: {mock_stats}")

        finally:
            # Stop mock environment
            await self.mock_env.stop()
            self.logger.info("Mock environment stopped")

        return results

    def generate_comprehensive_report(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        output_dir: str = "./test_reports",
    ):
        """Generate comprehensive test report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate main report
        report_file = output_path / f"mcp_test_report_{timestamp}.json"
        self.framework.generate_test_report(str(report_file))

        # Generate metrics export
        metrics_file = output_path / f"mcp_metrics_{timestamp}.json"
        self.metrics.export_metrics(str(metrics_file))

        # Generate summary report
        summary_file = output_path / f"mcp_summary_{timestamp}.txt"
        self._generate_text_summary(results, summary_file)

        self.logger.info(f"Reports generated in {output_path}")
        return {
            "report_file": str(report_file),
            "metrics_file": str(metrics_file),
            "summary_file": str(summary_file),
        }

    def _generate_text_summary(
        self, results: Dict[str, List[Dict[str, Any]]], output_file: Path
    ):
        """Generate text summary report"""
        total_tests = 0
        total_passed = 0
        total_duration = 0.0

        with open(output_file, "w") as f:
            f.write("MCP Test Environment - Test Summary Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Environment: {self.config.environment}\n\n")

            for suite_name, suite_results in results.items():
                f.write(f"Test Suite: {suite_name}\n")
                f.write("-" * 30 + "\n")

                if not suite_results:
                    f.write("No tests run\n\n")
                    continue

                suite_passed = sum(1 for r in suite_results if r["success"])
                suite_total = len(suite_results)
                suite_duration = sum(r["duration"] for r in suite_results)

                f.write(f"Tests: {suite_passed}/{suite_total} passed\n")
                f.write(f"Duration: {suite_duration:.3f}s\n")
                f.write(f"Success Rate: {suite_passed/suite_total*100:.1f}%\n\n")

                # List failed tests
                failed_tests = [r for r in suite_results if not r["success"]]
                if failed_tests:
                    f.write("Failed Tests:\n")
                    for test in failed_tests:
                        f.write(f"  - {test['test_name']}: {test['error']}\n")
                    f.write("\n")

                total_tests += suite_total
                total_passed += suite_passed
                total_duration += suite_duration

            # Overall summary
            f.write("Overall Summary\n")
            f.write("=" * 30 + "\n")
            f.write(f"Total Tests: {total_passed}/{total_tests} passed\n")
            f.write(f"Total Duration: {total_duration:.3f}s\n")
            if total_tests > 0:
                f.write(f"Overall Success Rate: {total_passed/total_tests*100:.1f}%\n")

        self.logger.info(f"Text summary generated: {output_file}")


async def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description="MCP Test Environment Runner")
    parser.add_argument(
        "--suite",
        choices=["integration", "performance", "stress", "all"],
        default="all",
        help="Test suite to run",
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock environment for testing"
    )
    parser.add_argument(
        "--output-dir",
        default="./test_reports",
        help="Output directory for test reports",
    )
    parser.add_argument(
        "--config-env", default="test", help="Configuration environment"
    )

    args = parser.parse_args()

    # Create test runner
    runner = MCPTestRunner(config_env=args.config_env)

    try:
        # Run tests
        if args.mock:
            # Run with mock environment
            if args.suite == "all":
                suites = list(runner.available_suites.keys())
            else:
                suites = [args.suite]

            results = await runner.run_with_mocks(suites)
        else:
            # Run without mocks
            if args.suite == "all":
                results = await runner.run_all_suites()
            else:
                suite_results = await runner.run_test_suite(args.suite)
                results = {args.suite: suite_results}

        # Generate reports
        report_files = runner.generate_comprehensive_report(results, args.output_dir)

        # Print summary
        total_tests = sum(len(suite_results) for suite_results in results.values())
        total_passed = sum(
            sum(1 for r in suite_results if r["success"])
            for suite_results in results.values()
        )

        print(f"\nTest run completed!")
        print(f"Total tests: {total_passed}/{total_tests} passed")
        print(f"Reports generated in: {args.output_dir}")

        # Exit with appropriate code
        sys.exit(0 if total_passed == total_tests else 1)

    except Exception as e:
        runner.logger.error(f"Test run failed: {e}")
        sys.exit(1)

    finally:
        # Cleanup
        runner.framework.cleanup_test_environment()


if __name__ == "__main__":
    asyncio.run(main())
