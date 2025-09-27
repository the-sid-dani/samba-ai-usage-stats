#!/usr/bin/env python3
"""System health check script for AI Usage Analytics Dashboard."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.monitoring import SystemMonitor
from shared.logging_setup import setup_logging


def main():
    """Run comprehensive system health check."""
    logger = setup_logging()
    logger.info("Starting system health check")

    try:
        # Create system monitor
        monitor = SystemMonitor()

        # Run health checks
        health_report = monitor.run_system_health_check()

        # Display results
        print("\n" + "="*60)
        print("AI USAGE ANALYTICS DASHBOARD - HEALTH CHECK")
        print("="*60)
        print()

        # Overall status
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️ ",
            "critical": "❌",
            "unknown": "❓"
        }

        emoji = status_emoji.get(health_report.overall_status.value, "❓")
        print(f"Overall Status: {emoji} {health_report.overall_status.value.upper()}")
        print(f"Components Checked: {health_report.total_checks}")
        print(f"Healthy: {health_report.healthy_checks}")
        print(f"Warnings: {health_report.warning_checks}")
        print(f"Critical: {health_report.critical_checks}")
        print()

        # Component details
        print("Component Status:")
        print("-" * 40)

        for component in health_report.components:
            comp_emoji = status_emoji.get(component.status.value, "❓")
            response_time = f" ({component.response_time_ms:.0f}ms)" if component.response_time_ms else ""
            print(f"{comp_emoji} {component.component:<20} {component.message}{response_time}")

        print()

        # Recommendations
        if health_report.recommendations:
            print("Recommendations:")
            print("-" * 40)
            for rec in health_report.recommendations:
                print(f"• {rec}")
            print()

        # Generate monitoring summary
        summary = monitor.generate_monitoring_summary()
        print("Detailed Monitoring Summary:")
        print("-" * 40)
        print(summary)

        # Exit code based on health status
        if health_report.overall_status == HealthStatus.CRITICAL:
            logger.error("System health check failed with critical issues")
            sys.exit(1)
        elif health_report.overall_status == HealthStatus.WARNING:
            logger.warning("System health check completed with warnings")
            sys.exit(0)
        else:
            logger.info("System health check passed")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Health check script failed: {e}")
        print(f"\n❌ Health check failed: {e}")
        print("\nPlease check:")
        print("- Google Cloud credentials are configured")
        print("- Environment variables are set correctly")
        print("- Required services are accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()