# BPM DSL - Complete Process Automation Platform

A comprehensive platform for defining, generating, and executing business processes with Camunda Zeebe. Combines a powerful text-based DSL with automatic microservice generation from OpenAPI specifications.

## Features

### Core DSL Features
- **🎯 Simple Text-based Syntax**: Write business processes in a clean, readable format
- **🔧 Essential BPM Primitives**: Focus on core elements (start, end, xor gateway, scriptCall, serviceTask, processEntity)
- **⚡ Full Zeebe Compatibility**: Generates BPMN XML with proper FEEL expressions and Zeebe extensions
- **🎨 Professional Layout Engine**: Automatic diagram positioning with intelligent gateway handling
- **✅ Comprehensive Validation**: Built-in process validation with detailed error reporting
- **💻 CLI Interface**: Complete command-line tools for conversion, validation, and analysis
- **🔄 Variable Mapping**: Advanced input/output mappings with custom result variables

### Microservices Architecture (NEW)
- **🚀 Automatic API Generation**: Generate C# ASP.NET Core microservices from OpenAPI specifications
- **📦 NuGet Orchestration Package**: Reusable `ProcessDsl.Orchestration` library for Camunda integration
- **🔗 Seamless Process Triggering**: REST API endpoints automatically start Camunda process instances
- **🏗️ API-First Design**: Each process paired with OpenAPI spec ensures contract-driven development
- **🧪 Fully Tested**: Comprehensive unit tests with 27 passing tests for orchestration layer

## Supported Primitives

- **Start Event**: Process entry points with configurable properties
- **End Event**: Process termination points with multiple outcomes
- **Script Call**: Execute JavaScript/FEEL expressions with advanced variable I/O mapping
- **Service Task**: External job workers with headers and retries
- **Process Entity**: Entity validation with OpenAPI schemas
- **XOR Gateway**: Exclusive decision points with conditional routing

## Important Requirements

**⚠️ OpenAPI Specification Required**: Every `.bpm` file **must** have a corresponding OpenAPI specification file (`.yaml` or `.yml`) with the same base name in the same directory. This ensures API-first design and enables entity validation.

See **[OPENAPI_VALIDATION.md](OPENAPI_VALIDATION.md)** for detailed requirements and examples.

## Quick Start (5 Minutes)

Get from DSL to running microservice in 5 commands!

### 1. Create Process Definition + OpenAPI Spec

**Create `customer_process.bpm`:**
```bpm
process "Customer Onboarding" {
    id: "customer-onboarding"
    version: "1.0"
    
    start "Start Onboarding" {
    }
    
    processEntity "Validate Customer" {
        entityName: "Customer"
    }
    
    end "Complete" {
    }
    
    flow {
        "start-onboarding" -> "validate-customer"
        "validate-customer" -> "complete"
    }
}
```

**Create `customer_process.yaml`** (required):
```yaml
openapi: 3.0.3
info:
  title: Customer API
  version: 1.0.0

components:
  schemas:
    Customer:
      type: object
      required: [id, name, email]
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
          format: email

paths:
  /customers:
    post:
      operationId: customersPost
      x-process-id: customer-onboarding  # Links to process
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Customer'
      responses:
        '201':
          description: Customer created
```

### 2. Generate Microservice (100% Automated)

```bash
./scripts/generate_microservice.sh \
  customer_process.yaml \
  src/microservices/CustomerAPI \
  CustomerAPI
```

**Generated automatically:**
- ✅ ASP.NET Core microservice
- ✅ Camunda orchestration integration  
- ✅ Error handling (503/500)
- ✅ Swagger UI

### 3. Generate & Deploy BPMN

```bash
# Generate BPMN from DSL
PYTHONPATH=src python3 -m bpm_dsl.cli convert examples/customer_process/customer_process.bpm \
  --output examples/customer_process/customer_process.bpmn

# Start Camunda Zeebe (if not already running)
# Hint: Install locally from https://camunda.com/download/

# Deploy process
./scripts/deploy_to_camunda.sh examples/customer_process/customer_process.bpmn
```

### 4. Run & Test

```bash
# Run microservice
dotnet run --project src/microservices/CustomerAPI/src/CustomerAPI/

# Test in another terminal
./scripts/test_microservice.sh

# Or manually:
curl -X POST http://localhost:5100/customers \
  -H "Content-Type: application/json" \
  -d '{"id":"cust-001","name":"John Doe","email":"john@example.com"}'
```

**Result:** Process instance started in Camunda! ✅

### What Just Happened?

1. **POST /customers** → Microservice receives request
2. **Microservice** → Starts Camunda process `customer-onboarding`
3. **Camunda** → Creates process instance
4. **Job Worker** → Validates customer against OpenAPI schema
5. **Process** → Completes successfully

**Monitor:** Check Camunda Operate at http://localhost:8081 (demo/demo)

---

### Next Steps

- **Add more tasks:** See [DSL_GRAMMAR.md](DSL_GRAMMAR.md) for all keywords
- **Complex flows:** Add XOR gateways, parallel gateways, etc.
- **Production:** See [END_TO_END_TESTING.md](END_TO_END_TESTING.md)

## Advanced Features

### Professional Layout Engine

The BPM DSL includes a sophisticated layout algorithm that automatically positions BPMN elements for optimal readability:

- **Intelligent Positioning**: Hierarchical element placement with proper spacing
- **Gateway Branch Handling**: Automatic vertical spacing for decision branches
- **Edge Routing**: Orthogonal routing with waypoint optimization
- **Customizable Configuration**: Adjustable spacing, dimensions, and layout parameters

```python
from src.bpm_dsl.layout_engine import LayoutConfig

# Custom layout configuration
config = LayoutConfig()
config.SPACING['horizontal'] = 200
config.SPACING['vertical'] = 120

generator = BPMNGenerator(layout_config=config)
```

### Variable Mapping System

Advanced variable handling with full Zeebe compatibility:

```bmp
scriptCall "Process Data" {
    id: "process-task"
    script: "result = processUserData(userData)"
    inputMappings: [
        {source: "userData" target: "localUserData"}
    ]
    outputMappings: [
        {source: "processedData" target: "processedData"},
        {source: "status" target: "taskStatus"}
    ]
    resultVariable: "customResult"  // Optional, defaults to "result"
}
```

### CLI Interface

Complete command-line interface with multiple commands:

```bash
# Convert DSL to BPMN with validation
python -m bpm_dsl.cli convert process.bpm --output result.bpmn

# Validate process without generating BPMN
python -m bpm_dsl.cli validate process.bpm

# Show detailed process information
python -m bpm_dsl.cli info process.bpm

# Get help
python -m bpm_dsl.cli --help
```

## Architecture Overview

ProcessDsl follows a **microservices-per-process** architecture where each business process gets its own dedicated API microservice:

```
┌─────────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│  OpenAPI Spec   │─────▶│  C# Microservice     │─────▶│ Camunda Process │
│  (REST API)     │      │  (Auto-generated)    │      │  (BPMN)         │
└─────────────────┘      └──────────────────────┘      └─────────────────┘
       ↓                           ↓                            ↓
   Customer.yaml            POST /customers              process-entity-demo
                           ┌──────────────┐
                           │ Orchestrator │
                           │   (NuGet)    │
                           └──────────────┘
```

### Key Components

1. **DSL Layer (Python)**: Define processes in `.bpm` files → Generate BPMN XML
2. **OpenAPI Specs**: Define REST APIs in `.yaml` files (paired with `.bpm` files)
3. **Microservice Generation**: Auto-generate C# APIs using OpenAPI Generator
4. **ProcessDsl.Orchestration (NuGet)**: Shared library for Camunda integration
5. **Camunda Zeebe**: Execute processes and coordinate workflows

## Project Structure

```
ProcessDsl/
├── src/
│   ├── bpm_dsl/              # Python DSL Engine
│   │   ├── parser.py         # Lark-based DSL parser
│   │   ├── ast_nodes.py      # AST node definitions
│   │   ├── bpmn_generator.py # BPMN XML generator
│   │   ├── layout_engine.py  # Layout algorithm
│   │   ├── validator.py      # Process validation
│   │   ├── cli.py           # CLI interface
│   │   └── grammar.lark     # EBNF grammar
│   │
│   ├── ProcessDsl.Orchestration/   # NuGet Package
│   │   ├── ICamundaClient.cs
│   │   ├── CamundaClient.cs
│   │   ├── IProcessOrchestrator.cs
│   │   ├── ProcessOrchestrator.cs
│   │   ├── Models/
│   │   └── README.md
│   │
│   ├── microservices/        # Generated C# APIs
│   │   ├── ProcessEntityDemo/
│   │   │   ├── Generated/    # OpenAPI generated code
│   │   │   ├── Controllers/  # Custom controllers
│   │   │   ├── *.csproj
│   │   │   └── Program.cs
│   │   └── ...
│   │
│   └── jobWorkers/           # TypeScript job workers
│       └── src/
│
├── tests/
│   ├── test_parser.py        # DSL parser tests
│   ├── test_bpmn_generator.py
│   └── ProcessDsl.Orchestration.Tests/  # C# unit tests (27 tests)
│
├── examples/                 # Sample .bpm/.yaml pairs
│   ├── process_entity_demo.bpm
│   ├── process_entity_demo.yaml
│   └── ...
│
├── packages/                 # Local NuGet packages
│   └── ProcessDsl.Orchestration.1.0.0.nupkg
│
└── scripts/                  # Generation scripts
    └── generate-microservice.py
```

## Grammar & Documentation

- **[DSL_GRAMMAR.md](DSL_GRAMMAR.md)**: Complete EBNF grammar specification
- **[LAYOUT_ALGORITHM.md](LAYOUT_ALGORITHM.md)**: Detailed layout engine documentation
- **[OPENAPI_VALIDATION.md](OPENAPI_VALIDATION.md)**: OpenAPI file requirements and validation
- **[QUICKSTART.md](QUICKSTART.md)**: Quick start guide with examples

## Examples

The `examples/` directory contains sample processes demonstrating various patterns:

- **simple_approval.bpm**: Basic approval workflow with gateways
- **order_processing**: Complex order processing with multiple decision points
- **document_review**: Multi-stage review process with parallel branches

Run the demonstration scripts to see all features in action:

```bash
# Basic feature demonstration
python demo.py

# Advanced layout algorithm demonstration  
python demo_advanced_layout.py
```

## Microservices Generation (100% Automated)

### Quick Start - Generate Everything in One Command

```bash
# Generate microservice with Camunda orchestration
./scripts/generate_microservice.sh \
  examples/process_entity_demo.yaml \
  src/microservices/ProcessEntityDemo \
  ProcessEntityDemo

# Build (zero manual edits needed!)
dotnet build src/microservices/ProcessEntityDemo/src/ProcessEntityDemo/

# Run
dotnet run --project src/microservices/ProcessEntityDemo/src/ProcessEntityDemo/
```

**That's it!** The microservice is generated with:
- ✅ Camunda orchestration built-in
- ✅ Process ID from OpenAPI `x-process-id` extension
- ✅ Complete error handling
- ✅ Swagger UI at http://localhost:5100

### Complete End-to-End Workflow

#### 1. Generate BPMN from DSL
```bash
PYTHONPATH=src python3 -m bpm_dsl.cli convert examples/process_entity_demo.bpm \
  --output examples/process_entity_demo.bpmn
```

#### 2. Start Camunda
```bash
# Using Docker
docker run -d -p 26500:26500 -p 8080:8080 --name zeebe camunda/zeebe:latest
```

#### 3. Deploy BPMN
```bash
./scripts/deploy_to_camunda.sh examples/process_entity_demo.bpmn
```

#### 4. Test Everything
```bash
./scripts/test_microservice.sh
# ✅ All tests passing!
```

**See [END_TO_END_TESTING.md](END_TO_END_TESTING.md) for complete testing guide.**

### What Gets Generated Automatically

The custom OpenAPI Generator templates inject orchestration code:

```csharp
// Controllers automatically include:
using ProcessDsl.Orchestration;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("[controller]")]
public class CustomersController : ControllerBase
{
    private readonly IProcessOrchestrator _orchestrator;

    public CustomersController(IProcessOrchestrator orchestrator)
    {
        _orchestrator = orchestrator;
    }

    [HttpPost]
    public async Task<IActionResult> CreateCustomer([FromBody] Customer customer)
    {
        // Automatically start Camunda process when entity is created
        await _orchestrator.StartProcessForEntityAsync(
            "process-entity-demo",  // Process ID from .bpm file
            customer                // Entity data
        );

        return CreatedAtAction(nameof(GetCustomer), new { id = customer.Id }, customer);
    }
}
```

### Local NuGet Package Reference

Add the local package to your microservice project:

```xml
<ItemGroup>
  <PackageReference Include="ProcessDsl.Orchestration" Version="1.0.0" />
</ItemGroup>
```

Configure local package source in `nuget.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="local" value="../../packages" />
  </packageSources>
</configuration>
```

## Development

### Prerequisites

**Python Components:**
- Python 3.8+
- Dependencies: `lark-parser`, `lxml`, `click`

**C# Components:**
- .NET 8.0 SDK
- OpenAPI Generator CLI (via npx)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running Tests

**Python Tests:**
```bash
# Run all Python tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage
python -m pytest tests/ --cov=src/bpm_dsl --cov-report=html
```

**C# Tests:**
```bash
# Run ProcessDsl.Orchestration tests (27 tests)
dotnet test tests/ProcessDsl.Orchestration.Tests/

# Run with detailed output
dotnet test tests/ProcessDsl.Orchestration.Tests/ --verbosity normal

# Generate coverage report
dotnet test tests/ProcessDsl.Orchestration.Tests/ /p:CollectCoverage=true
```

### Project Status

✅ **Complete Features (DSL Layer):**
- Text-based DSL with comprehensive parser
- BPMN XML generation with Zeebe compatibility
- Professional layout engine with gateway handling
- Process validation with detailed error reporting
- CLI interface with convert/validate/info commands
- Comprehensive test suite (100% passing)
- Variable mapping with FEEL expressions
- Custom result variable support

✅ **Complete Features (Microservices Layer - NEW):**
- ProcessDsl.Orchestration NuGet package v1.0.0
- Camunda REST API client with automatic variable mapping
- Process orchestration with entity-driven workflows
- 27 comprehensive unit tests (100% passing)
- OpenAPI Generator integration for C# API generation
- Automatic process triggering from REST endpoints

🚀 **Ready for Production:**
- Deploy generated BPMN files directly to Camunda Zeebe
- Generate production-ready C# microservices from OpenAPI specs
- Seamless REST API → Process orchestration
- Multi-team microservices architecture support
- Use in CI/CD pipelines for end-to-end process automation

## License

MIT License
