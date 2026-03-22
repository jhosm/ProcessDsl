## ADDED Requirements

### Requirement: Empty body shorthand
The system SHALL allow element declarations without `{}` when no properties are specified. `start "Begin"` SHALL be equivalent to `start "Begin" {}`. This shorthand SHALL apply to all element types: `start`, `end`, `gateway`, `serviceTask`, `scriptCall`, `processEntity`, `timer`, `receiveMessage`.

#### Scenario: Parse start without braces
- **WHEN** a `.bpm` file contains `start "Begin"` with no `{}`
- **THEN** the parser SHALL produce a StartEvent AST node identical to `start "Begin" {}`

#### Scenario: Parse end without braces
- **WHEN** a `.bpm` file contains `end "Done"` with no `{}`
- **THEN** the parser SHALL produce an EndEvent AST node identical to `end "Done" {}`

### Requirement: Gateway type as keyword shorthand
The system SHALL accept `xor "Name"` as shorthand for `gateway "Name" { type: "xor" }` and `parallel "Name"` as shorthand for `gateway "Name" { type: "parallel" }`. The shorthand forms SHALL produce identical Gateway AST nodes. Block form SHALL be supported for extra properties: `xor "Name" { id: "custom" }`.

#### Scenario: Parse xor shorthand
- **WHEN** a `.bpm` file contains `xor "Decision"`
- **THEN** the parser SHALL produce a Gateway AST node with name "Decision" and gateway_type "xor"

#### Scenario: Parse parallel shorthand
- **WHEN** a `.bpm` file contains `parallel "Fork"`
- **THEN** the parser SHALL produce a Gateway AST node with name "Fork" and gateway_type "parallel"

#### Scenario: Parse xor shorthand with block
- **WHEN** a `.bpm` file contains `xor "Decision" { id: "my-id" }`
- **THEN** the parser SHALL produce a Gateway AST node with name "Decision", gateway_type "xor", and id "my-id"

### Requirement: Inline type colon shorthand for service tasks
The system SHALL accept `serviceTask "Name" : "type-value"` as shorthand for `serviceTask "Name" { type: "type-value" }`. The combined form `serviceTask "Name" : "type-value" { retries: 3 }` SHALL set both the type and additional properties.

#### Scenario: Parse service task with inline type
- **WHEN** a `.bpm` file contains `serviceTask "Check Stock" : "check-stock"`
- **THEN** the parser SHALL produce a ServiceTask AST node with name "Check Stock" and taskType "check-stock"

#### Scenario: Parse service task with inline type and block
- **WHEN** a `.bpm` file contains `serviceTask "Call API" : "api-call" { retries: 5 }`
- **THEN** the parser SHALL produce a ServiceTask AST node with taskType "api-call" and retries=5

### Requirement: Inline processId shorthand for call activities
The system SHALL accept `callActivity "Name" : "process-id"` as shorthand for `callActivity "Name" { processId: "process-id", propagateAllVariables: true }`. The shorthand form SHALL default to `propagateAllVariables: true`.

#### Scenario: Parse call activity with inline processId
- **WHEN** a `.bpm` file contains `callActivity "Validate Payment" : "payment-validation"`
- **THEN** the parser SHALL produce a CallActivity AST node with processId "payment-validation" and propagateAllVariables=true

### Requirement: Inline entityName shorthand for process entities
The system SHALL accept `processEntity "Name" : "EntityName"` as shorthand for `processEntity "Name" { entityName: "EntityName" }`.

#### Scenario: Parse processEntity with inline entity name
- **WHEN** a `.bpm` file contains `processEntity "Load Order" : "Order"`
- **THEN** the parser SHALL produce a ProcessEntity AST node with name "Load Order" and entityName "Order"

### Requirement: Flow chains
The system SHALL support chained flow expressions where `"a" -> "b" -> "c"` desugars to two separate flows: `"a" -> "b"` and `"b" -> "c"`. Conditions (`when`, `otherwise`) SHALL apply only to the last edge in a chain.

#### Scenario: Parse flow chain
- **WHEN** the flow section contains `"a" -> "b" -> "c" -> "d"`
- **THEN** the parser SHALL produce three Flow nodes: ("a","b"), ("b","c"), ("c","d")

#### Scenario: Flow chain with condition on last edge
- **WHEN** the flow section contains `"a" -> "b" -> "c" when "x > 0"`
- **THEN** the parser SHALL produce Flow("a","b") with no condition and Flow("b","c") with condition "x > 0"

### Requirement: Inline end events in flow
The system SHALL support `-> end "Name"` and `-> end` in flow expressions. Inline end events SHALL generate EndEvent nodes with IDs derived from their name (or ID `"end"` for unnamed). These implicit end events SHALL appear in the BPMN output as standard end events.

#### Scenario: Parse inline named end
- **WHEN** the flow section contains `"notify-customer" -> end "Order Complete"`
- **THEN** the parser SHALL produce an EndEvent node with name "Order Complete" and ID "order-complete", and a Flow from "notify-customer" to "order-complete"

#### Scenario: Parse inline unnamed end
- **WHEN** the flow section contains `"last-task" -> end`
- **THEN** the parser SHALL produce an EndEvent node with ID "end" and a Flow from "last-task" to "end"

### Requirement: Implicit XOR from conditional flows on non-gateway elements
When a non-gateway element has outgoing flows with `when` or `otherwise` conditions, the system SHALL automatically insert an XOR gateway between the source element and the conditional targets. The implicit gateway SHALL have ID `<source-id>-gateway`.

#### Scenario: Implicit XOR insertion
- **WHEN** the flow section contains `"settlement-delay" -> "record-success" when "status == 'done'"` and `"settlement-delay" -> "record-failure" otherwise`, and "settlement-delay" is a timer element (not a gateway)
- **THEN** the parser SHALL produce: a Gateway node with ID "settlement-delay-gateway" and type "xor", a Flow from "settlement-delay" to "settlement-delay-gateway", and conditional flows from "settlement-delay-gateway" to the targets

#### Scenario: No implicit XOR when source is a gateway
- **WHEN** the flow section contains `"my-gateway" -> "a" when "x"` and "my-gateway" is a declared gateway element
- **THEN** the parser SHALL NOT insert an implicit gateway — the conditions apply directly to the declared gateway

### Requirement: Parallel fork/join with bracket syntax
The system SHALL support `"source" -> ["a", "b", "c"] -> "target"` in flow expressions. The `[...]` syntax SHALL create implicit parallel gateway nodes: a fork gateway after the source and a join gateway before the target. The fork gateway ID SHALL be `<source-id>-fork` and the join gateway ID SHALL be `<target-id>-join`.

#### Scenario: Parse parallel fork and join
- **WHEN** the flow section contains `"load-order" -> ["check-inventory", "validate-payment"] -> "next-step"`
- **THEN** the parser SHALL produce: a parallel Gateway "load-order-fork", a parallel Gateway "next-step-join", flows from source to fork, fork to each branch, each branch to join, and join to target

#### Scenario: Parse fork-only (no join target)
- **WHEN** the flow section contains `"start" -> ["a", "b"]`
- **THEN** the parser SHALL produce a parallel fork gateway and flows from fork to each branch

### Requirement: Named joins with `as`
The system SHALL support `[...] as "name"` to assign a custom ID to an implicit join gateway, making it referenceable in subsequent flow expressions.

#### Scenario: Parse named join
- **WHEN** the flow section contains `"load-order" -> ["check-inventory", "validate-payment"] as "validated"` followed by `"validated" -> "next" when "valid"`
- **THEN** the parser SHALL produce a parallel join gateway with ID "validated" (instead of the auto-generated ID), referenceable in subsequent flows

## MODIFIED Requirements

### Requirement: DSL grammar supports BPM process definitions
The system SHALL parse `.bpm` files containing process definitions with a name, optional id, and optional version. The grammar SHALL support element types in both full form (`keyword "Name" { props }`) and shorthand forms (empty body without braces, inline type with colon, gateway type as keyword). The `flow` block SHALL support chains, inline end events, parallel bracket syntax, named joins, and implicit XOR gateway insertion from conditional flows.

#### Scenario: Parse a minimal process
- **WHEN** a `.bpm` file contains a process with a start, processEntity, and end element connected by flows
- **THEN** the parser SHALL produce an AST with a Process node containing the declared elements and flows

#### Scenario: Parse shorthand and full forms together
- **WHEN** a `.bpm` file mixes `start "Begin"` (shorthand) with `serviceTask "X" { type: "y", retries: 3 }` (full form)
- **THEN** the parser SHALL produce correct AST nodes for both forms

#### Scenario: Parse complex flow with all sugar
- **WHEN** a flow section contains chains, inline ends, parallel brackets, and implicit XOR
- **THEN** the parser SHALL produce a fully expanded set of elements and flows with all implicit nodes generated
