## 1. Grammar and AST

- [ ] 1.1 Update `grammar.lark`: remove `xorGateway` rule, add `gateway` rule with required `type` property accepting `"xor"` and `"parallel"`
- [ ] 1.2 Update `grammar.lark`: replace `default` keyword with `otherwise` in flow sequence rules
- [ ] 1.3 Replace `XorGateway` AST node in `ast_nodes.py` with a `Gateway` dataclass containing `gateway_type` field

## 2. Parser

- [ ] 2.1 Update `parser.py` transformer to handle the new `gateway` grammar rule and produce `Gateway` AST nodes
- [ ] 2.2 Update `parser.py` transformer to handle `otherwise` in flow rules, mapping to `is_default=True` on Flow nodes

## 3. BPMN Generator

- [ ] 3.1 Update `bpmn_generator.py` to handle `Gateway` nodes: emit `bpmn:exclusiveGateway` for `type: "xor"` and `bpmn:parallelGateway` for `type: "parallel"`
- [ ] 3.2 Update default-flow handling in the generator to use the `otherwise` semantics (setting `default` attribute on gateway XML elements)

## 4. Validator

- [ ] 4.1 Update `validator.py` to validate `Gateway` nodes instead of `XorGateway`
- [ ] 4.2 Add validation rule: parallel gateways SHALL NOT have conditional (`when`) flows on their outgoing edges

## 5. Layout Engine

- [ ] 5.1 Update `layout_engine.py` to handle `Gateway` node type for positioning (replacing `XorGateway` references)

## 6. Tests

- [ ] 6.1 Migrate all `xorGateway` references in `test_parser.py` to use `gateway { type: "xor" }` syntax
- [ ] 6.2 Migrate all `default` flow references in tests to use `otherwise`
- [ ] 6.3 Add parser tests for `gateway { type: "parallel" }`
- [ ] 6.4 Add BPMN generator tests for parallel gateway output (`bpmn:parallelGateway`)
- [ ] 6.5 Add validator tests for parallel gateway rules (no conditions on outgoing flows)
- [ ] 6.6 Add parser tests that `xorGateway` keyword is rejected

## 7. Examples and CLI

- [ ] 7.1 Update all `.bpm` example files to use `gateway` with `type` instead of `xorGateway`
- [ ] 7.2 Update all `.bpm` example files to use `otherwise` instead of `default`
- [ ] 7.3 Verify CLI `convert`, `validate`, and `info` commands work with updated examples
