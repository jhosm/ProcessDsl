## Why

The current DSL has no way to compose processes — everything is a flat sequence of tasks in a single process. Real-world BPM requires embedded subprocesses (grouping related steps with their own internal flow), call activities (invoking reusable processes), and multi-instance execution (running a task or subprocess for each item in a collection). These three composition primitives are P0 requirements that unlock hierarchical process design.

## What Changes

- Add `subprocess` element containing its own elements, flow section, and optional boundary events
- Add `callActivity` element that invokes another process by ID with variable propagation or explicit mappings
- Add `forEach` / `as` / `parallel` modifiers applicable to any task or subprocess for multi-instance execution
- BPMN generation for `bpmn:subProcess`, `bpmn:callActivity`, and multi-instance loop characteristics

## Capabilities

### New Capabilities

### Modified Capabilities
- `dsl-engine`: Grammar, AST, parser, validator, and BPMN generator extended with subprocess, call activity, and multi-instance constructs

## Impact

- **Grammar** (`grammar.lark`): New `subprocess` rule (recursive — contains elements and flow), `callActivity` rule with `processId`/mappings, `forEach`/`as`/`parallel` modifier properties on tasks and subprocesses
- **AST** (`ast_nodes.py`): New `Subprocess` dataclass (contains child elements and flows), `CallActivity` dataclass, multi-instance fields on `ServiceTask`/`Subprocess`
- **Parser** (`parser.py`): Transformer for subprocess (recursive descent into child elements), call activity, multi-instance modifiers
- **BPMN Generator** (`bpmn_generator.py`): Emit `bpmn:subProcess` with nested elements, `bpmn:callActivity` with `zeebe:calledElement`, `bpmn:multiInstanceLoopCharacteristics`
- **Validator** (`validator.py`): Validate subprocess internal structure (must have start/end, valid internal flows), call activity references, multi-instance collection references
- **Layout Engine** (`layout_engine.py`): Subprocess needs a container box with internal layout; call activity uses standard task dimensions
