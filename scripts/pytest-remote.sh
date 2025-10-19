#!/bin/bash

# =================================================================
# Variables
# ENGINE_NAME, PYTHON_VERSION, OS_NAME - are now MANDATORY
# =================================================================
ENGINE_NAME=""
PYTHON_VERSION=""
OS_NAME=""
STRESS_TEST_FLAG="false" # Optional, defaults to false
WORKFLOW_NAME="Manual Test Runner"

# =================================================================
# Help Function (Usage function)
# =================================================================
usage() {
    echo "Usage: $0 --engine <ENGINE_NAME> -p <PYTHON_VERSION> -o <OS_NAME> [--stress]"
    echo ""
    echo "Required arguments:"
    echo "  --engine  Engine name (e.g., rk4_engine)."
    echo "  -p        Python version (e.g., 3.12, 3.14t)."
    echo "  -o        Operating system (e.g., ubuntu-latest, macos-15)."
    echo ""
    echo "Optional arguments:"
    echo "  --stress  Flag to enable stress tests (will be set to true)."
    exit 1
}

# =================================================================
# Argument Parsing
# =================================================================
# Define short and long options
OPTS=$(getopt -o p:o: --long engine:,stress -- "$@")

if [ $? -ne 0 ]; then
    echo "Error processing arguments." >&2
    usage
fi

eval set -- "$OPTS"

while true; do
    case "$1" in
        --engine)
            ENGINE_NAME="$2"
            shift 2
            ;;
        -p)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -o)
            OS_NAME="$2"
            shift 2
            ;;
        --stress)
            STRESS_TEST_FLAG="true"
            shift 1
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

# =================================================================
# Mandatory Argument Check
# =================================================================
if [ -z "$ENGINE_NAME" ] || [ -z "$PYTHON_VERSION" ] || [ -z "$OS_NAME" ]; then
    echo "Error: Missing required arguments. --engine, -p, and -o are mandatory." >&2
    usage
fi

# =================================================================
# Execution
# =================================================================

# 1. Get current Git branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" = "HEAD" ]; then
    echo "Error: You are in a 'detached HEAD' state. Please check out a branch." >&2
    exit 1
fi

echo "--- Test Configuration ---"
echo "Branch: $CURRENT_BRANCH"
echo "OS: $OS_NAME"
echo "Python: $PYTHON_VERSION"
echo "Engine: $ENGINE_NAME"
echo "Stress Test: $STRESS_TEST_FLAG"
echo "--------------------------"
echo ""

# 2. Execute the gh-cli command
gh workflow run "$WORKFLOW_NAME" \
  --ref "$CURRENT_BRANCH" \
  -f os="$OS_NAME" \
  -f python_version="$PYTHON_VERSION" \
  -f engine_name="$ENGINE_NAME" \
  -f stress_test="$STRESS_TEST_FLAG"

# Check gh-cli exit status
if [ $? -eq 0 ]; then
    echo "✅ Workflow successfully triggered!"
else
    echo "❌ Error triggering workflow."
fi