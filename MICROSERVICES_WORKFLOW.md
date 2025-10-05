# Microservices Generation Workflow

Complete guide for generating microservices from BPM DSL processes.

## Overview

The ProcessDsl platform enables automatic generation of C# microservices that trigger Camunda process instances when entities are created via REST APIs.

```
.bpm file → Parse → Extract Metadata → Generate C# API → Deploy
    ↓                      ↓                  ↓
.yaml file          process-mappings    Orchestration
```

---

## Prerequisites

**Tools Required:**
- Python 3.8+
- .NET 8.0 SDK
- Node.js (for OpenAPI Generator)
- Running Camunda instance

**Install Dependencies:**
```bash
# Python dependencies
pip install -r requirements.txt

# OpenAPI Generator (via npx - no install needed)
npx @openapitools/openapi-generator-cli version
```

---

## Step-by-Step Workflow

### Step 1: Define Your Process (.bpm file)

Create a business process with a `processEntity` element:

```bpm
process "Customer Onboarding" {
    id: "customer-onboarding"
    version: "1.0"
    
    start "Start Onboarding" {
        id: "start"
    }
    
    processEntity "Validate Customer Data" {
        entityName: "Customer"
    }
    
    scriptCall "Send Welcome Email" {
        id: "send-email"
        script: "sendEmail(customer.email)"
    }
    
    end "Onboarding Complete" {
        id: "end"
    }
    
    flow {
        "start" -> "validate-customer-data"
        "validate-customer-data" -> "send-email"
        "send-email" -> "end"
    }
}
```

**Key Requirements:**
- Process must have a unique `id`
- Must contain at least one `processEntity` element
- File must have `.bpm` extension

### Step 2: Define Your API (.yaml file)

Create an OpenAPI specification with the **same base name** as your `.bpm` file:

```yaml
# customer_onboarding.yaml (matches customer_onboarding.bpm)
openapi: 3.0.3
info:
  title: Customer API
  version: 1.0.0

components:
  schemas:
    Customer:
      type: object
      required:
        - id
        - name
        - email
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
      summary: Create a new customer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Customer'
      responses:
        '201':
          description: Customer created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Customer'
```

**Key Requirements:**
- Must define the entity schema referenced in `processEntity`
- Must have at least one POST endpoint
- File must have `.yaml` or `.yml` extension
- Must be in the same directory as the `.bpm` file

### Step 3: Extract Process Metadata

Run the metadata extraction script to analyze your processes:

```bash
python3 scripts/extract_process_metadata.py examples/
```

**Output:** `src/microservices/process-mappings.json`
```json
{
  "customer-onboarding": {
    "processId": "customer-onboarding",
    "processName": "Customer Onboarding",
    "entityName": "Customer",
    "bpmFile": "examples/customer_onboarding.bpm",
    "yamlFile": "examples/customer_onboarding.yaml",
    "postEndpoint": "/customers",
    "version": "1.0"
  }
}
```

This JSON file:
- Maps process IDs to their metadata
- Links entities to process definitions
- Identifies REST endpoints for process triggering

### Step 4: Generate BPMN

Convert your DSL to BPMN for Camunda:

```bash
python3 -m bpm_dsl.cli convert examples/customer_onboarding.bpm
```

**Output:** `customer_onboarding.bpmn`
- Ready to deploy to Camunda
- Contains all Zeebe extensions
- Includes process entity validation tasks

### Step 5: Generate C# Microservice

Generate the ASP.NET Core API from your OpenAPI spec:

```bash
# Create output directory
mkdir -p src/microservices/CustomerOnboarding

# Generate C# code
npx @openapitools/openapi-generator-cli generate \
  -i examples/customer_onboarding.yaml \
  -g aspnetcore \
  -o src/microservices/CustomerOnboarding/Generated \
  --additional-properties=aspnetCoreVersion=8.0,packageName=CustomerOnboarding.Generated
```

### Step 6: Add ProcessDsl.Orchestration

Reference the NuGet package in your generated project:

```bash
cd src/microservices/CustomerOnboarding/Generated/src/CustomerOnboarding.Generated

# Add local package reference
dotnet add package ProcessDsl.Orchestration --source ../../../../../packages
```

### Step 7: Create Custom Controller

Override the generated controller to integrate process orchestration:

**Create:** `src/microservices/CustomerOnboarding/Controllers/CustomersController.cs`

```csharp
using Microsoft.AspNetCore.Mvc;
using ProcessDsl.Orchestration;
using CustomerOnboarding.Generated.Models;
using CustomerOnboarding.Generated.Controllers;

namespace CustomerOnboarding.Controllers;

[ApiController]
[Route("api/[controller]")]
public class CustomersController : DefaultApiController
{
    private readonly IProcessOrchestrator _orchestrator;

    public CustomersController(IProcessOrchestrator orchestrator)
    {
        _orchestrator = orchestrator;
    }

    public override async Task<IActionResult> CustomersPost([FromBody] Customer customer)
    {
        // Start Camunda process instance
        await _orchestrator.StartProcessForEntityAsync(
            "customer-onboarding",  // From process-mappings.json
            customer
        );

        return CreatedAtAction(nameof(CustomersPost), new { id = customer.Id }, customer);
    }
}
```

### Step 8: Configure Program.cs

Update the startup configuration:

```csharp
using ProcessDsl.Orchestration;

var builder = WebApplication.CreateBuilder(args);

// Add ProcessDsl Orchestration
builder.Services.AddProcessDslOrchestration(options =>
{
    options.BaseUrl = builder.Configuration["Camunda:BaseUrl"] 
        ?? "http://localhost:8080";
    options.TimeoutSeconds = 30;
});

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.MapControllers();
app.Run();
```

### Step 9: Add Configuration

**appsettings.json:**
```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "ProcessDsl.Orchestration": "Debug"
    }
  },
  "Camunda": {
    "BaseUrl": "http://localhost:8080"
  },
  "AllowedHosts": "*"
}
```

### Step 10: Build and Run

```bash
# Build
dotnet build

# Run the microservice
dotnet run --urls http://localhost:5100
```

### Step 11: Test the Integration

```bash
# Create a customer via REST API
curl -X POST http://localhost:5100/customers \
  -H "Content-Type: application/json" \
  -d '{
    "id": "cust-001",
    "name": "John Doe",
    "email": "john@example.com"
  }'

# Response: 201 Created
# Behind the scenes: Camunda process "customer-onboarding" started automatically
```

### Step 12: Verify in Camunda

Check that the process instance was created:

```bash
# Query Camunda for process instances
curl http://localhost:8080/engine-rest/process-instance?processDefinitionKey=customer-onboarding
```

---

## Complete Example: Full Workflow

```bash
#!/bin/bash
# generate-customer-service.sh

# 1. Extract metadata
python3 scripts/extract_process_metadata.py examples/

# 2. Generate BPMN
python3 -m bpm_dsl.cli convert examples/customer_onboarding.bpm

# 3. Generate C# API
npx @openapitools/openapi-generator-cli generate \
  -i examples/customer_onboarding.yaml \
  -g aspnetcore \
  -o src/microservices/CustomerOnboarding/Generated \
  --additional-properties=aspnetCoreVersion=8.0,packageName=CustomerOnboarding.Generated

# 4. Add orchestration package
cd src/microservices/CustomerOnboarding/Generated/src/CustomerOnboarding.Generated
dotnet add package ProcessDsl.Orchestration --source ../../../../../packages
cd ../../../../..

# 5. Build
dotnet build src/microservices/CustomerOnboarding/Generated/src/CustomerOnboarding.Generated/

echo "✓ Microservice generated successfully!"
echo "  - Process ID: customer-onboarding"
echo "  - API Port: 5100"
echo "  - Swagger: http://localhost:5100/swagger"
```

---

## Architecture Flow

```
┌──────────────────┐
│  Client Request  │
│  POST /customers │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────┐
│  ASP.NET Core API       │
│  CustomersController    │
│  (Generated + Custom)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  ProcessDsl             │
│  Orchestration (NuGet)  │
│  - IProcessOrchestrator │
│  - ICamundaClient       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Camunda REST API       │
│  POST /process-         │
│  definition/key/{id}/   │
│  start                  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Camunda Zeebe Engine   │
│  - Start Process        │
│  - Execute Tasks        │
│  - Run Job Workers      │
└─────────────────────────┘
```

---

## Best Practices

### 1. Process Design
- ✅ Use descriptive process and entity names
- ✅ Keep processes focused (single responsibility)
- ✅ Add version numbers for tracking
- ✅ Document process intent in comments

### 2. API Design
- ✅ Follow REST conventions
- ✅ Use proper HTTP status codes
- ✅ Validate input schemas
- ✅ Include meaningful descriptions

### 3. Error Handling
- ✅ Handle Camunda connection failures gracefully
- ✅ Log process start attempts
- ✅ Return meaningful error messages to clients
- ✅ Implement retry policies

### 4. Configuration
- ✅ Externalize Camunda URL
- ✅ Use environment-specific settings
- ✅ Configure timeouts appropriately
- ✅ Enable logging in development

### 5. Testing
- ✅ Unit test controllers
- ✅ Mock ProcessDsl.Orchestration in tests
- ✅ Integration test with test containers
- ✅ Verify process instances in Camunda

---

## Troubleshooting

### Process Not Starting

**Problem:** Process instance not created when calling API

**Solutions:**
1. Check Camunda is running: `curl http://localhost:8080/engine-rest/version`
2. Verify BPMN is deployed: Deploy `.bpmn` file to Camunda
3. Check process ID matches: Compare `process-mappings.json` with controller code
4. Review logs: Look for orchestration errors

### Entity Validation Failing

**Problem:** ProcessEntity task fails in Camunda

**Solutions:**
1. Ensure OpenAPI spec is available to job worker
2. Verify entity schema matches request body
3. Check job worker is running: `npm start` in `src/jobWorkers`
4. Review Camunda job failures

### Code Generation Issues

**Problem:** OpenAPI Generator fails

**Solutions:**
1. Validate OpenAPI spec: `npx @openapitools/openapi-generator-cli validate -i spec.yaml`
2. Check API version: Use OpenAPI 3.0.x
3. Verify paths and schemas are defined
4. Review generator output for warnings

---

## Next Steps

- [Generate Multiple Microservices](scripts/README.md)
- [Configure CI/CD Pipeline](#)
- [Deploy to Kubernetes](#)
- [Monitor Process Instances](#)

---

## Resources

- [BPM DSL Grammar](DSL_GRAMMAR.md)
- [ProcessDsl.Orchestration API](src/ProcessDsl.Orchestration/README.md)
- [Camunda Documentation](https://docs.camunda.io/)
- [OpenAPI Specification](https://swagger.io/specification/)
