## Context

Message events are fundamental to event-driven BPM. Zeebe implements message correlation — matching incoming messages to waiting process instances using correlation keys. The DSL needs to express message names and correlation keys while generating the correct Zeebe extensions for message subscriptions.

## Goals / Non-Goals

**Goals:**
- Support message start events (`start "Name" { message: "msg-name" }`)
- Support receive message intermediate catch events (`receiveMessage "Name" { message: "...", correlationKey: "..." }`)
- Support boundary message events (`onMessage "Name" { message: "...", correlationKey: "...", interrupting: ... }`)
- Generate Zeebe-compatible message subscriptions with correlation keys
- Generate `bpmn:message` definitions at the process/definitions level

**Non-Goals:**
- Message throw events (send) — Zeebe uses job workers or publish-message API instead
- Message correlation with multiple keys — Zeebe supports single correlation key
- Message TTL (time-to-live) configuration — use Zeebe defaults

## Decisions

### Decision 1: `receiveMessage` as a distinct keyword (not `message`)

Use `receiveMessage` instead of `message` for intermediate catch events to avoid ambiguity with the `message:` property on start events and boundary events.

**Rationale:** `message` is overloaded — it's both a property name and could be an element type. `receiveMessage` is unambiguous and reads well: "receive message 'Wait for Confirmation'".

**Alternative considered:** `messageCatch "Name"` — more technical but less readable.

### Decision 2: Correlation key is a FEEL expression string

The `correlationKey` property takes a string that becomes a FEEL expression in the Zeebe subscription. The generator auto-prefixes with `=` if not already present, consistent with how script expressions work.

**Rationale:** Consistent with existing FEEL expression handling in the DSL. The correlation key is typically a process variable reference (e.g., `"orderId"`).

### Decision 3: Message definitions generated at process level

Each unique message name used in the process generates a `bpmn:message` element in the BPMN `definitions` section. Elements reference these via `messageRef`. This follows the BPMN standard where messages are defined globally.

**Rationale:** Required by the BPMN spec and Zeebe runtime. Duplicate message names across elements share a single definition.

## Risks / Trade-offs

- **[Correlation key required for non-start events]** → Zeebe requires correlation keys on intermediate and boundary message events but not on start events. → Validation enforces this rule.
- **[Message name uniqueness]** → Multiple elements can reference the same message name (e.g., same message on start and boundary). → The generator deduplicates message definitions.
- **[No send/throw support]** → The DSL only models receive-side message events. Sending messages is done via Zeebe job workers or the publish-message API. → Document this explicitly; it's consistent with Zeebe's architecture.
