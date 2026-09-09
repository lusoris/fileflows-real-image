#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${TEST_IMAGE:-revenz/fileflows:optimized}"
echo "==> Running FileFlows Real Image assertion test suite against: ${IMAGE_NAME}"

# Ensure python3 and pytest are installed
if ! command -v pytest >/dev/null 2>&1; then
    echo "Installing test dependencies..."
    pip install -r "$(dirname "$0")/requirements-test.txt"
fi

echo "==> Executing pytest suite..."
pytest "$(dirname "$0")/test_image.py" -v --tb=short

echo "==> All image assertion tests passed successfully!"
