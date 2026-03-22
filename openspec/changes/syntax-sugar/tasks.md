## 1. Grammar — Shorthand Syntax

- [ ] 1.1 Add optional empty-body alternative (no `{}`) for all element rules in `grammar.lark`
- [ ] 1.2 Add `xor` and `parallel` as gateway keyword aliases in the grammar
- [ ] 1.3 Add inline colon syntax for `serviceTask "Name" : "type"` with optional block
- [ ] 1.4 Add inline colon syntax for `callActivity "Name" : "processId"`
- [ ] 1.5 Add inline colon syntax for `processEntity "Name" : "entityName"`

## 2. Grammar — Flow Inference

- [ ] 2.1 Add flow chain rule: `"a" -> "b" -> "c"` as a multi-target sequence
- [ ] 2.2 Add inline end event syntax: `-> end "Name"` and `-> end` in flow rules
- [ ] 2.3 Add parallel bracket syntax: `["a", "b", "c"]` as flow targets/sources
- [ ] 2.4 Add `as "name"` modifier for naming implicit join gateways

## 3. Parser — Shorthand Desugaring

- [ ] 3.1 Add transformer for empty-body elements producing standard AST nodes with defaults
- [ ] 3.2 Add transformer for `xor`/`parallel` keywords producing Gateway AST nodes with correct type
- [ ] 3.3 Add transformer for inline colon on serviceTask setting taskType
- [ ] 3.4 Add transformer for inline colon on callActivity setting processId and propagateAllVariables=true
- [ ] 3.5 Add transformer for inline colon on processEntity setting entityName

## 4. Parser — Flow Inference Desugaring

- [ ] 4.1 Implement flow chain desugaring: split chain into individual Flow edges
- [ ] 4.2 Implement inline end event desugaring: create EndEvent nodes and flows
- [ ] 4.3 Implement implicit XOR insertion: detect conditional flows on non-gateway sources and insert Gateway nodes
- [ ] 4.4 Implement parallel bracket desugaring: create fork/join Gateway nodes and connecting flows
- [ ] 4.5 Implement named joins: assign `as "name"` ID to implicit join gateways

## 5. Validator

- [ ] 5.1 Validate implicit element IDs don't collide with explicit declarations
- [ ] 5.2 Validate implicit gateways pass the same structural rules as explicit gateways
- [ ] 5.3 Validate inline end events are properly connected

## 6. Tests — Shorthand Syntax

- [ ] 6.1 Add parser tests: empty-body shorthand for each element type
- [ ] 6.2 Add parser tests: `xor` and `parallel` keyword shorthands (with and without block)
- [ ] 6.3 Add parser tests: inline colon for serviceTask, callActivity, processEntity
- [ ] 6.4 Add equivalence tests: shorthand and full forms produce identical AST nodes
- [ ] 6.5 Add parser tests: combined shorthand + block form (`serviceTask "X" : "t" { retries: 3 }`)

## 7. Tests — Flow Inference

- [ ] 7.1 Add parser tests: flow chains of varying lengths
- [ ] 7.2 Add parser tests: inline named and unnamed end events
- [ ] 7.3 Add parser tests: implicit XOR insertion from conditional flows
- [ ] 7.4 Add parser tests: no implicit XOR when source is a declared gateway
- [ ] 7.5 Add parser tests: parallel bracket fork/join with 2 and 3+ branches
- [ ] 7.6 Add parser tests: named joins with `as`
- [ ] 7.7 Add parser tests: combined sugar (chains + inline ends + parallel + implicit XOR)
- [ ] 7.8 Add BPMN generator tests: processes using all sugar forms produce correct BPMN XML
- [ ] 7.9 Add end-to-end test: Order Processing example (Example 1 from design doc) using full sugar
