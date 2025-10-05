#!/bin/bash
#
# Deploy BPMN process to Camunda Zeebe using zbctl (gRPC)
# Usage: ./scripts/deploy_to_camunda.sh <bpmn-file> [zeebe-address]
#
# Prerequisites:
# - zbctl must be installed (https://docs.camunda.io/docs/apis-tools/cli-client/)
# - For local: zbctl is available in PATH
# - For cloud: Set ZEEBE_ADDRESS, ZEEBE_CLIENT_ID, ZEEBE_CLIENT_SECRET, ZEEBE_AUTHORIZATION_SERVER_URL
#

set -e

BPMN_FILE=$1
ZEEBE_ADDRESS=${2:-"localhost:26500"}

if [ -z "$BPMN_FILE" ]; then
    echo "Usage: $0 <bpmn-file> [zeebe-address]"
    echo "Example: $0 examples/process_entity_demo.bpmn"
    echo ""
    echo "For local Zeebe (default):"
    echo "  $0 examples/process_entity_demo.bpmn"
    echo ""
    echo "For Camunda Cloud:"
    echo "  export ZEEBE_ADDRESS='your-cluster.zeebe.camunda.io:443'"
    echo "  export ZEEBE_CLIENT_ID='your-client-id'"
    echo "  export ZEEBE_CLIENT_SECRET='your-client-secret'"
    echo "  export ZEEBE_AUTHORIZATION_SERVER_URL='https://login.cloud.camunda.io/oauth/token'"
    echo "  $0 examples/process_entity_demo.bpmn"
    exit 1
fi

if [ ! -f "$BPMN_FILE" ]; then
    echo "❌ Error: BPMN file not found: $BPMN_FILE"
    exit 1
fi

# Check if zbctl is installed
if ! command -v zbctl &> /dev/null; then
    echo "❌ Error: zbctl is not installed"
    echo ""
    echo "Install zbctl:"
    echo "  macOS: brew install camunda/camunda/zbctl"
    echo "  Linux: Download from https://github.com/camunda/zeebe/releases"
    echo "  Or use npm: npm install -g zbctl"
    exit 1
fi

PROCESS_ID=$(grep -o '<process id="[^"]*"' "$BPMN_FILE" | head -2 | tail -1 | cut -d'"' -f2)

echo "📦 Deploying BPMN process to Camunda Zeebe (gRPC)..."
echo "   File: $BPMN_FILE"
echo "   Process ID: $PROCESS_ID"
echo "   Zeebe Address: ${ZEEBE_ADDRESS}"
echo ""

# Set address if not using environment variable
if [ -z "$ZEEBE_ADDRESS" ]; then
    export ZEEBE_ADDRESS="$ZEEBE_ADDRESS"
fi

# Deploy using zbctl (gRPC)
if zbctl deploy "$BPMN_FILE" --address "$ZEEBE_ADDRESS" --insecure 2>&1; then
    echo ""
    echo "✅ Process deployed successfully!"
    echo ""
    echo "🎯 Process is now available in Camunda Zeebe"
    echo "   Process ID: $PROCESS_ID"
    echo "   You can now start instances via gRPC client or microservice"
else
    echo "❌ Deployment failed"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if Zeebe is running: docker ps | grep zeebe"
    echo "2. Verify address: $ZEEBE_ADDRESS"
    echo "3. For cloud: ensure environment variables are set (ZEEBE_CLIENT_ID, etc.)"
    exit 1
fi
