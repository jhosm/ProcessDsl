## Purpose

The entity validation system is a TypeScript Zeebe job worker that validates process entity data against OpenAPI schemas at runtime. It bridges the DSL's `processEntity` construct with runtime schema enforcement, ensuring data conforms to the paired OpenAPI spec before the process continues.

## Requirements

### Requirement: Validator registers as a process-entity-validator worker
The system SHALL register a Zeebe job worker for the task type `process-entity-validator`. The worker SHALL connect to the Zeebe broker, subscribe to jobs of that type, and process them asynchronously.

#### Scenario: Worker registration
- **WHEN** the validator is started
- **THEN** it SHALL register a worker for the `process-entity-validator` task type with the Zeebe client

### Requirement: Validator extracts entity data and schema references from jobs
The worker SHALL read the `processEntity` variable from job variables and the `entityName` and `entityModel` values from job custom headers. If any of these are missing, the worker SHALL complete the job with `isValid: false` and an appropriate error message.

#### Scenario: All inputs present
- **WHEN** a job has `processEntity` in variables and `entityName`/`entityModel` in headers
- **THEN** the worker SHALL proceed with validation

#### Scenario: Missing processEntity variable
- **WHEN** a job has no `processEntity` variable or it is not an object
- **THEN** the worker SHALL complete the job with `isValid: false` and an error indicating the entity is missing

#### Scenario: Missing entityName header
- **WHEN** a job has no `entityName` custom header
- **THEN** the worker SHALL complete the job with `isValid: false` and an error about the missing header

### Requirement: Validator loads OpenAPI schemas from the filesystem
The worker SHALL resolve the `entityModel` header to a file path under the `openAPI_contracts/` directory. Path values SHALL be sanitized by stripping leading slashes. The system SHALL support `.yaml`, `.yml`, and `.json` file formats. If the file does not exist, the worker SHALL complete the job with `isValid: false`.

#### Scenario: Load YAML schema
- **WHEN** `entityModel` points to a `.yaml` file in `openAPI_contracts/`
- **THEN** the worker SHALL parse the file as YAML and extract the OpenAPI spec

#### Scenario: Schema file not found
- **WHEN** `entityModel` points to a file that does not exist
- **THEN** the worker SHALL complete the job with `isValid: false` and an error about the missing file

#### Scenario: Path traversal prevention
- **WHEN** `entityModel` starts with a leading slash
- **THEN** the worker SHALL strip the leading slash before resolving the path

### Requirement: Validator resolves entity schemas from OpenAPI components
The worker SHALL look up the entity schema at `components.schemas[entityName]` in the loaded OpenAPI spec. All schemas in `components.schemas` SHALL be registered with AJV using `#/components/schemas/{name}` references to enable `$ref` resolution. If the named entity is not found in the spec, the worker SHALL complete the job with `isValid: false`.

#### Scenario: Entity found in schema
- **WHEN** the OpenAPI spec has `components.schemas.Customer` and `entityName` is "Customer"
- **THEN** the worker SHALL use that schema for validation

#### Scenario: Entity not in schema
- **WHEN** `entityName` does not match any key in `components.schemas`
- **THEN** the worker SHALL complete the job with `isValid: false` and an error about the missing entity

#### Scenario: Cross-schema references
- **WHEN** a schema uses `$ref: "#/components/schemas/Address"` to reference another schema
- **THEN** the worker SHALL resolve the reference via pre-registered AJV schemas

### Requirement: Validator performs JSON Schema validation with format checking
The worker SHALL validate the `processEntity` data against the resolved schema using AJV with `allErrors: true` (collect all errors), `strict: false` (allow OpenAPI keywords), and format validation enabled via `ajv-formats`. Supported formats include `email`, `date`, `time`, `uri`, and pattern-based constraints.

#### Scenario: Valid entity passes
- **WHEN** `processEntity` conforms to the schema
- **THEN** the worker SHALL complete the job with `isValid: true` and an empty errors array

#### Scenario: Multiple validation errors collected
- **WHEN** `processEntity` has three constraint violations
- **THEN** the worker SHALL complete the job with `isValid: false` and all three errors listed

#### Scenario: Format validation
- **WHEN** a field has `format: "email"` and the value is not a valid email
- **THEN** the worker SHALL report a format validation error

### Requirement: Validator returns structured validation results
The worker SHALL always complete the job (never fail or retry). The completion payload SHALL include a `validationResult` object with: `isValid` (boolean), `errors` (array of strings in `"<path>: <message>"` format), `entityName` (echoed from input), and `entityModel` (echoed from input).

#### Scenario: Successful validation result
- **WHEN** validation passes
- **THEN** `validationResult` SHALL have `isValid: true`, empty `errors`, and the original `entityName` and `entityModel`

#### Scenario: Failed validation result with paths
- **WHEN** validation fails on field `/address/zipCode`
- **THEN** `errors` SHALL contain a string starting with `/address/zipCode:` describing the constraint violation

### Requirement: Worker supports graceful shutdown
The system SHALL handle SIGINT and SIGTERM signals by gracefully closing the worker and the Zeebe client connection before exiting.

#### Scenario: SIGTERM received
- **WHEN** the process receives SIGTERM
- **THEN** the worker SHALL stop accepting new jobs, close the Zeebe connection, and exit cleanly
