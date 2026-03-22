## MODIFIED Requirements

### Requirement: DSL grammar supports BPM process definitions
The system SHALL parse `.bpm` files containing process definitions with a name, optional id, and optional version. The grammar SHALL support element types: `start`, `end`, `scriptCall`, `serviceTask`, `processEntity`, and `gateway`. Each element SHALL have a quoted display name and a block body with type-specific properties. The `gateway` element SHALL require a `type` property with allowed values `"xor"` and `"parallel"`. A `flow` block SHALL define sequence flows between elements using `"source" -> "target"` syntax with optional `when` conditions and `otherwise` markers.

#### Scenario: Parse a minimal process
- **WHEN** a `.bpm` file contains a process with a start, processEntity, and end element connected by flows
- **THEN** the parser SHALL produce an AST with a Process node containing the declared elements and flows

#### Scenario: Parse conditional flows
- **WHEN** a flow uses `when "expression"` or `otherwise` modifiers
- **THEN** the parser SHALL produce Flow nodes with the condition expression or is_default flag set accordingly

#### Scenario: Parse an exclusive gateway
- **WHEN** a `.bpm` file contains `gateway "Decision" { type: "xor" }`
- **THEN** the parser SHALL produce a Gateway AST node with name "Decision" and gateway_type "xor"

#### Scenario: Parse a parallel gateway
- **WHEN** a `.bpm` file contains `gateway "Fork" { type: "parallel" }`
- **THEN** the parser SHALL produce a Gateway AST node with name "Fork" and gateway_type "parallel"

#### Scenario: Reject unknown gateway type
- **WHEN** a `.bpm` file contains `gateway "X" { type: "unknown" }`
- **THEN** the parser SHALL raise a parse error

#### Scenario: Reject legacy xorGateway keyword
- **WHEN** a `.bpm` file contains `xorGateway "Decision" {}`
- **THEN** the parser SHALL raise a parse error because `xorGateway` is no longer a valid keyword

### Requirement: BPMN generation produces Zeebe-compatible XML
The generator SHALL produce BPMN 2.0 XML with Zeebe namespace extensions. StartEvents and EndEvents SHALL generate standard BPMN events. ScriptCalls SHALL generate `bpmn:scriptTask` with `zeebe:script` extensions using FEEL expressions. ServiceTasks SHALL generate `bpmn:serviceTask` with `zeebe:taskDefinition` (type, retries) and `zeebe:taskHeaders`. Gateway elements with `type: "xor"` SHALL generate `bpmn:exclusiveGateway`. Gateway elements with `type: "parallel"` SHALL generate `bpmn:parallelGateway`. Variable mappings SHALL generate `zeebe:ioMapping` with `zeebe:input` and `zeebe:output` elements. FEEL expressions SHALL be auto-prefixed with `=` if not already present. Default/otherwise flows SHALL be indicated via the `default` attribute on the gateway element in the BPMN XML.

#### Scenario: Generate scriptTask with FEEL
- **WHEN** a scriptCall has `script: "result = x + 1"` and `inputVars: ["x"]`
- **THEN** the BPMN XML SHALL contain a scriptTask with zeebe:script expression and zeebe:ioMapping

#### Scenario: Generate serviceTask with headers
- **WHEN** a serviceTask has `taskType: "api-call"`, `retries: 5`, and headers
- **THEN** the BPMN XML SHALL contain a serviceTask with zeebe:taskDefinition and zeebe:taskHeaders

#### Scenario: Generate exclusive gateway
- **WHEN** a gateway element has `type: "xor"` with two outgoing flows, one conditional and one `otherwise`
- **THEN** the BPMN XML SHALL contain a `bpmn:exclusiveGateway` element with the `default` attribute set to the otherwise flow's ID

#### Scenario: Generate parallel gateway
- **WHEN** a gateway element has `type: "parallel"` with three outgoing flows
- **THEN** the BPMN XML SHALL contain a `bpmn:parallelGateway` element with three outgoing sequence flows and no condition expressions

## REMOVED Requirements

### Requirement: xorGateway keyword
**Reason**: Replaced by the generic `gateway` keyword with `type: "xor"`. The `xorGateway` keyword is removed from the grammar.
**Migration**: Replace `xorGateway "Name" {}` with `gateway "Name" { type: "xor" }`. Replace `default` with `otherwise` in flow expressions.
