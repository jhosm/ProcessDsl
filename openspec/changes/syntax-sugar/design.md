## Context

The DSL V2 introduces many new element types, making process definitions potentially verbose. Sections 9 (Shorthand Syntax) and 10 (Flow Inference) of the design doc propose syntactic sugar to reduce boilerplate. This sugar layer sits on top of the canonical element/flow model and desugars to the same AST that explicit declarations produce.

## Goals / Non-Goals

**Goals:**
- All shorthand forms desugar to the same AST as their full equivalents
- Flow chains, inline ends, implicit XOR, and parallel brackets desugar in the parser phase
- The BPMN generator and validator see no difference between sugar and explicit declarations
- All sugar forms are optional — the full form always works
- Sugar and explicit forms can coexist in the same process

**Non-Goals:**
- Pretty-printing or reformatting sugar back from AST — one-way desugaring only
- Optimizing the desugared AST (e.g., merging consecutive gateways)
- IDE/editor support for sugar autocompletion

## Decisions

### Decision 1: Desugaring happens entirely in the parser/transformer phase

All shorthand and flow inference constructs are resolved in the Lark transformer. The AST contains only canonical node types (Gateway, ServiceTask, etc.) and explicit flows. Downstream phases (validator, generator) are unaware of sugar.

**Rationale:** Single responsibility — the parser owns syntax, other phases own semantics. This prevents sugar-awareness from leaking into the generator or validator, keeping them simple.

**Alternative considered:** A separate desugaring pass after parsing. Rejected because Lark transformers naturally handle this during tree-to-AST conversion.

### Decision 2: Implicit elements get deterministic auto-generated IDs

- Implicit XOR gateways: `<source-id>-gateway`
- Implicit parallel fork: `<source-id>-fork`
- Implicit parallel join: `<target-id>-join` (or the `as "name"` ID if provided)
- Inline end events: kebab-case of name, or `end` for unnamed

**Rationale:** Deterministic IDs make processes debuggable and testable. Users can predict what the generated BPMN will contain.

### Decision 3: `xor` and `parallel` are grammar-level aliases

The grammar accepts `xor "Name"` and `parallel "Name"` as alternatives to `gateway "Name" { type: "xor" }`. The transformer produces the same `Gateway` AST node with the appropriate type.

**Rationale:** Grammar-level aliases keep the parser the single source of truth for syntax. No special handling needed anywhere downstream.

**Consideration:** `parallel` is also a multi-instance modifier property name. The grammar disambiguates by context — `parallel "Name"` (with a string) is a gateway declaration, `parallel: true` (with colon) is a property.

### Decision 4: Flow chains are syntactic sugar for individual edges

`"a" -> "b" -> "c"` desugars to `Flow("a", "b")` and `Flow("b", "c")`. Conditions and `otherwise` apply only to the last edge in a chain.

**Rationale:** Keeps chain semantics simple and predictable. Conditions on intermediate edges would be confusing.

### Decision 5: `[...]` parallel blocks desugar to explicit fork/join gateways

`"a" -> ["b", "c"] -> "d"` creates two Gateway nodes (fork and join) and the connecting flows. The fork gateway is added after `"a"` and the join gateway is added before `"d"`.

**Rationale:** This is pure syntactic sugar — the generated BPMN is identical to explicit gateway declarations. The parser creates the gateway nodes and flows during transformation.

## Risks / Trade-offs

- **[Grammar ambiguity]** → `parallel` as both a gateway keyword and a property name requires careful grammar design. → Lark's PEG-like parsing with priorities can disambiguate by context.
- **[Implicit element ID collisions]** → Auto-generated IDs like `<source>-gateway` could collide with user-declared elements. → Validation catches duplicate IDs; document the naming convention.
- **[Debugging implicit elements]** → Users may be confused when BPMN output contains elements they didn't declare. → CLI `info` command should show the desugared process with all implicit elements listed.
- **[Interaction between sugar forms]** → Combining implicit XOR with parallel brackets and inline ends in one flow statement increases parser complexity. → Test combinations thoroughly; limit nesting depth if needed.
