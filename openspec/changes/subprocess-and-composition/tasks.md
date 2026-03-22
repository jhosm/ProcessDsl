## 1. Grammar

- [ ] 1.1 Add `subprocess` rule to `grammar.lark` as a recursive container with child elements and `flow {}` block
- [ ] 1.2 Add `callActivity` rule with `processId`, `propagateAllVariables`, `inputMappings`, `outputMappings` properties
- [ ] 1.3 Add `forEach`, `as`, `parallel` modifier properties to `serviceTask` and `subprocess` rules
- [ ] 1.4 Allow `onTimer` and `onError` boundary events inside `subprocess` blocks

## 2. AST

- [ ] 2.1 Create `Subprocess` dataclass in `ast_nodes.py` with child elements, flows, boundary_events, and multi-instance fields
- [ ] 2.2 Create `CallActivity` dataclass with processId, propagateAllVariables, inputMappings, outputMappings
- [ ] 2.3 Add `forEach`, `as_var`, `parallel` optional fields to `ServiceTask` and `Subprocess` dataclasses

## 3. Parser

- [ ] 3.1 Add transformer for `subprocess` rule with recursive parsing of child elements and internal flow
- [ ] 3.2 Add transformer for `callActivity` rule producing `CallActivity` nodes
- [ ] 3.3 Add transformer logic for `forEach`/`as`/`parallel` modifiers on tasks and subprocesses

## 4. BPMN Generator

- [ ] 4.1 Generate `bpmn:subProcess` with nested child elements and internal sequence flows
- [ ] 4.2 Generate `bpmn:callActivity` with `zeebe:calledElement` extension (processId, propagation flag)
- [ ] 4.3 Generate `zeebe:ioMapping` on call activities with explicit variable mappings
- [ ] 4.4 Generate `bpmn:multiInstanceLoopCharacteristics` with `isSequential` flag and Zeebe input/output collection extensions

## 5. Validator

- [ ] 5.1 Add recursive validation for subprocess internal structure (start/end events, flow references, reachability)
- [ ] 5.2 Validate callActivity processId is non-empty and valid
- [ ] 5.3 Validate multi-instance `forEach` has a corresponding `as` variable
- [ ] 5.4 Validate element ID uniqueness across subprocess boundaries

## 6. Layout Engine

- [ ] 6.1 Implement subprocess container box layout with internal element positioning
- [ ] 6.2 Position call activity elements using standard task dimensions
- [ ] 6.3 Handle multi-instance marker rendering (three vertical/horizontal lines at bottom of task)

## 7. Tests

- [ ] 7.1 Add parser tests for subprocess with internal elements and flow
- [ ] 7.2 Add parser tests for subprocess with boundary events
- [ ] 7.3 Add parser tests for callActivity with propagateAll and explicit mappings
- [ ] 7.4 Add parser tests for multi-instance on serviceTask and subprocess
- [ ] 7.5 Add BPMN generator tests for subprocess XML output
- [ ] 7.6 Add BPMN generator tests for callActivity with zeebe:calledElement
- [ ] 7.7 Add BPMN generator tests for multi-instance loop characteristics
- [ ] 7.8 Add validator tests for subprocess internal structure validation
- [ ] 7.9 Add end-to-end test: batch processing with multi-instance subprocess (Example 2 from design doc)
