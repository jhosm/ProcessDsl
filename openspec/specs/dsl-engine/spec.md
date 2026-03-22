## Purpose

The DSL engine is the core Python pipeline that parses `.bpm` text files into an AST, validates process structure, generates Zeebe-compatible BPMN XML, and applies automatic diagram layout. It is the foundation of the ProcessDsl platform — all other components consume its output.

## Requirements

### Requirement: DSL grammar supports BPM process definitions
The system SHALL parse `.bpm` files containing process definitions with a name, optional id, and optional version. The grammar SHALL support six element types: `start`, `end`, `scriptCall`, `serviceTask`, `processEntity`, and `xorGateway`. Each element SHALL have a quoted display name and a block body with type-specific properties. A `flow` block SHALL define sequence flows between elements using `"source" -> "target"` syntax with optional `when` conditions and `default` markers.

#### Scenario: Parse a minimal process
- **WHEN** a `.bpm` file contains a process with a start, processEntity, and end element connected by flows
- **THEN** the parser SHALL produce an AST with a Process node containing the declared elements and flows

#### Scenario: Parse conditional flows
- **WHEN** a flow uses `when "expression"` or `default` modifiers
- **THEN** the parser SHALL produce Flow nodes with the condition expression or is_default flag set accordingly

### Requirement: Element IDs are auto-generated in kebab-case
The system SHALL auto-generate element IDs from display names by lowercasing, removing special characters, and replacing spaces and underscores with hyphens. Explicitly provided IDs SHALL override auto-generation.

#### Scenario: Auto-generate ID from display name
- **WHEN** an element has the display name "Load Customer Data"
- **THEN** the generated ID SHALL be `load-customer-data`

#### Scenario: Handle special characters in names
- **WHEN** an element has the display name "Order Valid?"
- **THEN** the generated ID SHALL be `order-valid` with the question mark stripped

### Requirement: Every BPM file must have a matching OpenAPI spec
The parser SHALL require a `.yaml` or `.yml` file with the same basename in the same directory as the `.bpm` file. The parser SHALL search for `.yaml` first, then `.yml`. If no matching file exists, the parser SHALL raise a `FileNotFoundError`.

#### Scenario: Matching YAML file exists
- **WHEN** parsing `examples/demo.bpm` and `examples/demo.yaml` exists
- **THEN** the parser SHALL store the OpenAPI file path on the Process node

#### Scenario: No matching YAML file
- **WHEN** parsing `examples/demo.bpm` and neither `demo.yaml` nor `demo.yml` exists
- **THEN** the parser SHALL raise a `FileNotFoundError`

### Requirement: Variable mappings support identity and explicit forms
The system SHALL support two forms of variable mapping: identity mappings (`inputVars: ["x", "y"]`) where source equals target, and explicit mappings (`inputMappings: ["source" -> "target"]`) with distinct source and target. Both forms SHALL be available on `scriptCall` and `serviceTask` elements.

#### Scenario: Identity variable mapping
- **WHEN** an element declares `inputVars: ["x", "y"]`
- **THEN** the AST SHALL contain VariableMapping nodes with source=target for each variable

#### Scenario: Explicit source-to-target mapping
- **WHEN** an element declares `inputMappings: ["data" -> "processData"]`
- **THEN** the AST SHALL contain a VariableMapping with source="data" and target="processData"

### Requirement: ScriptCall elements have sensible defaults
A `scriptCall` element SHALL default `resultVariable` to `"result"` when not explicitly specified. Input and output mappings SHALL default to empty lists.

#### Scenario: Default result variable
- **WHEN** a scriptCall does not specify resultVariable
- **THEN** the AST node SHALL have resultVariable="result"

### Requirement: ServiceTask elements have sensible defaults
A `serviceTask` element SHALL default `retries` to `3` when not explicitly specified. Headers, input mappings, and output mappings SHALL default to empty lists.

#### Scenario: Default retries
- **WHEN** a serviceTask does not specify retries
- **THEN** the AST node SHALL have retries=3

### Requirement: Process validation enforces structural rules
The validator SHALL enforce the following rules across five levels:
1. Process name and ID must be non-empty; ID must be a valid XML identifier
2. All element IDs must be unique and valid XML identifiers; exactly one ProcessEntity must exist; at least one StartEvent and one EndEvent required
3. Flow source/target IDs must reference existing elements
4. StartEvents must have no incoming flows; EndEvents must have no outgoing flows; all elements must be reachable from a start event; ProcessEntity must be the first task after start events
5. Script expressions must be non-empty for Zeebe compatibility

#### Scenario: Missing processEntity
- **WHEN** a process has zero processEntity elements
- **THEN** validation SHALL return an error indicating exactly one processEntity is required

#### Scenario: ProcessEntity not first after start
- **WHEN** a processEntity is not directly connected from a start event as the first task
- **THEN** validation SHALL return an error about processEntity positioning

#### Scenario: Unreachable element
- **WHEN** an element has no path from any start event
- **THEN** validation SHALL return an error about the orphaned element

#### Scenario: Duplicate element IDs
- **WHEN** two elements share the same ID
- **THEN** validation SHALL return an error about duplicate IDs

### Requirement: BPMN generation produces Zeebe-compatible XML
The generator SHALL produce BPMN 2.0 XML with Zeebe namespace extensions. StartEvents and EndEvents SHALL generate standard BPMN events. ScriptCalls SHALL generate `bpmn:scriptTask` with `zeebe:script` extensions using FEEL expressions. ServiceTasks SHALL generate `bpmn:serviceTask` with `zeebe:taskDefinition` (type, retries) and `zeebe:taskHeaders`. Variable mappings SHALL generate `zeebe:ioMapping` with `zeebe:input` and `zeebe:output` elements. FEEL expressions SHALL be auto-prefixed with `=` if not already present.

#### Scenario: Generate scriptTask with FEEL
- **WHEN** a scriptCall has `script: "result = x + 1"` and `inputVars: ["x"]`
- **THEN** the BPMN XML SHALL contain a scriptTask with zeebe:script expression and zeebe:ioMapping

#### Scenario: Generate serviceTask with headers
- **WHEN** a serviceTask has `taskType: "api-call"`, `retries: 5`, and headers
- **THEN** the BPMN XML SHALL contain a serviceTask with zeebe:taskDefinition and zeebe:taskHeaders

### Requirement: ProcessEntity auto-generates validation flow
When a `processEntity` element is encountered, the generator SHALL automatically produce three BPMN elements: a serviceTask (type `process-entity-validator` with entityModel and entityName headers), an exclusiveGateway for validation checking, and an error endEvent. The generator SHALL create flows connecting entity → gateway, gateway → error-end (when `entityValidationResult.isValid = false`), and gateway → next-element (default/success path).

#### Scenario: ProcessEntity generates validation pattern
- **WHEN** a processEntity with entityName "Customer" is converted to BPMN
- **THEN** the output SHALL contain a process-entity-validator serviceTask, a validation gateway, and an error end event with appropriate connecting flows

#### Scenario: ProcessEntity validation gateway IDs
- **WHEN** a processEntity has ID "load-customer"
- **THEN** the validation gateway SHALL have ID "load-customer-validation-gateway" and the error end event SHALL have ID "load-customer-validation-error"

### Requirement: Layout engine produces professional diagram positions
The layout engine SHALL assign horizontal positions via topological level assignment (BFS from start events) and vertical positions within each level. Gateway branches SHALL be spread vertically around the gateway. Edge routing SHALL use straight lines for same-level connections and orthogonal (L-shaped) routing for cross-level connections. The output SHALL include BPMNDiagram with BPMNShape bounds and BPMNEdge waypoints.

#### Scenario: Elements positioned left to right
- **WHEN** a process has start → task → end
- **THEN** the start event SHALL be at level 0 (leftmost), the task at level 1, and the end event at level 2

#### Scenario: Gateway branches spread vertically
- **WHEN** a gateway has two outgoing branches
- **THEN** the branch targets SHALL be positioned at different vertical offsets relative to the gateway

### Requirement: CLI provides convert, validate, and info commands
The CLI SHALL provide three commands: `convert` (parse, validate, generate BPMN XML with layout), `validate` (parse and validate only), and `info` (display process metadata without validation). The `convert` command SHALL default output filename to the input basename with `.bpmn` extension. All commands SHALL exit with code 1 on errors.

#### Scenario: Convert produces BPMN file
- **WHEN** `convert examples/demo.bpm` is run
- **THEN** the system SHALL produce `examples/demo.bpmn` containing valid BPMN XML

#### Scenario: Validate reports errors
- **WHEN** `validate` is run on a BPM file with structural errors
- **THEN** the system SHALL display error messages and exit with code 1
