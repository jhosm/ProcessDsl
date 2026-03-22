## Context

The DSL currently has no event types beyond basic start and end. BPMN supports rich event semantics — timer events (start, intermediate catch, boundary) and error boundary events are the most commonly used in production workflows. The DSL V2 design proposes a nesting pattern where boundary events are declared inside the task they attach to, making the parent-child relationship visually clear without separate ID-based linking.

## Goals / Non-Goals

**Goals:**
- Support timer intermediate catch events (`timer "Name" { duration: ... }`)
- Support timer start events (`start "Name" { timer: cycle(...) }`)
- Support duration syntactic sugar (`30s`, `5m`, `2h`, `1d`) alongside ISO 8601
- Support boundary timer events (`onTimer`) nested in tasks
- Support boundary error events (`onError`) nested in tasks
- Both boundary types generate proper BPMN `boundaryEvent` elements with `attachedToRef`
- Boundary events are referenceable by their kebab-case ID in flow sections

**Non-Goals:**
- Message boundary events — covered by the message-events change
- Signal events — not in current roadmap
- Compensation boundary events — not in current roadmap
- Escalation events — not in current roadmap

## Decisions

### Decision 1: Boundary events nested inside parent elements

Boundary events are declared inside the task block they attach to, rather than as top-level elements with an `attachedTo` property.

**Rationale:** Nesting makes the relationship obvious at a glance. It also prevents orphaned boundary events (a boundary event without a valid parent). The parser can enforce the parent-child constraint structurally.

**Alternative considered:** Top-level boundary events with `attachedTo: "task-id"`. Rejected because it separates related declarations and requires cross-referencing by ID.

### Decision 2: Duration sugar is parser-level desugaring

Duration shorthands like `30s`, `2h30m` are parsed as tokens and converted to ISO 8601 strings in the parser/transformer phase. The AST and generator only see ISO 8601 strings.

**Rationale:** Keeps the AST and BPMN generator simple — they don't need to know about sugar. All duration logic is concentrated in one place (the parser).

**Supported patterns:** `Ns` (seconds), `Nm` (minutes), `Nh` (hours), `Nd` (days), and combinations like `2h30m`. Mapped to `PTnHnMnS` or `PnD`.

### Decision 3: Boundary events stored as a list on the parent AST node

`ServiceTask` (and later `Subprocess`) AST nodes get an optional `boundary_events` list field. Each boundary event is a dataclass (`BoundaryTimerEvent`, `BoundaryErrorEvent`) with its own name, ID, and properties.

**Rationale:** Keeps the tree structure natural — boundary events belong to their parent. The BPMN generator can iterate a task's boundary events when generating that task.

### Decision 4: `interrupting` defaults to `true` per BPMN spec

Boundary events default to `interrupting: true`, matching the BPMN 2.0 standard. Users only need to declare `interrupting: false` for non-interrupting events. Maps to `cancelActivity` attribute in BPMN XML.

## Risks / Trade-offs

- **[Layout complexity]** → Boundary events must be positioned on the border of their parent task, which adds complexity to the layout engine. → Start with a fixed offset (e.g., bottom-center of task) and refine later.
- **[Duration sugar ambiguity]** → `1d` could mean 24 hours (PT24H) or 1 calendar day (P1D). → Use `P1D` for days per ISO 8601 convention, matching BPMN semantics.
- **[Nested grammar complexity]** → Nesting boundary events inside tasks increases grammar depth. → Lark handles recursive grammars well; keep boundary event rules as optional children of task rules.
