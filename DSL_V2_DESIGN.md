# DSL v2 — Design Proposal for P0 Gaps

## Context

The current DSL supports 6 element types: `start`, `end`, `scriptCall`, `serviceTask`, `processEntity`, and `xorGateway`. This document proposes syntax for the 7 P0 gaps identified in the roadmap, focusing on readability and consistency.

**Note:** The DSL is not yet in production. It can be changed without backwards compatibility concerns.

### Design Principles

1. **`keyword "Name" { props }` blocks** — consistent across all elements
2. **`key: value` properties** — declarative
3. **Separate flow section** — the graph is explicit, separated from element definitions
4. **Auto-generated IDs** from name in kebab-case (override with explicit `id:`)
5. **Sensible defaults** — only declare what differs from the default

---

## 1. Generic Gateway

**Replaces `xorGateway`** with a generic `gateway` with `type`. Scales to inclusive (P1) without a new keyword.

```
gateway "Decision" {
    type: "xor"
}

gateway "Parallel Fork" {
    type: "parallel"
}
```

Supported types: `"xor"` (exclusive), `"parallel"`, `"inclusive"` (future P1).

**Note:** `xorGateway` ceases to exist. Migrate to `gateway` with `type: "xor"`.

---

## 2. Timer Events

Three variants: timer start, intermediate catch, and boundary.

### Timer Start (process triggered by timer)

```
start "Every Hour" {
    timer: cycle("R/PT1H")
}
```

### Intermediate Catch (wait in the flow)

```
timer "Wait 30 Minutes" {
    duration: "PT30M"
}
```

Supports `duration` (wait X time), `date` (wait until date), and `cycle` (repetition).

### Duration Syntactic Sugar

ISO 8601 (`"PT30M"`) is the canonical format, but the DSL accepts readable shorthands as an alternative:

```
timer "Wait" { duration: 30m }           // equivalent to "PT30M"
timer "Long Delay" { duration: 2h30m }   // equivalent to "PT2H30M"
timer "Retry" { duration: 5s }           // equivalent to "PT5S"
timer "Wait a Day" { duration: 1d }      // equivalent to "P1D"
```

The same sugar applies to boundary events:

```
onTimer "Timeout" { duration: 30s }
onTimer "Reminder" { duration: 1h, interrupting: false }
```

And to timer starts with cycle:

```
start "Daily" { timer: cycle(1d) }       // equivalent to cycle("R/P1D")
start "Every Hour" { timer: cycle(1h) }  // equivalent to cycle("R/PT1H")
```

Raw ISO 8601 format is still supported for expressions the sugar cannot cover (e.g., `"R3/PT1H"` for repeat 3 times).

### Boundary Timer (attached to a task)

```
serviceTask "Call Slow API" {
    type: "slow-api"

    onTimer "Timeout" {
        duration: "PT5M"
    }
}
```

The boundary event is **nested inside the task it belongs to** — readable because you see the association immediately, instead of declaring separately and linking by ID.

`interrupting` is `true` by default (BPMN default). Only declare it when you want the opposite:

```
serviceTask "Long Process" {
    type: "long-process"

    onTimer "Reminder" {
        duration: "PT1M"
        interrupting: false
    }
}
```

---

## 3. Error Boundary Events

Same nesting pattern as timer boundary:

```
serviceTask "Call API" {
    type: "api-call"
    retries: 3

    onError "API Failure" {
        errorCode: "API_ERROR"
    }
}
```

`interrupting` is `true` by default. The boundary event generates an ID from the name (`"api-failure"`) and is referenceable in the flow section:

```
flow {
    "call-api" -> "next-step"
    "api-failure" -> "error-handler"
}
```

---

## 4. Subprocess (Embedded)

Contains its own elements and flow section, recursively. Boundary events are nested:

```
subprocess "Process Order" {

    start "Sub Start" {}

    serviceTask "Check Stock" {
        type: "check-stock"
    }

    end "Sub End" {}

    flow {
        "sub-start" -> "check-stock"
        "check-stock" -> "sub-end"
    }

    onError "Order Error" {
        errorCode: "ORDER_ERROR"
    }
}
```

---

## 5. Call Activity

Invokes another process by ID. Supports full propagation or explicit variable mapping:

```
callActivity "Validate Payment" {
    processId: "payment-validation"
    propagateAllVariables: true
}
```

With explicit mapping:

```
callActivity "Validate Payment" {
    processId: "payment-validation"
    inputMappings: ["orderId" -> "orderId", "amount" -> "paymentAmount"]
    outputMappings: ["paymentResult" -> "paymentStatus"]
}
```

---

## 6. Multi-Instance

Modifier applicable to any task or subprocess. Reads almost like natural language:

```
serviceTask "Send Notification" {
    type: "send-notification"

    forEach: "stakeholders"
    as: "stakeholder"
    parallel: true
}
```

> "for each stakeholder in stakeholders, in parallel"

In subprocess:

```
subprocess "Process Item" {
    forEach: "lineItems"
    as: "item"
    parallel: false

    start "Begin" {}
    serviceTask "Process" { type: "process-item" }
    end "Done" {}

    flow {
        "begin" -> "process"
        "process" -> "done"
    }
}
```

---

## 7. Message Events

### Message Start (process triggered by message)

```
start "Order Received" {
    message: "new-order"
}
```

### Intermediate Catch (wait for message)

```
receiveMessage "Wait for Confirmation" {
    message: "payment-confirmed"
    correlationKey: "orderId"
}
```

### Boundary Message (attached to task)

```
serviceTask "Long Process" {
    type: "long-process"

    onMessage "Cancellation" {
        message: "cancel-request"
        correlationKey: "orderId"
        interrupting: true
    }
}
```

---

## 8. Flow — `otherwise` instead of `default`

Readability improvement in the flow section:

```
flow {
    "check" -> "happy-path" when "approved"
    "check" -> "retry" otherwise
}
```

`otherwise` replaces `default` — reads better and avoids confusion with reserved keywords in other languages.

---

## 9. Shorthand Syntax

Many elements follow a pattern where the keyword and name are the only meaningful parts, or the body just sets a single `type`. The DSL provides shorthands for these common cases. The full `keyword "Name" { props }` form always works — shorthands are optional convenience.

### Empty Body — Drop the Braces

When an element has no properties, the `{}` can be omitted:

```
// Full form
start "Begin" {}
end "Done" {}

// Shorthand — equivalent
start "Begin"
end "Done"
```

### Gateway Type as Keyword

Since every gateway must have a type, and it's almost always the only property, the type can be used directly as the keyword:

```
// Full form
gateway "Decision" {
    type: "xor"
}

gateway "Fork" {
    type: "parallel"
}

// Shorthand — equivalent
xor "Decision"
parallel "Fork"
```

When you need extra properties (e.g., an explicit `id:`), use the block form:

```
xor "Decision" {
    id: "my-custom-id"
}
```

### Service Task with Inline Type

A service task that only defines a `type` can use a colon shorthand:

```
// Full form
serviceTask "Check Stock" {
    type: "check-stock"
}

// Shorthand — equivalent
serviceTask "Check Stock" : "check-stock"
```

When you need additional properties (retries, headers, boundary events), use the full block:

```
serviceTask "Call API" : "api-call" {
    retries: 3
    headers: ["url" -> "https://api.example.com"]
}
```

### Call Activity with Inline Process ID

Same pattern — a call activity that only sets `processId`:

```
// Full form
callActivity "Validate Payment" {
    processId: "payment-validation"
    propagateAllVariables: true
}

// Shorthand — equivalent
callActivity "Validate Payment" : "payment-validation"
```

By default, the shorthand form uses `propagateAllVariables: true`. Use the full block form when you need explicit mappings.

### Process Entity with Inline Entity Name

```
// Full form
processEntity "Load Order" {
    entityName: "Order"
}

// Shorthand — equivalent
processEntity "Load Order" : "Order"
```

### Summary

| Full Form | Shorthand | When |
|---|---|---|
| `start "X" {}` | `start "X"` | No properties |
| `end "X" {}` | `end "X"` | No properties |
| `gateway "X" { type: "xor" }` | `xor "X"` | Gateway with only a type |
| `gateway "X" { type: "parallel" }` | `parallel "X"` | Gateway with only a type |
| `serviceTask "X" { type: "t" }` | `serviceTask "X" : "t"` | Task with only a type |
| `callActivity "X" { processId: "p", propagateAllVariables: true }` | `callActivity "X" : "p"` | Propagate-all call |
| `processEntity "X" { entityName: "E" }` | `processEntity "X" : "E"` | Entity with only a name |

---

## Grammar Changes Summary

| Current | Proposed | Type |
|---|---|---|
| `xorGateway` | `gateway` with `type` | **Breaking change** |
| — | `xor` / `parallel` shorthand keywords | New sugar |
| — | `timer` (intermediate catch) | New element |
| — | `start` with `timer:` / `message:` | Extension |
| — | `onTimer` / `onError` / `onMessage` (nested) | New pattern |
| — | `subprocess` | New element |
| — | `callActivity` | New element |
| — | `forEach` / `as` / `parallel` (modifiers) | New pattern |
| — | `receiveMessage` | New element |
| `[default]` in flow | `otherwise` | **Breaking change** |
| — | Empty body without `{}` | New sugar |
| — | Inline `: "value"` for type/processId/entityName | New sugar |
| — | Duration shorthands (`30s`, `5m`, `2h`, `1d`) | New sugar |

---

## Full Example 1 — Order Processing with Parallelism and Error Handling

```
process "Order Processing" {
    id: "order-processing"
    version: "2.0"

    start "Order Received" {
        message: "new-order"
    }

    processEntity "Load Order" : "Order"

    parallel "Validate and Enrich"

    serviceTask "Check Inventory" : "inventory-check" {
        retries: 3

        onTimer "Inventory Timeout" { duration: 30s }
        onError "Inventory Error" { errorCode: "INVENTORY_UNAVAILABLE" }
    }

    serviceTask "Validate Payment" : "payment-validation" {
        retries: 3

        onError "Payment Failed" { errorCode: "PAYMENT_DECLINED" }
    }

    serviceTask "Enrich Customer Data" : "customer-enrichment"

    parallel "Join Results"

    xor "Payment OK?"

    serviceTask "Fulfill Order" : "order-fulfillment"

    serviceTask "Notify Customer" : "send-notification" {
        headers: ["template" -> "order-confirmed"]
    }

    serviceTask "Cancel Order" : "order-cancellation"

    end "Order Complete"
    end "Order Cancelled"

    flow {
        "order-received" -> "load-order"
        "load-order" -> "validate-and-enrich"

        // parallel fork
        "validate-and-enrich" -> "check-inventory"
        "validate-and-enrich" -> "validate-payment"
        "validate-and-enrich" -> "enrich-customer-data"

        // parallel join
        "check-inventory" -> "join-results"
        "validate-payment" -> "join-results"
        "enrich-customer-data" -> "join-results"

        // decision
        "join-results" -> "payment-ok?"
        "payment-ok?" -> "fulfill-order" when "paymentValid == true"
        "payment-ok?" -> "cancel-order" otherwise

        "fulfill-order" -> "notify-customer"
        "notify-customer" -> "order-complete"
        "cancel-order" -> "order-cancelled"

        // error paths
        "inventory-timeout" -> "cancel-order"
        "inventory-error" -> "cancel-order"
        "payment-failed" -> "cancel-order"
    }
}
```

---

## Full Example 2 — Batch Processing with Multi-Instance and Subprocess

```
process "Invoice Batch Processing" {
    id: "invoice-batch"
    version: "1.0"

    start "Batch Triggered" {
        timer: cycle(1d)
    }

    processEntity "Load Invoices" : "InvoiceBatch"

    subprocess "Process Single Invoice" {
        forEach: "invoices"
        as: "invoice"
        parallel: true

        start "Begin Invoice"

        serviceTask "Validate Invoice" : "invoice-validation" {
            onError "Validation Failed" { errorCode: "INVALID_INVOICE" }
        }

        serviceTask "Calculate Tax" : "tax-calculation"

        callActivity "Submit to ERP" : "erp-submission" {
            inputMappings: ["invoice" -> "document", "taxAmount" -> "tax"]
            outputMappings: ["erpReference" -> "reference"]
        }

        end "Invoice Done"
        end "Invoice Failed"

        flow {
            "begin-invoice" -> "validate-invoice"
            "validate-invoice" -> "calculate-tax"
            "calculate-tax" -> "submit-to-erp"
            "submit-to-erp" -> "invoice-done"

            // error path
            "validation-failed" -> "invoice-failed"
        }
    }

    serviceTask "Generate Report" : "batch-report"

    serviceTask "Send Summary Email" : "send-email" {
        headers: ["template" -> "batch-summary"]
    }

    end "Batch Complete"

    flow {
        "batch-triggered" -> "load-invoices"
        "load-invoices" -> "process-single-invoice"
        "process-single-invoice" -> "generate-report"
        "generate-report" -> "send-summary-email"
        "send-summary-email" -> "batch-complete"
    }
}
```

---

## Full Example 3 — Async Webhook with Message Events and Timers

```
process "Payment Reconciliation" {
    id: "payment-reconciliation"
    version: "1.0"

    start "Reconciliation Request"

    processEntity "Load Transaction" : "Transaction"

    serviceTask "Initiate Bank Transfer" : "bank-transfer" {
        retries: 3
        inputMappings: ["transactionId" -> "txId", "amount" -> "transferAmount"]
    }

    receiveMessage "Wait for Bank Callback" {
        message: "bank-transfer-result"
        correlationKey: "transactionId"
    }

    timer "Settlement Delay" { duration: 2h }

    xor "Transfer Result"

    serviceTask "Record Success" : "record-transaction" {
        headers: ["status" -> "completed"]
    }

    serviceTask "Record Failure" : "record-transaction" {
        headers: ["status" -> "failed"]
    }

    serviceTask "Notify Operations" : "send-notification" {
        headers: ["channel" -> "ops-alerts"]

        onTimer "Notification Timeout" {
            duration: 1m
            interrupting: false
        }
    }

    end "Reconciled"
    end "Failed"

    flow {
        "reconciliation-request" -> "load-transaction"
        "load-transaction" -> "initiate-bank-transfer"
        "initiate-bank-transfer" -> "wait-for-bank-callback"
        "wait-for-bank-callback" -> "settlement-delay"
        "settlement-delay" -> "transfer-result"

        "transfer-result" -> "record-success" when "transferStatus == 'completed'"
        "transfer-result" -> "record-failure" otherwise

        "record-success" -> "reconciled"
        "record-failure" -> "notify-operations"
        "notify-operations" -> "failed"
    }
}
```
