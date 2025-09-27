#!/usr/bin/env python3
"""Setup script for alert policies and notification channels."""

import sys
import os
import json
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.shared.alert_manager import alert_manager
from src.shared.logging_setup import setup_logging, RequestContextLogger

def main():
    """Main setup function for alerts."""
    # Setup logging
    setup_logging()
    context_logger = RequestContextLogger("alert_setup", operation="setup_monitoring_alerts")

    context_logger.info("Starting alert policies and notification channels setup")

    try:
        # Setup all alerts
        results = alert_manager.setup_all_alerts()

        if results["success"]:
            context_logger.log_operation_complete(
                "setup_monitoring_alerts",
                channels_created=len(results["notification_channels"]),
                policies_created=len(results["alert_policies"])
            )

            print("\n✅ Alert setup completed successfully!")
            print(f"📧 Notification channels created: {len(results['notification_channels'])}")
            print(f"🚨 Alert policies created: {len(results['alert_policies'])}")

            # Display created resources
            if results["notification_channels"]:
                print("\n📧 Notification Channels:")
                for name, channel_id in results["notification_channels"].items():
                    print(f"  - {name}: {channel_id}")

            if results["alert_policies"]:
                print("\n🚨 Alert Policies:")
                for name, policy_id in results["alert_policies"].items():
                    print(f"  - {name}: {policy_id}")

        else:
            context_logger.log_operation_error(
                "setup_monitoring_alerts",
                error=Exception(f"Setup failed with errors: {results['errors']}")
            )

            print("\n❌ Alert setup failed!")
            for error in results["errors"]:
                print(f"  Error: {error}")

            return 1

    except Exception as e:
        context_logger.log_operation_error("setup_monitoring_alerts", error=e)
        print(f"\n❌ Alert setup failed with exception: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)