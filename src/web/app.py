"""Flask web application for AI Usage Analytics Dashboard.

Provides HTTP endpoints for health checks, pipeline execution, and monitoring.
Designed for Cloud Run deployment with proper authentication and monitoring.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any

from flask import Flask, request, jsonify, Response
from werkzeug.exceptions import BadRequest

from ..orchestration.daily_job import DailyJobOrchestrator, ExecutionMode
from ..shared.config import config
from ..shared.logging_setup import get_logger
from ..shared.monitoring import SystemMonitor
from ..shared.cloud_monitoring import get_cloud_monitoring

# Initialize logger
logger = get_logger("web_app")

# Initialize Flask app
app = Flask(__name__)

# Global orchestrator instance
orchestrator = None
system_monitor = None


def create_app() -> Flask:
    """Create and configure Flask application for Cloud Run."""
    global orchestrator, system_monitor

    logger.info("Initializing AI Usage Analytics Web Application")

    # Initialize system components
    try:
        orchestrator = DailyJobOrchestrator()
        system_monitor = SystemMonitor()
        logger.info("Application components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application components: {e}")
        # Continue with limited functionality

    return app


@app.route("/health", methods=["GET"])
def health_check():
    """
    Comprehensive health check endpoint for Cloud Run.

    Returns:
        JSON response with health status and component details
    """
    start_time = time.time()

    try:
        # Basic application health
        app_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ai-usage-analytics-pipeline",
            "version": os.getenv("APP_VERSION", "unknown"),
            "environment": os.getenv("ENVIRONMENT", "development")
        }

        # Component health checks
        components = {}
        overall_healthy = True

        # Pipeline orchestrator health
        if orchestrator:
            try:
                pipeline_health = orchestrator.health_check()
                components["pipeline"] = pipeline_health
                if pipeline_health.get("overall_status") != "healthy":
                    overall_healthy = False
            except Exception as e:
                components["pipeline"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_healthy = False
        else:
            components["pipeline"] = {
                "status": "unhealthy",
                "error": "Pipeline orchestrator not initialized"
            }
            overall_healthy = False

        # System monitor health
        if system_monitor:
            try:
                system_health = system_monitor.run_system_health_check()
                components["system"] = {
                    "status": system_health.overall_status.value,
                    "total_checks": system_health.total_checks,
                    "healthy_checks": system_health.healthy_checks,
                    "warning_checks": system_health.warning_checks,
                    "critical_checks": system_health.critical_checks
                }
                if system_health.overall_status.value != "healthy":
                    overall_healthy = False
            except Exception as e:
                components["system"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_healthy = False

        # Update overall status
        app_status["status"] = "healthy" if overall_healthy else "unhealthy"
        app_status["components"] = components
        app_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

        # HTTP status code
        status_code = 200 if overall_healthy else 503

        # Log health check result
        logger.info(f"Health check completed: {app_status['status']}", extra={
            "status": app_status["status"],
            "components_count": len(components),
            "response_time_ms": app_status["response_time_ms"]
        })

        return jsonify(app_status), status_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
        return jsonify(error_response), 500


@app.route("/ready", methods=["GET"])
def readiness_check():
    """
    Kubernetes/Cloud Run readiness probe endpoint.

    Returns:
        Simple OK response when service is ready to accept traffic
    """
    try:
        # Basic readiness checks
        ready = True
        issues = []

        # Check if orchestrator is initialized
        if not orchestrator:
            ready = False
            issues.append("Pipeline orchestrator not initialized")

        # Check environment configuration
        required_env_vars = ["GOOGLE_CLOUD_PROJECT"]
        for var in required_env_vars:
            if not os.getenv(var):
                ready = False
                issues.append(f"Missing required environment variable: {var}")

        if ready:
            return Response("OK", status=200, mimetype="text/plain")
        else:
            logger.warning(f"Service not ready: {issues}")
            return Response(f"NOT READY: {'; '.join(issues)}", status=503, mimetype="text/plain")

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return Response(f"ERROR: {str(e)}", status=500, mimetype="text/plain")


@app.route("/liveness", methods=["GET"])
def liveness_check():
    """
    Kubernetes/Cloud Run liveness probe endpoint.

    Returns:
        Simple OK response when service is alive
    """
    try:
        # Basic liveness check - just verify app is responding
        return Response("OK", status=200, mimetype="text/plain")
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return Response(f"ERROR: {str(e)}", status=500, mimetype="text/plain")


@app.route("/run-daily-job", methods=["POST"])
def run_daily_job():
    """
    Execute the daily data pipeline job.

    Request body (JSON):
        - mode: execution mode (production, development, dry_run)
        - days: number of days to process (default: 1)
        - force: force execution even if already run today

    Returns:
        JSON response with execution results
    """
    start_time = time.time()

    try:
        # Verify orchestrator is available
        if not orchestrator:
            return jsonify({
                "status": "error",
                "message": "Pipeline orchestrator not initialized"
            }), 500

        # Parse request
        data = request.get_json() or {}

        # Execution parameters
        mode_str = data.get("mode", "production")
        days = data.get("days", 1)
        force = data.get("force", False)

        # Validate mode
        try:
            mode = ExecutionMode(mode_str)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": f"Invalid execution mode: {mode_str}. Valid modes: {[m.value for m in ExecutionMode]}"
            }), 400

        # Validate days
        if not isinstance(days, int) or days < 1 or days > 30:
            return jsonify({
                "status": "error",
                "message": "Days must be an integer between 1 and 30"
            }), 400

        logger.info(f"Starting daily job execution: mode={mode_str}, days={days}, force={force}")

        # Execute pipeline
        try:
            result = orchestrator.run_daily_pipeline(mode=mode, days_back=days, force_execution=force)

            # Prepare response
            response = {
                "status": "success" if result.success else "failure",
                "execution_id": result.execution_id,
                "mode": mode_str,
                "days_processed": days,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "metrics": {
                    "cursor_records": result.cursor_records,
                    "anthropic_records": result.anthropic_records,
                    "storage_operations": result.storage_operations,
                    "errors": len(result.errors)
                }
            }

            # Add error details if any
            if result.errors:
                response["errors"] = [
                    {
                        "component": error.component,
                        "error_code": error.error_code,
                        "message": error.message,
                        "recoverable": error.recoverable
                    }
                    for error in result.errors
                ]

            # Add success details
            if result.success:
                response["message"] = f"Pipeline executed successfully for {days} day(s)"
                logger.info(f"Daily job completed successfully: {result.execution_id}")
            else:
                response["message"] = f"Pipeline execution failed with {len(result.errors)} error(s)"
                logger.error(f"Daily job failed: {result.execution_id}")

            status_code = 200 if result.success else 500
            return jsonify(response), status_code

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return jsonify({
                "status": "error",
                "message": f"Pipeline execution failed: {str(e)}",
                "execution_time_ms": round((time.time() - start_time) * 1000, 2)
            }), 500

    except BadRequest as e:
        logger.warning(f"Invalid request: {e}")
        return jsonify({
            "status": "error",
            "message": "Invalid JSON request body"
        }), 400

    except Exception as e:
        logger.error(f"Daily job endpoint failed: {e}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "execution_time_ms": round((time.time() - start_time) * 1000, 2)
        }), 500


@app.route("/status", methods=["GET"])
def get_status():
    """
    Get current pipeline status and recent execution history.

    Returns:
        JSON response with pipeline status information
    """
    try:
        if not system_monitor:
            return jsonify({
                "status": "error",
                "message": "System monitor not initialized"
            }), 500

        # Get system status
        status_info = system_monitor.get_status_summary()

        # Add timestamp and service info
        response = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ai-usage-analytics-pipeline",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "status": status_info
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Status endpoint failed: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get status: {str(e)}"
        }), 500


@app.route("/metrics", methods=["GET"])
def get_metrics():
    """
    Get pipeline metrics in Prometheus format (if monitoring is configured).

    Returns:
        Metrics in Prometheus text format or JSON
    """
    try:
        # This would integrate with your monitoring system
        # For now, return basic metrics

        response = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "app_info": {
                    "service": "ai-usage-analytics-pipeline",
                    "version": os.getenv("APP_VERSION", "unknown"),
                    "environment": os.getenv("ENVIRONMENT", "development")
                },
                "runtime": {
                    "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else 0
                }
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get metrics: {str(e)}"
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": [
            "GET /health - Health check",
            "GET /ready - Readiness check",
            "GET /liveness - Liveness check",
            "POST /run-daily-job - Execute pipeline",
            "GET /status - Pipeline status",
            "GET /metrics - Service metrics"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500


if __name__ == "__main__":
    # Record start time
    app.start_time = time.time()

    # Create application
    app = create_app()

    # Development server (not used in production)
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting development server on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)