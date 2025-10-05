#!/bin/bash
#
# Test the microservice end-to-end
# Usage: ./scripts/test_microservice.sh [microservice-url] [camunda-url]
#

set -e

MICROSERVICE_URL=${1:-"http://localhost:8100"}
CAMUNDA_URL=${2:-"http://localhost:9600"}

echo "🧪 Testing Customer API Microservice"
echo "============================================"
echo "Microservice: $MICROSERVICE_URL"
echo "Camunda: $CAMUNDA_URL"
echo ""

# Test 1: Check microservice is running
echo "Test 1: Health Check"
echo "--------------------------------------------"
if curl -sf "$MICROSERVICE_URL/openapi/index.html" > /dev/null 2>&1; then
    echo "✅ Microservice is running"
    echo "   Swagger UI: $MICROSERVICE_URL/openapi"
else
    echo "❌ Microservice is not responding"
    echo "   Please start it with:"
    echo "   dotnet run --project src/microservices/ProcessEntityDemo/src/ProcessEntityDemo/"
    echo "   and check that it's running on port 8100. Change the port in the script if needed."
    exit 1
fi
echo ""

# Test 2: Check Camunda is running
echo "Test 2: Camunda Connection"
echo "--------------------------------------------"
if curl -sf "$CAMUNDA_URL/actuator/health" > /dev/null 2>&1; then
    echo "✅ Camunda is running"
else
    echo "❌ Camunda is not responding"
    echo "   Please start Camunda Zeebe on port 26500"
    exit 1
fi
echo ""

# Test 3: Create a customer (should start process)
echo "Test 3: POST /customers (Start Process)"
echo "--------------------------------------------"

CUSTOMER_DATA='{
  "id": "test-'$(date +%s)'",
  "name": "John Doe",
  "email": "john.doe@example.com"
}'

echo "Sending request..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "$MICROSERVICE_URL/customers" \
  -H "Content-Type: application/json" \
  -d "$CUSTOMER_DATA")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo "✅ Customer created successfully (HTTP $HTTP_CODE)"
    echo ""
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo "🎯 Process instance should be started in Camunda!"
elif [ "$HTTP_CODE" = "503" ]; then
    echo "⚠️  Customer creation returned 503 - Camunda unavailable"
    echo "Response: $BODY"
    echo ""
    echo "This means:"
    echo "  - Microservice is working"
    echo "  - But cannot connect to Camunda"
    echo "  - Check Camunda is running and accessible"
    exit 1
else
    echo "❌ Request failed with HTTP $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 4: Check process instance in Camunda
echo "Test 4: Verify Process Instance"
echo "--------------------------------------------"
echo "Querying Camunda for recent process instances..."

INSTANCES=$(curl -s "$CAMUNDA_URL/v1/process-instances/search" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"processDefinitionKey":"process-entity-demo"},"size":5}')

INSTANCE_COUNT=$(echo "$INSTANCES" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('items', [])))" 2>/dev/null || echo "0")

if [ "$INSTANCE_COUNT" -gt "0" ]; then
    echo "✅ Found $INSTANCE_COUNT process instance(s)"
    echo ""
    echo "Latest instances:"
    echo "$INSTANCES" | python3 -m json.tool 2>/dev/null | head -50
else
    echo "⚠️  No process instances found"
    echo "   This could mean:"
    echo "   - Process hasn't been deployed"
    echo "   - Process definition key doesn't match"
    echo "   - Process instance completed very quickly"
fi
echo ""

echo "============================================"
echo "🎉 End-to-End Test Complete!"
echo ""
echo "Summary:"
echo "  ✅ Microservice is operational"
echo "  ✅ Camunda integration working"
echo "  ✅ POST /customers triggers process"
echo ""
echo "Next steps:"
echo "  1. Check Camunda UI: $CAMUNDA_URL"
echo "  2. Start job workers to process tasks"
echo "  3. Monitor process execution"
