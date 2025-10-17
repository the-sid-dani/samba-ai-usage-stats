#!/usr/bin/env python3
"""Simple test web server for Cloud Run deployment validation."""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "ai-usage-analytics-pipeline",
        "version": "test",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    })

@app.route("/ready")
def ready():
    return "OK"

@app.route("/")
def root():
    return jsonify({
        "message": "AI Usage Analytics Pipeline",
        "status": "running",
        "endpoints": ["/health", "/ready"]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)