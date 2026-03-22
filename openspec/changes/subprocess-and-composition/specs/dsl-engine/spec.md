## ADDED Requirements

### Requirement: Subprocess elements with nested structure
The system SHALL support a `subprocess` element that contains its own child elements (start, end, tasks, gateways) and an internal `flow` block. The subprocess SHALL generate an ID from its name in kebab-case. Boundary events (`onTimer`, `onError`) SHALL be nestable inside subprocesses, following the same pattern as service tasks.

#### Scenario: Parse subprocess with internal elements and flow
- **WHEN** a `.bpm` file contains a subprocess with start, serviceTask, end elements and a flow block
- **THEN** the parser SHALL produce a Subprocess AST node containing the child elements and internal flows

#### Scenario: Subprocess with boundary error
- **WHEN** a subprocess contains an `onError "Order Error" { errorCode: "ORDER_ERROR" }` block
- **THEN** the parser SHALL produce a Subprocess AST node with a BoundaryErrorEvent in its boundary_events list

#### Scenario: Generate BPMN for subprocess
- **WHEN** a subprocess with internal start, task, and end is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:subProcess` element with nested `bpmn:startEvent`, task elements, `bpmn:endEvent`, and internal `bpmn:sequenceFlow` elements

#### Scenario: Validate subprocess internal structure
- **WHEN** a subprocess is missing a start or end event internally
- **THEN** the validator SHALL return an error about the subprocess's internal structure

### Requirement: Call activity elements
The system SHALL support a `callActivity` element that invokes another process by ID. The element SHALL accept `processId` (required), `propagateAllVariables` (default `true`), and optional `inputMappings` / `outputMappings` properties. Variable mappings SHALL use the `"source" -> "target"` syntax.

#### Scenario: Parse call activity with propagateAll
- **WHEN** a `.bpm` file contains `callActivity "Validate" { processId: "validation", propagateAllVariables: true }`
- **THEN** the parser SHALL produce a CallActivity AST node with processId="validation" and propagateAllVariables=true

#### Scenario: Parse call activity with explicit mappings
- **WHEN** a `.bpm` file contains a callActivity with `inputMappings: ["orderId" -> "orderId"]` and `outputMappings: ["result" -> "status"]`
- **THEN** the parser SHALL produce a CallActivity AST node with the specified variable mappings

#### Scenario: Generate BPMN for call activity
- **WHEN** a callActivity with processId "payment-validation" and propagateAllVariables=true is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:callActivity` with a `zeebe:calledElement` extension specifying `processId="payment-validation"` and `propagateAllChildVariables="true"`

#### Scenario: Generate BPMN for call activity with mappings
- **WHEN** a callActivity with explicit input/output mappings is converted to BPMN
- **THEN** the output SHALL contain `zeebe:ioMapping` with `zeebe:input` and `zeebe:output` elements inside the call activity

### Requirement: Multi-instance execution
The system SHALL support `forEach`, `as`, and `parallel` modifier properties on `serviceTask` and `subprocess` elements. `forEach` SHALL specify the collection variable name, `as` SHALL specify the element variable name, and `parallel` SHALL be a boolean (default `false`). When present, the BPMN output SHALL include `bpmn:multiInstanceLoopCharacteristics` on the activity.

#### Scenario: Parse sequential multi-instance service task
- **WHEN** a serviceTask contains `forEach: "items"`, `as: "item"`, `parallel: false`
- **THEN** the parser SHALL produce a ServiceTask AST node with forEach="items", as="item", parallel=false

#### Scenario: Parse parallel multi-instance subprocess
- **WHEN** a subprocess contains `forEach: "lineItems"`, `as: "item"`, `parallel: true`
- **THEN** the parser SHALL produce a Subprocess AST node with forEach="lineItems", as="item", parallel=true

#### Scenario: Generate BPMN for multi-instance
- **WHEN** a serviceTask with `forEach: "stakeholders"`, `as: "stakeholder"`, `parallel: true` is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:multiInstanceLoopCharacteristics` with `isSequential="false"` and Zeebe extension elements for `inputCollection`, `inputElement`, `outputCollection`, and `outputElement`

#### Scenario: Default parallel to false
- **WHEN** a serviceTask has `forEach` and `as` but no `parallel` property
- **THEN** the multi-instance SHALL be sequential (`isSequential="true"` in BPMN)

## MODIFIED Requirements

### Requirement: Process validation enforces structural rules
The validator SHALL enforce the following rules across five levels:
1. Process name and ID must be non-empty; ID must be a valid XML identifier
2. All element IDs must be unique and valid XML identifiers; at least one StartEvent and one EndEvent required
3. Flow source/target IDs must reference existing elements (including boundary event IDs)
4. StartEvents must have no incoming flows; EndEvents must have no outgoing flows; all elements must be reachable from a start event
5. Script expressions must be non-empty for Zeebe compatibility
6. Subprocess internal elements SHALL be validated recursively using the same rules (levels 1-5)
7. CallActivity processId SHALL be non-empty and a valid identifier

#### Scenario: Missing processEntity
- **WHEN** a process has zero processEntity elements
- **THEN** validation SHALL return an error indicating exactly one processEntity is required

#### Scenario: Unreachable element
- **WHEN** an element has no path from any start event
- **THEN** validation SHALL return an error about the orphaned element

#### Scenario: Duplicate element IDs
- **WHEN** two elements share the same ID (including across subprocess boundaries)
- **THEN** validation SHALL return an error about duplicate IDs

#### Scenario: Invalid subprocess internal structure
- **WHEN** a subprocess has no internal start event
- **THEN** validation SHALL return an error about the subprocess missing a required start event

#### Scenario: Empty callActivity processId
- **WHEN** a callActivity has an empty processId
- **THEN** validation SHALL return an error about missing process reference
