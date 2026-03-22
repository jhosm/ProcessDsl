## Why

The DSL V2 introduces many new element types, and real-world processes tend to have a lot of structural boilerplate: empty-body elements, gateways that only specify a type, service tasks with just a type, and verbose flow sections with one edge per line. Two categories of syntactic sugar address this: **shorthand syntax** (concise element declarations) and **flow inference** (letting the flow section express routing constructs implicitly). Together they can eliminate 50%+ of the lines in typical process definitions while keeping the full form available for complex cases.

## What Changes

**Shorthand syntax (Section 9):**
- Empty body elements: drop `{}` when no properties (e.g., `start "Begin"` instead of `start "Begin" {}`)
- Gateway type as keyword: `xor "Decision"` and `parallel "Fork"` as sugar for `gateway "Name" { type: "..." }`
- Inline type colon: `serviceTask "X" : "type"` for tasks with only a type
- Inline processId: `callActivity "X" : "process-id"` (implies `propagateAllVariables: true`)
- Inline entityName: `processEntity "X" : "EntityName"`
- Combined shorthand + block: `serviceTask "X" : "type" { retries: 3 }` for inline type with extra props

**Flow inference (Section 10):**
- Flow chains: `"a" -> "b" -> "c" -> "d"` instead of separate edges
- Inline end events: `-> end "Name"` or `-> end` in flow section
- Implicit XOR: conditions on a non-gateway source auto-insert an XOR gateway
- Parallel `[...]`: `"a" -> ["b", "c"] -> "d"` creates implicit fork/join gateways
- Named joins: `[...] as "name"` assigns an ID to the implicit join gateway

## Capabilities

### New Capabilities

### Modified Capabilities
- `dsl-engine`: Grammar extended with shorthand syntax alternatives and flow inference constructs; parser desugars all forms to canonical AST; BPMN generator handles implicit elements

## Impact

- **Grammar** (`grammar.lark`): Alternative rules for shorthand declarations, flow chain rule, inline end/parallel bracket syntax in flow
- **Parser** (`parser.py`): Desugaring logic in transformer — shorthands expand to canonical AST nodes, flow inference generates implicit gateway/end nodes
- **BPMN Generator** (`bpmn_generator.py`): No changes needed if desugaring is complete at the AST level
- **Validator** (`validator.py`): Validates the expanded AST (implicit elements must pass the same rules as explicit ones)
- **Tests**: Both shorthand and expanded forms must produce identical AST/BPMN output
