## 1. Grammar

- [ ] 1.1 Add `timer` element rule to `grammar.lark` with `duration`, `date`, and `cycle` properties
- [ ] 1.2 Add duration shorthand token patterns (`\d+[smhd]`) and combination patterns to the grammar
- [ ] 1.3 Add `cycle(...)` function syntax to the grammar for timer start events
- [ ] 1.4 Extend `start` element rule to accept optional `timer:` property
- [ ] 1.5 Add `onTimer` and `onError` rules as optional nested children inside `serviceTask` blocks
- [ ] 1.6 Add `interrupting` and `errorCode` properties to boundary event rules

## 2. AST

- [ ] 2.1 Create `TimerEvent` dataclass in `ast_nodes.py` with name, id, duration/date/cycle fields
- [ ] 2.2 Create `BoundaryTimerEvent` dataclass with name, id, duration, interrupting fields
- [ ] 2.3 Create `BoundaryErrorEvent` dataclass with name, id, errorCode, interrupting fields
- [ ] 2.4 Extend `StartEvent` dataclass with optional `timer` field
- [ ] 2.5 Extend `ServiceTask` dataclass with optional `boundary_events` list field

## 3. Parser

- [ ] 3.1 Add transformer methods for `timer` element producing `TimerEvent` nodes
- [ ] 3.2 Add duration sugar desugaring logic (convert `30s` → `"PT30S"`, `2h30m` → `"PT2H30M"`, `1d` → `"P1D"`)
- [ ] 3.3 Add transformer for `cycle()` function in timer start events
- [ ] 3.4 Add transformer methods for `onTimer` and `onError` producing boundary event nodes attached to parent task

## 4. BPMN Generator

- [ ] 4.1 Generate `bpmn:intermediateCatchEvent` with `bpmn:timerEventDefinition` for timer elements
- [ ] 4.2 Generate `bpmn:timerEventDefinition` inside `bpmn:startEvent` for timer start events
- [ ] 4.3 Generate `bpmn:boundaryEvent` elements with `attachedToRef` and `cancelActivity` for boundary timer events
- [ ] 4.4 Generate `bpmn:boundaryEvent` with `bpmn:errorEventDefinition` for boundary error events
- [ ] 4.5 Generate BPMN `bpmn:error` definitions at process level for referenced error codes

## 5. Validator

- [ ] 5.1 Validate timer events have at least one of duration, date, or cycle
- [ ] 5.2 Validate boundary events reference valid parent tasks
- [ ] 5.3 Validate boundary event IDs are unique and don't collide with element IDs
- [ ] 5.4 Validate duration strings are valid ISO 8601 or were properly desugared

## 6. Layout Engine

- [ ] 6.1 Position timer intermediate catch events in the normal flow layout
- [ ] 6.2 Position boundary events on the bottom edge of their parent task shape

## 7. Tests

- [ ] 7.1 Add parser tests for timer intermediate catch events (ISO 8601 and sugar variants)
- [ ] 7.2 Add parser tests for timer start events with cycle
- [ ] 7.3 Add parser tests for boundary timer events (interrupting and non-interrupting)
- [ ] 7.4 Add parser tests for boundary error events
- [ ] 7.5 Add duration sugar conversion unit tests
- [ ] 7.6 Add BPMN generator tests for all timer and boundary event BPMN output
- [ ] 7.7 Add validator tests for boundary event validation rules
- [ ] 7.8 Add end-to-end test with a process using timer start, boundary timeout, and error handling
