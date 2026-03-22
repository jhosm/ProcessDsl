## ADDED Requirements

### Requirement: Timer intermediate catch events
The system SHALL support a `timer` element as an intermediate catch event. The timer element SHALL accept `duration` (wait a fixed time), `date` (wait until a specific date), or `cycle` (repeated timer) properties. Duration values SHALL accept ISO 8601 strings (e.g., `"PT30M"`) or shorthand literals (`30s`, `5m`, `2h`, `1d`, `2h30m`). Shorthand literals SHALL be desugared to ISO 8601 at parse time.

#### Scenario: Parse timer with ISO 8601 duration
- **WHEN** a `.bpm` file contains `timer "Wait" { duration: "PT30M" }`
- **THEN** the parser SHALL produce a TimerEvent AST node with duration="PT30M"

#### Scenario: Parse timer with duration sugar
- **WHEN** a `.bpm` file contains `timer "Wait" { duration: 30m }`
- **THEN** the parser SHALL produce a TimerEvent AST node with duration="PT30M"

#### Scenario: Parse combined duration sugar
- **WHEN** a `.bpm` file contains `timer "Wait" { duration: 2h30m }`
- **THEN** the parser SHALL produce a TimerEvent AST node with duration="PT2H30M"

#### Scenario: Parse timer with day duration
- **WHEN** a `.bpm` file contains `timer "Wait" { duration: 1d }`
- **THEN** the parser SHALL produce a TimerEvent AST node with duration="P1D"

#### Scenario: Generate BPMN for timer intermediate catch
- **WHEN** a timer element with duration "PT30M" is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:intermediateCatchEvent` with a nested `bpmn:timerEventDefinition` containing a `bpmn:timeDuration` element with value "PT30M"

### Requirement: Timer start events
The system SHALL support timer-triggered process starts via `start "Name" { timer: cycle(...) }`. The `cycle` function SHALL accept an ISO 8601 repeating interval string or a duration shorthand. When a start event has a `timer` property, the BPMN output SHALL include a `bpmn:timerEventDefinition` inside the start event.

#### Scenario: Parse timer start with cycle
- **WHEN** a `.bpm` file contains `start "Every Hour" { timer: cycle("R/PT1H") }`
- **THEN** the parser SHALL produce a StartEvent AST node with a timer cycle property of "R/PT1H"

#### Scenario: Parse timer start with cycle sugar
- **WHEN** a `.bpm` file contains `start "Daily" { timer: cycle(1d) }`
- **THEN** the parser SHALL produce a StartEvent AST node with a timer cycle property of "R/P1D"

#### Scenario: Generate BPMN for timer start
- **WHEN** a start event with `timer: cycle("R/PT1H")` is converted to BPMN
- **THEN** the output SHALL contain a `bpmn:startEvent` with a nested `bpmn:timerEventDefinition` containing a `bpmn:timeCycle` element

### Requirement: Boundary timer events
The system SHALL support `onTimer` boundary events nested inside `serviceTask` elements. The `onTimer` element SHALL have a quoted name, `duration` property (ISO 8601 or shorthand), and optional `interrupting` property (default `true`). The boundary event SHALL generate an ID from its name in kebab-case and be referenceable in the flow section.

#### Scenario: Parse interrupting boundary timer
- **WHEN** a serviceTask contains `onTimer "Timeout" { duration: "PT5M" }`
- **THEN** the parser SHALL produce a BoundaryTimerEvent on the parent task with name "Timeout", duration "PT5M", and interrupting=true

#### Scenario: Parse non-interrupting boundary timer
- **WHEN** a serviceTask contains `onTimer "Reminder" { duration: "PT1M", interrupting: false }`
- **THEN** the parser SHALL produce a BoundaryTimerEvent with interrupting=false

#### Scenario: Parse boundary timer with duration sugar
- **WHEN** a serviceTask contains `onTimer "Timeout" { duration: 30s }`
- **THEN** the parser SHALL produce a BoundaryTimerEvent with duration "PT30S"

#### Scenario: Generate BPMN for boundary timer
- **WHEN** a boundary timer event with duration "PT5M" is attached to a serviceTask with ID "call-api"
- **THEN** the BPMN output SHALL contain a `bpmn:boundaryEvent` with `attachedToRef="call-api"`, `cancelActivity="true"`, and a nested `bpmn:timerEventDefinition`

#### Scenario: Reference boundary timer in flow
- **WHEN** a boundary timer named "Timeout" (ID "timeout") has a flow `"timeout" -> "error-handler"` in the flow section
- **THEN** the BPMN output SHALL contain a sequence flow from the boundary event to the error handler element

### Requirement: Boundary error events
The system SHALL support `onError` boundary events nested inside `serviceTask` elements. The `onError` element SHALL have a quoted name, `errorCode` property, and optional `interrupting` property (default `true`). The boundary event SHALL generate an ID from its name in kebab-case and be referenceable in the flow section.

#### Scenario: Parse boundary error event
- **WHEN** a serviceTask contains `onError "API Failure" { errorCode: "API_ERROR" }`
- **THEN** the parser SHALL produce a BoundaryErrorEvent on the parent task with name "API Failure", errorCode "API_ERROR", and interrupting=true

#### Scenario: Generate BPMN for boundary error
- **WHEN** a boundary error event with errorCode "API_ERROR" is attached to a serviceTask with ID "call-api"
- **THEN** the BPMN output SHALL contain a `bpmn:boundaryEvent` with `attachedToRef="call-api"`, `cancelActivity="true"`, and a nested `bpmn:errorEventDefinition` with `errorRef` referencing an error definition with errorCode "API_ERROR"

#### Scenario: Reference boundary error in flow
- **WHEN** a boundary error named "API Failure" (ID "api-failure") has a flow `"api-failure" -> "error-handler"`
- **THEN** the BPMN output SHALL contain a sequence flow from the boundary event to the error handler element

## MODIFIED Requirements

### Requirement: ServiceTask elements have sensible defaults
A `serviceTask` element SHALL default `retries` to `3` when not explicitly specified. Headers, input mappings, and output mappings SHALL default to empty lists. Boundary events SHALL default to an empty list.

#### Scenario: Default retries
- **WHEN** a serviceTask does not specify retries
- **THEN** the AST node SHALL have retries=3

#### Scenario: Default boundary events
- **WHEN** a serviceTask does not contain any `onTimer` or `onError` blocks
- **THEN** the AST node SHALL have an empty boundary_events list

### Requirement: Layout engine produces professional diagram positions
The layout engine SHALL assign horizontal positions via topological level assignment (BFS from start events) and vertical positions within each level. Gateway branches SHALL be spread vertically around the gateway. Boundary events SHALL be positioned on the bottom edge of their parent task element. Edge routing SHALL use straight lines for same-level connections and orthogonal (L-shaped) routing for cross-level connections. The output SHALL include BPMNDiagram with BPMNShape bounds and BPMNEdge waypoints.

#### Scenario: Elements positioned left to right
- **WHEN** a process has start → task → end
- **THEN** the start event SHALL be at level 0 (leftmost), the task at level 1, and the end event at level 2

#### Scenario: Gateway branches spread vertically
- **WHEN** a gateway has two outgoing branches
- **THEN** the branch targets SHALL be positioned at different vertical offsets relative to the gateway

#### Scenario: Boundary event positioned on parent task
- **WHEN** a serviceTask has a boundary timer event
- **THEN** the boundary event shape SHALL be positioned on the bottom edge of the parent task shape
