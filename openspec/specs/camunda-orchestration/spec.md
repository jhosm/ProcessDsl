## Purpose

The Camunda orchestration library is a C# NuGet package (.NET 8.0) that provides a high-level API for starting and managing Zeebe process instances. It wraps the Zeebe gRPC client with configuration, dependency injection, structured logging, and convenience methods for entity-based workflows.

## Requirements

### Requirement: CamundaClient connects to Zeebe in plaintext or TLS mode
The CamundaClient SHALL support two connection modes: plaintext (unencrypted gRPC for development) and TLS-encrypted with bearer token authentication (for production/Camunda Cloud). When `UsePlainText` is false and no `AuthToken` is provided, the client SHALL throw an `InvalidOperationException`. The client SHALL implement `IDisposable` for proper gRPC cleanup.

#### Scenario: Plaintext connection
- **WHEN** CamundaConfiguration has `UsePlainText=true`
- **THEN** the client SHALL connect via unencrypted gRPC without requiring an auth token

#### Scenario: TLS connection with token
- **WHEN** CamundaConfiguration has `UsePlainText=false` and `AuthToken` is set
- **THEN** the client SHALL connect via TLS-encrypted gRPC with bearer token authentication

#### Scenario: TLS connection without token
- **WHEN** CamundaConfiguration has `UsePlainText=false` and `AuthToken` is null
- **THEN** the client SHALL throw `InvalidOperationException`

### Requirement: CamundaClient creates process instances
The client SHALL provide `CreateProcessInstanceAsync` to start process instances in Zeebe, accepting a process definition key and a `StartProcessRequest` containing variables and an optional business key. Variables SHALL be serialized as a single JSON object. The method SHALL always use the latest version of the process definition. The client SHALL throw `ArgumentException` if the process definition key is null or empty, and `ArgumentNullException` if the request is null.

#### Scenario: Start process with variables
- **WHEN** `CreateProcessInstanceAsync` is called with a valid key and variables
- **THEN** the client SHALL create a Zeebe process instance and return a `ProcessInstance` with instance key, definition key, BPMN process ID, and version

#### Scenario: Empty process definition key
- **WHEN** `CreateProcessInstanceAsync` is called with an empty string
- **THEN** the client SHALL throw `ArgumentException`

### Requirement: CamundaClient supports entity-based process creation
The client SHALL provide `CreateProcessInstanceWithEntityAsync` that wraps any entity object as a `processEntity` variable and delegates to `CreateProcessInstanceAsync`. This supports the DSL's processEntity validation workflow pattern.

#### Scenario: Start process with entity data
- **WHEN** `CreateProcessInstanceWithEntityAsync` is called with entity data
- **THEN** the client SHALL create a process instance with the entity wrapped in a `processEntity` variable

### Requirement: ProcessOrchestrator provides high-level process management
The orchestrator SHALL provide `StartProcessAsync` (with arbitrary variables and optional business key) and `StartProcessForEntityAsync` (with entity data). Both methods SHALL validate inputs (non-null, non-empty process ID) before delegating to the CamundaClient. Both methods SHALL support `CancellationToken` for async cancellation.

#### Scenario: Start process with business key
- **WHEN** `StartProcessAsync` is called with variables and a business key
- **THEN** the orchestrator SHALL delegate to the CamundaClient and return the process instance metadata

#### Scenario: Null process ID
- **WHEN** either method is called with a null or empty process ID
- **THEN** the orchestrator SHALL throw `ArgumentException` before contacting Zeebe

### Requirement: ProcessOrchestrator provides structured logging
The orchestrator SHALL log at INFO level when starting a process (including process ID and variable count or entity type) and when a process instance is successfully created (including the instance key). On failure, the orchestrator SHALL log at ERROR level with exception details. Logging SHALL be optional — a null `ILogger` SHALL not cause errors.

#### Scenario: Successful process start logging
- **WHEN** a process is started successfully
- **THEN** the orchestrator SHALL log both the start attempt and the resulting instance key at INFO level

#### Scenario: No logger configured
- **WHEN** the orchestrator is created without an ILogger
- **THEN** all operations SHALL succeed without logging

### Requirement: Configuration supports development and production environments
`CamundaConfiguration` SHALL provide: `GatewayAddress` (default "localhost:26500"), `AuthToken` (nullable), `TimeoutSeconds` (default 30), `UsePlainText` (default true), and `KeepAliveSeconds` (default 30). Configuration SHALL be injectable via `IOptions<CamundaConfiguration>`.

#### Scenario: Default configuration
- **WHEN** no configuration overrides are provided
- **THEN** the client SHALL connect to localhost:26500 in plaintext mode with 30-second timeouts

### Requirement: DI registration provides two convenience overloads
`AddProcessDslOrchestration` SHALL support a lambda overload for full configuration and a string overload for gateway-address-only setup. `ICamundaClient` SHALL be registered as singleton; `IProcessOrchestrator` SHALL be registered as scoped. Both overloads SHALL return `IServiceCollection` for method chaining.

#### Scenario: Lambda configuration registration
- **WHEN** `AddProcessDslOrchestration(cfg => ...)` is called
- **THEN** the container SHALL have ICamundaClient (singleton) and IProcessOrchestrator (scoped) registered

#### Scenario: Gateway-only registration
- **WHEN** `AddProcessDslOrchestration("my-host:26500")` is called
- **THEN** the container SHALL be configured with that gateway address and default settings

### Requirement: All operations are async and support cancellation
All public methods on ICamundaClient and IProcessOrchestrator SHALL return `Task<ProcessInstance>` and accept an optional `CancellationToken`. No blocking calls SHALL be used.

#### Scenario: Cancellation token propagation
- **WHEN** an operation is called with a cancelled token
- **THEN** the operation SHALL respect cancellation and throw `OperationCanceledException`
