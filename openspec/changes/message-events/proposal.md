## Why

The current DSL cannot model asynchronous message-based interactions — a core BPMN capability for event-driven architectures. Message events enable processes to be triggered by external messages (message start), wait for external callbacks (intermediate catch), and react to messages during task execution (boundary). Without these, workflows that depend on webhooks, external system callbacks, or inter-process messaging cannot be modeled.

## What Changes

- Extend `start` element to support `message: "name"` for message-triggered process starts
- Add `receiveMessage` intermediate catch event element with `message` and `correlationKey` properties
- Add `onMessage` boundary event syntax nested inside task elements with `message`, `correlationKey`, and `interrupting` properties
- BPMN generation for message start events, intermediate message catch events, and boundary message events with Zeebe message subscription extensions

## Capabilities

### New Capabilities

### Modified Capabilities
- `dsl-engine`: Grammar, AST, parser, validator, and BPMN generator extended with message start events, receiveMessage intermediate catch events, and onMessage boundary events

## Impact

- **Grammar** (`grammar.lark`): Extend `start` rule with `message:` property, add `receiveMessage` element rule, add `onMessage` nested rule inside task blocks
- **AST** (`ast_nodes.py`): New `ReceiveMessageEvent` dataclass, `BoundaryMessageEvent` dataclass; `StartEvent` extended with optional `message` field
- **Parser** (`parser.py`): Transformers for message events and correlation key handling
- **BPMN Generator** (`bpmn_generator.py`): Emit `bpmn:messageEventDefinition` inside start events, `bpmn:intermediateCatchEvent` for receive message, `bpmn:boundaryEvent` for message boundary; generate `bpmn:message` definitions and Zeebe subscription extensions with correlation keys
- **Validator** (`validator.py`): Validate message names are non-empty, correlation keys present on intermediate and boundary message events
- **Layout Engine** (`layout_engine.py`): Position receive message events in normal flow; boundary message events on parent task edge
