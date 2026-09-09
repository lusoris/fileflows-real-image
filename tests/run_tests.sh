#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${TEST_IMAGE:-ghcr.io/lusoris/fileflows-real-image:latest}"
echo "==> Running FileFlows Real Image assertion test suite against: ${IMAGE_NAME}"

# Ensure python3 and pytest are installed
if ! command -v pytest >/dev/null 2>&1; then
    echo "Installing test dependencies..."
    pip install -r "$(dirname "$0")/requirements-test.txt"
fi

echo "==> Executing pytest test suite..."
pytest "$(dirname "$0")" -v --tb=short

echo "==> All image assertion and documentation consistency tests passed successfully!"
