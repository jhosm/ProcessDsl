#!/bin/bash
#
# Generate C# microservice with ProcessDsl orchestration
# Usage: ./scripts/generate_microservice.sh <openapi-spec.yaml> <output-dir> <package-name>
#
# Example: ./scripts/generate_microservice.sh examples/process_entity_demo.yaml src/microservices/ProcessEntityDemo ProcessEntityDemo
#

set -e

OPENAPI_SPEC=$1
OUTPUT_DIR=$2
PACKAGE_NAME=$3

if [ -z "$OPENAPI_SPEC" ] || [ -z "$OUTPUT_DIR" ] || [ -z "$PACKAGE_NAME" ]; then
    echo "Usage: $0 <openapi-spec.yaml> <output-dir> <package-name>"
    echo "Example: $0 examples/process_entity_demo.yaml src/microservices/ProcessEntityDemo ProcessEntityDemo"
    exit 1
fi

echo "🚀 Generating microservice from $OPENAPI_SPEC..."

# Step 1: Run OpenAPI Generator with custom templates
npx @openapitools/openapi-generator-cli generate \
  -i "$OPENAPI_SPEC" \
  -g aspnetcore \
  -t templates/aspnetcore-processdsl \
  -o "$OUTPUT_DIR" \
  --additional-properties=aspnetCoreVersion=8.0,packageName=$PACKAGE_NAME,operationModifier=virtual,serverPort=5100

# Step 2: Create nuget.config for local package reference
echo "📦 Creating nuget.config..."
cat > "$OUTPUT_DIR/nuget.config" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <!-- Local ProcessDsl.Orchestration package -->
    <add key="local" value="../../packages" />
    <!-- Official NuGet source -->
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
</configuration>
EOF

echo "✅ Microservice generated successfully!"
echo "📍 Location: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Build: dotnet build $OUTPUT_DIR/src/$PACKAGE_NAME/$PACKAGE_NAME.csproj"
echo "  2. Run:   dotnet run --project $OUTPUT_DIR/src/$PACKAGE_NAME/$PACKAGE_NAME.csproj"
echo ""
