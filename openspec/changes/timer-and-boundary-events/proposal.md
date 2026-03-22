## Why

The current DSL has no support for timer events or boundary events — both are essential BPMN constructs for real-world workflows. Timer events enable scheduled process starts, wait states, and timeouts. Error boundary events enable structured error handling on tasks. Without these, processes cannot model timeouts, retries with escalation, or scheduled triggers — all P0 requirements.

## What Changes

- Add `timer` intermediate catch event element with `duration`, `date`, and `cycle` properties
- Extend `start` element to support `timer: cycle(...)` for timer-triggered process starts
- Add duration syntactic sugar (`30s`, `5m`, `2h`, `1d`) as alternatives to ISO 8601 strings
- Add `onTimer` boundary event syntax nested inside task/subprocess elements
- Add `onError` boundary event syntax nested inside task/subprocess elements
- Both boundary event types support `interrupting` property (default `true`)
- Boundary events generate IDs from their name and are referenceable in the flow section
- BPMN generation for all timer and boundary event variants

## Capabilities

### New Capabilities

### Modified Capabilities
- `dsl-engine`: Grammar, AST, parser, validator, and BPMN generator extended with timer events, duration sugar, and boundary events (onTimer, onError) nested inside tasks

## Impact

- **Grammar** (`grammar.lark`): New `timer` element rule, `onTimer`/`onError` nested rules inside task blocks, duration literal tokens, `cycle()` function syntax
- **AST** (`ast_nodes.py`): New `TimerEvent`, `BoundaryTimerEvent`, `BoundaryErrorEvent` dataclasses; `ServiceTask` extended with optional boundary events list
- **Parser** (`parser.py`): Transformer for timer elements, boundary event nesting, duration sugar conversion to ISO 8601
- **BPMN Generator** (`bpmn_generator.py`): Emit `bpmn:intermediateCatchEvent` with `bpmn:timerEventDefinition`, `bpmn:boundaryEvent` with `attachedToRef`, `cancelActivity` attribute
- **Validator** (`validator.py`): Validate boundary events reference valid parent tasks, timer properties are well-formed
- **Layout Engine** (`layout_engine.py`): Position boundary events relative to their parent task
