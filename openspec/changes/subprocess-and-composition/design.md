## Context

The DSL currently supports only flat processes with a single level of elements. BPMN supports hierarchical composition through embedded subprocesses, inter-process invocation via call activities, and multi-instance execution for collection-based iteration. The DSL V2 design proposes all three as part of the composition feature set.

## Goals / Non-Goals

**Goals:**
- Support `subprocess` with nested elements, internal flow, and boundary events
- Support `callActivity` with process ID reference, `propagateAllVariables`, and explicit input/output mappings
- Support `forEach` / `as` / `parallel` modifiers on `serviceTask` and `subprocess` for multi-instance
- Generate correct BPMN XML for all three constructs with Zeebe extensions
- Validate subprocess internal structure recursively

**Non-Goals:**
- Event subprocesses — not in current roadmap
- Transaction subprocesses — not in current roadmap
- Ad-hoc subprocesses — not in BPMN standard for Zeebe
- Multi-instance on `scriptCall` — can be added later if needed

## Decisions

### Decision 1: Subprocess is a recursive process container

A `subprocess` contains its own `start`, `end`, tasks, and `flow {}` block — the same structure as a top-level process. The grammar rule is recursive, allowing nested subprocesses (though this is rare in practice).

**Rationale:** Reusing the same element/flow structure at both levels keeps the grammar and parser DRY. The BPMN spec treats subprocesses as mini-processes.

**Alternative considered:** A flattened "group" syntax that doesn't have its own flow section. Rejected because it would diverge from BPMN semantics and lose the ability to model internal error handling.

### Decision 2: Call activity uses Zeebe `calledElement` extension

The `callActivity` generates a `bpmn:callActivity` with `zeebe:calledElement` specifying the process ID and propagation flag. This matches Zeebe's required format (not vanilla BPMN's `calledElement` attribute).

**Rationale:** The platform targets Camunda Zeebe exclusively. Using `zeebe:calledElement` ensures deployment compatibility.

### Decision 3: Multi-instance is a modifier, not a separate element type

The `forEach`, `as`, and `parallel` properties are added as optional modifiers on `serviceTask` and `subprocess` elements rather than creating a separate `multiInstance` wrapper element.

**Rationale:** Reads naturally — "serviceTask with forEach" is intuitive. It matches how BPMN represents multi-instance (as `loopCharacteristics` on the activity element, not as a separate element).

### Decision 4: `propagateAllVariables: true` is the default for call activities

When no explicit input/output mappings are provided, call activities default to propagating all variables. This matches the most common use case and aligns with the shorthand syntax design.

**Rationale:** Most call activities pass all variables. Requiring explicit opt-in adds boilerplate for the common case.

## Risks / Trade-offs

- **[Recursive grammar complexity]** → Subprocess grammar is recursive (subprocess can contain subprocess). → Lark handles this natively; limit nesting depth in validation if needed.
- **[Layout for subprocesses]** → Subprocess requires a container box with internal element layout, significantly increasing layout engine complexity. → Phase 1: fixed-size subprocess box; Phase 2: auto-sizing based on content.
- **[Multi-instance output collection]** → Zeebe requires output element/collection variables for multi-instance results. → Default `outputElement` to the `as` variable name and `outputCollection` to `<forEach>Results` unless explicitly overridden.
