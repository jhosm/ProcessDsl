## Context

The DSL currently hardcodes `xorGateway` as the only gateway type and uses `default` as the default-flow marker in the flow section. The DSL is not yet in production, so these are free breaking changes. The design proposal (DSL V2) calls for a generic `gateway` keyword with a `type` property and replacing `default` with `otherwise`.

## Goals / Non-Goals

**Goals:**
- Replace `xorGateway` with `gateway { type: "xor" }` in the grammar, parser, AST, and generator
- Add `parallel` gateway type that generates `bpmn:parallelGateway` in BPMN XML
- Replace `default` with `otherwise` in flow expressions
- Maintain all existing validation rules adapted to the new node type
- Update all examples and tests

**Non-Goals:**
- Inclusive gateway (`type: "inclusive"`) — reserved for a future P1 change
- Gateway shorthand keywords (`xor "Name"`, `parallel "Name"`) — covered by the syntax-sugar change
- Event-based gateway — not in current roadmap

## Decisions

### Decision 1: Single `Gateway` AST node with a `type` enum

Replace the `XorGateway` dataclass with a `Gateway` dataclass carrying a `gateway_type` field. The field uses a string enum (`"xor"`, `"parallel"`) rather than separate classes per type.

**Rationale:** A single node keeps the AST flat and the visitor/generator simple — one branch with a type check instead of N separate visitor methods. Adding inclusive later is a one-line enum extension.

**Alternative considered:** Separate `XorGateway` / `ParallelGateway` classes. Rejected because it multiplies visitor branches and makes the grammar-to-AST mapping more complex for no structural benefit.

### Decision 2: `otherwise` is a grammar-level keyword, not an alias

Replace the `default` token in `grammar.lark` with `otherwise`. The parser will not accept `default` at all — there is no deprecation period since the DSL is pre-production.

**Rationale:** Clean break avoids carrying two code paths. The word `otherwise` reads more naturally in flow expressions and doesn't collide with language reserved words.

### Decision 3: Parallel gateway BPMN generation follows Zeebe semantics

Parallel gateways generate `bpmn:parallelGateway` with no conditions on outgoing flows. Zeebe requires all outgoing flows to be taken (fork) and all incoming flows to arrive (join). The generator will not emit condition expressions on parallel gateway flows.

**Rationale:** Aligns with BPMN 2.0 spec and Zeebe runtime behavior. Validation should warn if conditions are placed on parallel gateway flows.

## Risks / Trade-offs

- **[Breaking change]** → All existing `.bpm` files and tests must be updated. Mitigated by the DSL being pre-production with a small corpus.
- **[Validation gap for parallel gateways]** → Parallel gateways have different structural rules (no conditions, must have matching fork/join). → Add parallel-specific validation rules as part of the validator update.
- **[Type string vs enum]** → Using strings for gateway type is flexible but could allow typos. → The grammar constrains allowed values, so invalid types are caught at parse time.
