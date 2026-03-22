## Why

The current DSL has a hardcoded `xorGateway` keyword that only supports exclusive gateways. Adding parallel gateways (P0) or inclusive gateways (P1) would require new keywords each time. Replacing it with a generic `gateway` keyword with a `type` property provides a scalable foundation for all gateway types. Additionally, the flow section uses `default` for default flows, which conflicts with reserved keywords in several target languages — replacing it with `otherwise` improves readability and avoids confusion.

## What Changes

- **BREAKING**: Remove the `xorGateway` keyword entirely
- **BREAKING**: Replace `default` with `otherwise` in flow sequence expressions
- Add a new `gateway` keyword with a required `type` property supporting `"xor"` and `"parallel"` (with `"inclusive"` reserved for future P1)
- Add `parallel` gateway type to BPMN generation, producing `bpmn:parallelGateway` elements
- Update flow condition parsing to recognize `otherwise` as the default flow marker

## Capabilities

### New Capabilities

### Modified Capabilities
- `dsl-engine`: Grammar changes to replace `xorGateway` with `gateway { type }`, add `parallel` gateway support, and replace `default` with `otherwise` in flow syntax

## Impact

- **Grammar** (`grammar.lark`): `xorGateway` rule removed, `gateway` rule added with `type` property; flow rule updated to use `otherwise` instead of `default`
- **AST** (`ast_nodes.py`): `XorGateway` node replaced with a generic `Gateway` node carrying a `type` field
- **Parser** (`parser.py`): Transformer updated for new grammar rules
- **BPMN Generator** (`bpmn_generator.py`): Must emit `bpmn:exclusiveGateway` or `bpmn:parallelGateway` based on type; default flow handling updated
- **Validator** (`validator.py`): Gateway validation updated for new node type
- **Tests**: All tests referencing `xorGateway` or `default` must be migrated
- **Examples**: All `.bpm` example files must be updated to use the new syntax
