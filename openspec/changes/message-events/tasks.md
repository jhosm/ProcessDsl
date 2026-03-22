## 1. Grammar

- [ ] 1.1 Extend `start` element rule in `grammar.lark` with optional `message:` property
- [ ] 1.2 Add `receiveMessage` element rule with `message` and `correlationKey` properties
- [ ] 1.3 Add `onMessage` boundary event rule as optional nested child inside `serviceTask` and `subprocess` blocks

## 2. AST

- [ ] 2.1 Extend `StartEvent` dataclass with optional `message` field
- [ ] 2.2 Create `ReceiveMessageEvent` dataclass with name, id, message, correlationKey fields
- [ ] 2.3 Create `BoundaryMessageEvent` dataclass with name, id, message, correlationKey, interrupting fields
- [ ] 2.4 Add `BoundaryMessageEvent` to the boundary_events list type on `ServiceTask` and `Subprocess`

## 3. Parser

- [ ] 3.1 Add transformer for `receiveMessage` rule producing `ReceiveMessageEvent` nodes
- [ ] 3.2 Add transformer for `onMessage` boundary events attached to parent tasks
- [ ] 3.3 Handle message property on start events in the start event transformer

## 4. BPMN Generator

- [ ] 4.1 Generate `bpmn:messageEventDefinition` inside start events with message property
- [ ] 4.2 Generate `bpmn:intermediateCatchEvent` with `bpmn:messageEventDefinition` and `zeebe:subscription` for receiveMessage events
- [ ] 4.3 Generate `bpmn:boundaryEvent` with `bpmn:messageEventDefinition` and `zeebe:subscription` for boundary message events
- [ ] 4.4 Generate deduplicated `bpmn:message` definitions at the BPMN definitions level
- [ ] 4.5 Auto-prefix correlation keys with `=` for FEEL expression format

## 5. Validator

- [ ] 5.1 Validate receiveMessage events have non-empty message and correlationKey
- [ ] 5.2 Validate boundary message events have non-empty message and correlationKey
- [ ] 5.3 Validate message start events have non-empty message name (no correlationKey required)

## 6. Layout Engine

- [ ] 6.1 Position receiveMessage events in normal flow layout (same as intermediate catch events)
- [ ] 6.2 Position boundary message events on parent task edge (same pattern as boundary timer/error)

## 7. Tests

- [ ] 7.1 Add parser tests for message start events
- [ ] 7.2 Add parser tests for receiveMessage intermediate catch events
- [ ] 7.3 Add parser tests for boundary message events (interrupting and non-interrupting)
- [ ] 7.4 Add BPMN generator tests for message event BPMN output (all three variants)
- [ ] 7.5 Add BPMN generator tests for message definition deduplication
- [ ] 7.6 Add validator tests for correlation key requirements
- [ ] 7.7 Add end-to-end test: async webhook process with message events (Example 3 from design doc)
