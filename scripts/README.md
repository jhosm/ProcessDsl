# ProcessDsl Scripts

Automation scripts for ProcessDsl microservices generation and management.

## Scripts

### deploy_to_camunda.sh

Deploys BPMN processes to Camunda 8 Zeebe using the gRPC protocol via `zbctl`.

**Purpose:**
- Deploy BPMN files to local or cloud Zeebe instances
- Uses gRPC (Camunda 8 compatible)
- Supports both local development and Camunda Cloud

**Prerequisites:**
```bash
# Install zbctl
# macOS
brew install camunda/camunda/zbctl

# Or via npm
npm install -g zbctl

# Or download binary from https://github.com/camunda/zeebe/releases
```

**Usage:**
```bash
# Deploy to local Zeebe (default: localhost:26500)
./scripts/deploy_to_camunda.sh examples/process_entity_demo.bpmn

# Deploy to custom local address
./scripts/deploy_to_camunda.sh examples/process_entity_demo.bpmn localhost:26500

# Deploy to Camunda Cloud
export ZEEBE_ADDRESS='your-cluster.zeebe.camunda.io:443'
export ZEEBE_CLIENT_ID='your-client-id'
export ZEEBE_CLIENT_SECRET='your-client-secret'
export ZEEBE_AUTHORIZATION_SERVER_URL='https://login.cloud.camunda.io/oauth/token'
./scripts/deploy_to_camunda.sh examples/process_entity_demo.bpmn
```

**Features:**
- ✅ Camunda 8 (Zeebe gRPC) compatible
- ✅ Automatic zbctl installation check
- ✅ Supports local and cloud deployments
- ✅ Clear error messages and troubleshooting tips

---

### extract_process_metadata.py

Extracts process metadata from `.bpm` files to generate `process-mappings.json`.

**Purpose:**
- Parse all `.bpm` files in a directory
- Extract process ID, entity name, and paired OpenAPI file
- Generate JSON mapping file for runtime process discovery

**Usage:**
```bash
# Extract from examples directory (default)
python3 scripts/extract_process_metadata.py

# Extract from custom directory
python3 scripts/extract_process_metadata.py path/to/bpm/files

# Specify custom output file
python3 scripts/extract_process_metadata.py examples/ output/mappings.json
```

**Output Format (process-mappings.json):**
```json
{
  "process-entity-demo": {
    "processId": "process-entity-demo",
    "processName": "Process Entity Demo",
    "entityName": "Customer",
    "bpmFile": "examples/process_entity_demo.bpm",
    "yamlFile": "examples/process_entity_demo.yaml",
    "postEndpoint": "/customers",
    "version": "1.0"
  }
}
```

**Requirements:**
- Each `.bpm` file must have a paired `.yaml` or `.yml` file
- Process must contain a `processEntity` element
- OpenAPI spec must define at least one POST endpoint

**Example Workflow:**
```bash
# 1. Create your .bpm file
cat > examples/my_process.bpm <<EOF
process "My Process" {
    id: "my-process"
    version: "1.0"
    
    start "Start" {}
    
    processEntity "Load Data" {
        entityName: "Customer"
    }
    
    end "End" {}
    
    flow {
        "start" -> "load-data"
        "load-data" -> "end"
    }
}
EOF

# 2. Create paired OpenAPI spec
cat > examples/my_process.yaml <<EOF
openapi: 3.0.3
info:
  title: My API
  version: 1.0.0
components:
  schemas:
    Customer:
      type: object
      properties:
        id:
          type: string
paths:
  /customers:
    post:
      requestBody:
        content:
          application/json:
            schema:
              \$ref: '#/components/schemas/Customer'
      responses:
        '201':
          description: Created
EOF

# 3. Extract metadata
python3 scripts/extract_process_metadata.py examples/

# 4. View generated mappings
cat src/microservices/process-mappings.json
```

## Future Scripts

### generate_microservice.py (Coming Soon)
Generates a complete microservice from a `.bpm`/`.yaml` pair:
- Runs OpenAPI Generator
- Creates custom controllers with ProcessDsl.Orchestration integration
- Generates `appsettings.json` with Camunda configuration
- Creates `process-metadata.json` for the service

**Planned Usage:**
```bash
python3 scripts/generate_microservice.py examples/process_entity_demo.bpm
```

### generate_all_microservices.py (Coming Soon)
Batch generates all microservices from a directory:
```bash
python3 scripts/generate_all_microservices.py examples/
```

## Development

### Adding a New Script

1. Create the script in `scripts/`
2. Add shebang: `#!/usr/bin/env python3`
3. Make executable: `chmod +x scripts/your_script.py`
4. Add to this README
5. Update main README with usage examples

### Testing Scripts

```bash
# Test metadata extraction
python3 scripts/extract_process_metadata.py examples/

# Verify output
cat src/microservices/process-mappings.json | python3 -m json.tool
```

## Dependencies

Scripts require Python dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `lark-parser` - DSL parsing
- `PyYAML` - OpenAPI file parsing
- `click` - CLI framework (future scripts)
