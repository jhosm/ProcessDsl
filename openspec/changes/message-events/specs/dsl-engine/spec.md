## ADDED Requirements

### Requirement: Message start events
The system SHALL support message-triggered process starts via `start "Name" { message: "message-name" }`. When a start event has a `message` property, the BPMN output SHALL include a `bpmn:messageEventDefinition` inside the start event referencing a `bpmn:message` definition. Message start events SHALL NOT require a correlation key.

#### Scenario: Parse message start event
- **WHEN** a `.bpm` file contains `start "Order Received" { message: "new-order" }`
- **THEN** the parser SHALL produce a StartEvent AST node with message="new-order"

#### Scenario: Generate BPMN for message start
- **WHEN** a start event with `message: "new-order"` is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:startEvent` with a nested `bpmn:messageEventDefinition` and a `bpmn:message` definition at the definitions level with name "new-order"

### Requirement: Receive message intermediate catch events
The system SHALL support a `receiveMessage` element as an intermediate catch event. The element SHALL accept `message` (required) and `correlationKey` (required) properties. The correlation key SHALL be treated as a FEEL expression.

#### Scenario: Parse receiveMessage event
- **WHEN** a `.bpm` file contains `receiveMessage "Wait for Confirmation" { message: "payment-confirmed", correlationKey: "orderId" }`
- **THEN** the parser SHALL produce a ReceiveMessageEvent AST node with message="payment-confirmed" and correlationKey="orderId"

#### Scenario: Generate BPMN for receiveMessage
- **WHEN** a receiveMessage with message "payment-confirmed" and correlationKey "orderId" is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:intermediateCatchEvent` with a `bpmn:messageEventDefinition`, a `bpmn:message` definition, and a Zeebe `zeebe:subscription` extension with `correlationKey="=orderId"`

#### Scenario: Reject receiveMessage without correlationKey
- **WHEN** a receiveMessage element has no `correlationKey` property
- **THEN** validation SHALL return an error requiring a correlation key

### Requirement: Boundary message events
The system SHALL support `onMessage` boundary events nested inside `serviceTask` and `subprocess` elements. The `onMessage` element SHALL accept `message` (required), `correlationKey` (required), and `interrupting` (default `true`) properties. The boundary event SHALL generate an ID from its name and be referenceable in the flow section.

#### Scenario: Parse boundary message event
- **WHEN** a serviceTask contains `onMessage "Cancellation" { message: "cancel-request", correlationKey: "orderId", interrupting: true }`
- **THEN** the parser SHALL produce a BoundaryMessageEvent on the parent task with message="cancel-request", correlationKey="orderId", and interrupting=true

#### Scenario: Generate BPMN for boundary message
- **WHEN** a boundary message event with message "cancel-request" and correlationKey "orderId" is attached to a serviceTask with ID "long-process"
- **THEN** the BPMN output SHALL contain a `bpmn:boundaryEvent` with `attachedToRef="long-process"`, `cancelActivity="true"`, a nested `bpmn:messageEventDefinition`, and a Zeebe subscription extension

#### Scenario: Reference boundary message in flow
- **WHEN** a boundary message named "Cancellation" (ID "cancellation") has a flow `"cancellation" -> "handle-cancel"`
- **THEN** the BPMN output SHALL contain a sequence flow from the boundary event to the handler element

### Requirement: Message definitions are deduplicated
The system SHALL generate a single `bpmn:message` definition in the BPMN `definitions` section for each unique message name, even when multiple elements reference the same message name. All referencing elements SHALL use `messageRef` to point to the shared definition.

#### Scenario: Shared message name
- **WHEN** a start event and a boundary event both reference message name "order-update"
- **THEN** the BPMN output SHALL contain exactly one `bpmn:message` definition with name "order-update" and both events SHALL reference it via `messageRef`

## MODIFIED Requirements

### Requirement: DSL grammar supports BPM process definitions
The system SHALL parse `.bpm` files containing process definitions with a name, optional id, and optional version. The grammar SHALL support element types: `start`, `end`, `scriptCall`, `serviceTask`, `processEntity`, `gateway`, and `receiveMessage`. The `start` element SHALL accept optional `timer:` and `message:` properties for event-triggered starts. Task elements SHALL accept optional `onMessage` boundary events in addition to `onTimer` and `onError`.

#### Scenario: Parse a minimal process
- **WHEN** a `.bpm` file contains a process with a start, processEntity, and end element connected by flows
- **THEN** the parser SHALL produce an AST with a Process node containing the declared elements and flows

#### Scenario: Parse conditional flows
- **WHEN** a flow uses `when "expression"` or `otherwise` modifiers
- **THEN** the parser SHALL produce Flow nodes with the condition expression or is_default flag set accordingly

#### Scenario: Parse receiveMessage element
- **WHEN** a `.bpm` file contains a `receiveMessage` element with message and correlationKey
- **THEN** the parser SHALL produce a ReceiveMessageEvent AST node
