# ProcessDsl.Orchestration

Camunda Zeebe orchestration library for ProcessDsl microservices. Provides seamless integration between REST APIs and Camunda workflow processes.

## Installation

```bash
dotnet add package ProcessDsl.Orchestration
```

## Quick Start

### 1. Configure in Program.cs

```csharp
using ProcessDsl.Orchestration;

var builder = WebApplication.CreateBuilder(args);

// Add ProcessDsl Orchestration
builder.Services.AddProcessDslOrchestration(options =>
{
    options.BaseUrl = "http://localhost:8080"; // Camunda REST API URL
    options.TimeoutSeconds = 30;
    options.EnableLogging = true;
});

// Or with simple configuration
builder.Services.AddProcessDslOrchestration("http://localhost:8080");
```

### 2. Inject and Use in Controllers

```csharp
using ProcessDsl.Orchestration;

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
        // Start Camunda process with entity data
        var processInstance = await _orchestrator.StartProcessForEntityAsync(
            "process-entity-demo",  // Process ID from .bpm file
            customer
        );

        return CreatedAtAction(
            nameof(GetCustomer),
            new { id = customer.Id },
            customer
        );
    }
}
```

## Configuration Options

```csharp
public class CamundaConfiguration
{
    public string BaseUrl { get; set; }           // Camunda REST API URL
    public string? AuthToken { get; set; }        // Optional auth token
    public int TimeoutSeconds { get; set; }       // Request timeout (default: 30)
    public bool EnableLogging { get; set; }       // Enable logging (default: false)
}
```

## API Reference

### IProcessOrchestrator

High-level interface for starting processes:

- `StartProcessForEntityAsync(processId, entityData)` - Start process with entity as "entityData" variable
- `StartProcessAsync(processId, variables, businessKey)` - Start process with custom variables

### ICamundaClient

Low-level interface for direct Camunda API calls:

- `CreateProcessInstanceAsync(processDefinitionKey, request)` - Create process instance
- `CreateProcessInstanceWithEntityAsync(processDefinitionKey, entityData)` - Create with single entity

## Features

- ✅ Automatic process instance creation
- ✅ Type-safe entity data mapping
- ✅ Built-in error handling and logging
- ✅ Camunda Cloud authentication support
- ✅ Configurable timeouts and retry policies
- ✅ Easy dependency injection setup

## License

MIT
