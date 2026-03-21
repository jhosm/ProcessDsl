# DSL v2 — Proposta de Design para P0 Gaps

## Contexto

A DSL atual suporta 6 tipos de elementos: `start`, `end`, `scriptCall`, `serviceTask`, `processEntity` e `xorGateway`. Este documento propõe a sintaxe para os 7 gaps P0 identificados no roadmap, com foco em legibilidade e consistência.

**Nota:** A DSL ainda não é usada em produção. Pode ser alterada sem preocupações de backwards compatibility.

### Princípios de Design

1. **Blocos `keyword "Nome" { props }`** — consistente em todos os elementos
2. **Propriedades `key: value`** — declarativas
3. **Flow section separada** — o grafo é explícito, separado dos elementos
4. **IDs auto-gerados** do nome em kebab-case (override com `id:` explícito)
5. **Defaults sensatos** — só declarar o que diverge do default

---

## 1. Gateway Genérico

**Substitui `xorGateway`** por um `gateway` genérico com `type`. Escala para inclusive (P1) sem nova keyword.

```
gateway "Decisão" {
    type: "xor"
}

gateway "Fork Paralelo" {
    type: "parallel"
}
```

Tipos suportados: `"xor"` (exclusivo), `"parallel"`, `"inclusive"` (futuro P1).

**Nota:** `xorGateway` deixa de existir. Migra-se para `gateway` com `type: "xor"`.

---

## 2. Timer Events

Três variantes: timer start, intermediate catch e boundary.

### Timer Start (processo arranca por timer)

```
start "A Cada Hora" {
    timer: cycle("R/PT1H")
}
```

### Intermediate Catch (espera no fluxo)

```
timer "Esperar 30 Minutos" {
    duration: "PT30M"
}
```

Suporta `duration` (esperar X tempo), `date` (esperar até data) e `cycle` (repetição).

### Boundary Timer (em cima de um task)

```
serviceTask "Chamar API Lenta" {
    type: "slow-api"

    onTimer "Timeout" {
        duration: "PT5M"
    }
}
```

O boundary event fica **aninhado no task a que pertence** — legível porque vês logo a associação, em vez de declarar separadamente e ligar por ID.

`interrupting` é `true` por omissão (default BPMN). Só se declara quando se quer o contrário:

```
serviceTask "Processo Longo" {
    type: "long-process"

    onTimer "Lembrete" {
        duration: "PT1M"
        interrupting: false
    }
}
```

---

## 3. Error Boundary Events

Mesmo padrão de nesting que timer boundary:

```
serviceTask "Chamar API" {
    type: "api-call"
    retries: 3

    onError "Falha API" {
        errorCode: "API_ERROR"
    }
}
```

`interrupting` é `true` por omissão. O boundary event gera um ID a partir do nome (`"falha-api"`) e é referenciável no flow section:

```
flow {
    "chamar-api" -> "proximo-passo"
    "falha-api" -> "handler-erro"
}
```

---

## 4. Subprocess (Embedded)

Contém os seus próprios elementos e flow section, recursivamente. Boundary events ficam aninhados:

```
subprocess "Processar Encomenda" {

    start "Inicio Sub" {}

    serviceTask "Validar Stock" {
        type: "check-stock"
    }

    end "Fim Sub" {}

    flow {
        "inicio-sub" -> "validar-stock"
        "validar-stock" -> "fim-sub"
    }

    onError "Erro Encomenda" {
        errorCode: "ORDER_ERROR"
    }
}
```

---

## 5. Call Activity

Invoca outro processo por ID. Suporta propagação total ou mapeamento explícito de variáveis:

```
callActivity "Validar Pagamento" {
    processId: "payment-validation"
    propagateAllVariables: true
}
```

Com mapeamento explícito:

```
callActivity "Validar Pagamento" {
    processId: "payment-validation"
    inputMappings: ["orderId" -> "orderId", "amount" -> "paymentAmount"]
    outputMappings: ["paymentResult" -> "paymentStatus"]
}
```

---

## 6. Multi-Instance

Modificador aplicável a qualquer task ou subprocess. Lê-se quase como linguagem natural:

```
serviceTask "Enviar Notificacao" {
    type: "send-notification"

    forEach: "stakeholders"
    as: "stakeholder"
    parallel: true
}
```

> "para cada stakeholder em stakeholders, em paralelo"

Em subprocess:

```
subprocess "Processar Item" {
    forEach: "lineItems"
    as: "item"
    parallel: false

    start "Inicio" {}
    serviceTask "Processar" { type: "process-item" }
    end "Fim" {}

    flow {
        "inicio" -> "processar"
        "processar" -> "fim"
    }
}
```

---

## 7. Message Events

### Message Start (processo arranca por mensagem)

```
start "Pedido Recebido" {
    message: "new-order"
}
```

### Intermediate Catch (esperar por mensagem)

```
receiveMessage "Aguardar Confirmacao" {
    message: "payment-confirmed"
    correlationKey: "orderId"
}
```

### Boundary Message (em cima de task)

```
serviceTask "Processo Longo" {
    type: "long-process"

    onMessage "Cancelamento" {
        message: "cancel-request"
        correlationKey: "orderId"
        interrupting: true
    }
}
```

---

## 8. Flow — `otherwise` em vez de `default`

Melhoria de legibilidade no flow section:

```
flow {
    "check" -> "happy-path" when "approved"
    "check" -> "retry" otherwise
}
```

`otherwise` substitui `default` — lê-se melhor e evita confusão com keyword reservada de outras linguagens.

---

## Resumo de Alterações à Gramática

| Atual | Proposto | Tipo |
|---|---|---|
| `xorGateway` | `gateway` com `type` | **Breaking change** |
| — | `timer` (intermediate catch) | Novo elemento |
| — | `start` com `timer:` / `message:` | Extensão |
| — | `onTimer` / `onError` / `onMessage` (nested) | Novo padrão |
| — | `subprocess` | Novo elemento |
| — | `callActivity` | Novo elemento |
| — | `forEach` / `as` / `parallel` (modificadores) | Novo padrão |
| — | `receiveMessage` | Novo elemento |
| `[default]` no flow | `otherwise` | **Breaking change** |

---

## Exemplo Completo 1 — Order Processing com Parallelism e Error Handling

```
process "Order Processing" {
    id: "order-processing"
    version: "2.0"

    start "Order Received" {
        message: "new-order"
    }

    processEntity "Load Order" {
        entityName: "Order"
    }

    gateway "Validate and Enrich" {
        type: "parallel"
    }

    serviceTask "Check Inventory" {
        type: "inventory-check"
        retries: 3

        onTimer "Inventory Timeout" {
            duration: "PT30S"
        }

        onError "Inventory Error" {
            errorCode: "INVENTORY_UNAVAILABLE"
        }
    }

    serviceTask "Validate Payment" {
        type: "payment-validation"
        retries: 3

        onError "Payment Failed" {
            errorCode: "PAYMENT_DECLINED"
        }
    }

    serviceTask "Enrich Customer Data" {
        type: "customer-enrichment"
    }

    gateway "Join Results" {
        type: "parallel"
    }

    gateway "Payment OK?" {
        type: "xor"
    }

    serviceTask "Fulfill Order" {
        type: "order-fulfillment"
    }

    serviceTask "Notify Customer" {
        type: "send-notification"
        headers: ["template" -> "order-confirmed"]
    }

    serviceTask "Cancel Order" {
        type: "order-cancellation"
    }

    end "Order Complete" {}
    end "Order Cancelled" {}

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

## Exemplo Completo 2 — Batch Processing com Multi-Instance e Subprocess

```
process "Invoice Batch Processing" {
    id: "invoice-batch"
    version: "1.0"

    start "Batch Triggered" {
        timer: cycle("R/P1D")
    }

    processEntity "Load Invoices" {
        entityName: "InvoiceBatch"
    }

    subprocess "Process Single Invoice" {
        forEach: "invoices"
        as: "invoice"
        parallel: true

        start "Begin Invoice" {}

        serviceTask "Validate Invoice" {
            type: "invoice-validation"

            onError "Validation Failed" {
                errorCode: "INVALID_INVOICE"
            }
        }

        serviceTask "Calculate Tax" {
            type: "tax-calculation"
        }

        callActivity "Submit to ERP" {
            processId: "erp-submission"
            inputMappings: ["invoice" -> "document", "taxAmount" -> "tax"]
            outputMappings: ["erpReference" -> "reference"]
        }

        end "Invoice Done" {}
        end "Invoice Failed" {}

        flow {
            "begin-invoice" -> "validate-invoice"
            "validate-invoice" -> "calculate-tax"
            "calculate-tax" -> "submit-to-erp"
            "submit-to-erp" -> "invoice-done"

            // error path
            "validation-failed" -> "invoice-failed"
        }
    }

    serviceTask "Generate Report" {
        type: "batch-report"
    }

    serviceTask "Send Summary Email" {
        type: "send-email"
        headers: ["template" -> "batch-summary"]
    }

    end "Batch Complete" {}

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

## Exemplo Completo 3 — Async Webhook com Message Events e Timers

```
process "Payment Reconciliation" {
    id: "payment-reconciliation"
    version: "1.0"

    start "Reconciliation Request" {}

    processEntity "Load Transaction" {
        entityName: "Transaction"
    }

    serviceTask "Initiate Bank Transfer" {
        type: "bank-transfer"
        retries: 3
        inputMappings: ["transactionId" -> "txId", "amount" -> "transferAmount"]
    }

    receiveMessage "Wait for Bank Callback" {
        message: "bank-transfer-result"
        correlationKey: "transactionId"
    }

    timer "Settlement Delay" {
        duration: "PT2H"
    }

    gateway "Transfer Result" {
        type: "xor"
    }

    serviceTask "Record Success" {
        type: "record-transaction"
        headers: ["status" -> "completed"]
    }

    serviceTask "Record Failure" {
        type: "record-transaction"
        headers: ["status" -> "failed"]
    }

    serviceTask "Notify Operations" {
        type: "send-notification"
        headers: ["channel" -> "ops-alerts"]

        onTimer "Notification Timeout" {
            duration: "PT1M"
            interrupting: false
        }
    }

    end "Reconciled" {}
    end "Failed" {}

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
