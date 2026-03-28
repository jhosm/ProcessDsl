# Roadmap: DSL vs BPMN Gap Analysis

## Contexto

O ProcessDsl suporta atualmente 6 tipos de elementos BPMN: StartEvent (plain), EndEvent (plain), ScriptTask, ServiceTask, ExclusiveGateway e SequenceFlow, mais o macro ProcessEntity. Esta análise identifica os gaps face à spec BPMN 2.0.

**Scope atual:** processos totalmente automatizados (sem intervenção humana).

**Nota sobre priorização:** A ordenação é baseada em conhecimento geral sobre adoção de BPMN, não em dados quantitativos (surveys, análise de repositórios, etc.). Deve ser tratada como estimativa informada, não como facto.

**Princípio ProcessEntity:** O processEntity representa o workload do processo. Mantém-se a restrição de exatamente um por processo.

## Estado Atual da DSL

| Elemento DSL | Elemento BPMN | Extensões Zeebe |
|---|---|---|
| `start` | `<startEvent>` | — |
| `end` | `<endEvent>` | — |
| `scriptCall` | `<scriptTask>` | `<zeebe:script>`, `<zeebe:ioMapping>` |
| `serviceTask` | `<serviceTask>` | `<zeebe:taskDefinition>`, `<zeebe:taskHeaders>`, `<zeebe:ioMapping>` |
| `gateway { type: xor }` | `<exclusiveGateway>` | — |
| `gateway { type: parallel }` | `<parallelGateway>` | — |
| `processEntity` | `<serviceTask>` + gateway + error end (auto) | Vários |
| flow | `<sequenceFlow>` | `<conditionExpression>` |

**Restrições atuais:** 1 processo por ficheiro, 1 processEntity obrigatório (primeiro task após start), sem execução paralela, sem eventos intermédios, sem boundary events, sem subprocessos.

---

## P0 — Crítico (processos automatizados)

### 1. Parallel Gateway
- **BPMN:** `<bpmn:parallelGateway>`
- **Porquê:** Concorrência é essencial em pipelines automatizados — chamar múltiplas APIs em paralelo, fazer fork/join de processamento.
- **Habilita:** Execução concorrente, fork/join patterns.

### 2. Timer Events
- **BPMN:** `<bpmn:intermediateCatchEvent>` + `timerEventDefinition`, `<bpmn:boundaryEvent>` + `timerEventDefinition`, `<bpmn:startEvent>` + `timerEventDefinition`
- **Porquê:** Timeouts em service calls, retry delays, arranques agendados — ubíquos em automação. Sem humano para intervir, timeouts são críticos.
- **Habilita:** Timeouts, arranques agendados, retry delays, processos periódicos.

### 3. Error Boundary Events
- **BPMN:** `<bpmn:boundaryEvent>` + `errorEventDefinition`
- **Porquê:** Error handling em service tasks é crítico em processos sem intervenção humana. Atualmente só o ProcessEntity tem error handling auto-gerado.
- **Habilita:** Error handling em qualquer task, fallback logic, recovery paths.

### 4. Subprocess (Embedded)
- **BPMN:** `<bpmn:subProcess>`
- **Porquê:** Scope para error handling e organização de processos complexos. Pré-requisito para error boundary events terem todo o seu valor.
- **Habilita:** Decomposição hierárquica, scope de error handling, agrupamento lógico.

### 5. Call Activity
- **BPMN:** `<bpmn:callActivity>`
- **Porquê:** Composição de processos automatizados reutilizáveis. Core pattern quando há mais que meia dúzia de processos.
- **Habilita:** Reutilização, design modular, subfluxos partilhados.

### 6. Multi-Instance
- **BPMN:** `<bpmn:multiInstanceLoopCharacteristics>` em tasks/subprocessos
- **Porquê:** Iterar sobre coleções é muito comum em automação — processar N items, chamar N serviços, validar N documentos.
- **Habilita:** For-each patterns, processamento batch, paralelismo dinâmico.

### 7. Message Events
- **BPMN:** Vários eventos com `messageEventDefinition`
- **Porquê:** Event-driven: esperar por callback de API, webhook, comunicação inter-processo. Fundamental em arquiteturas de microserviços.
- **Habilita:** Arranques event-driven, espera por callbacks, comunicação inter-processo.

---

## P1 — Alto (processos não-triviais)

### 8. Inclusive Gateway (OR)
- **BPMN:** `<bpmn:inclusiveGateway>`
- Permite que uma ou mais branches sejam tomadas. Menos usado que XOR mas frequente em cenários com condições sobrepostas.

### 9. Send/Receive Task
- **BPMN:** `<bpmn:sendTask>`, `<bpmn:receiveTask>`
- Abordagem mais limpa para interações baseadas em mensagens. Receive tasks importantes para padrões request-response assíncronos.

### 10. Business Rule Task (DMN)
- **BPMN:** `<bpmn:businessRuleTask>`
- Invoca decision tables DMN, capacidade core do Camunda.

### 11. Terminate End Event
- **BPMN:** `<bpmn:endEvent>` + `terminateEventDefinition`
- Termina imediatamente todos os caminhos ativos. Necessário com parallel gateways.

### 12. Error Throw End Event (definido pelo user)
- **BPMN:** `<bpmn:endEvent>` + `errorEventDefinition`
- Atualmente só auto-gerado pelo ProcessEntity. Necessário para lançar errors dentro de subprocessos.

---

## P2 — Médio (padrões específicos)

### 13. Event Subprocess
- **BPMN:** `<bpmn:subProcess triggeredByEvent="true">`
- Handlers de cross-cutting concerns (cancelamento global, error handling a nível de processo).

### 14. Non-Interrupting Boundary Events
- **BPMN:** `<bpmn:boundaryEvent cancelActivity="false">`
- Side flows sem cancelar a atividade principal.

### 15. Signal Events
- **BPMN:** Eventos com `signalEventDefinition`
- Comunicação broadcast. Suporte limitado no Camunda 8.

### 16. Intermediate Throw Events
- **BPMN:** `<bpmn:intermediateThrowEvent>` com message/signal
- Enviar mensagem ou broadcast a meio do fluxo.

### 17. Data Objects
- **BPMN:** `<bpmn:dataObjectReference>`, `<bpmn:dataStoreReference>`
- Documentação visual do fluxo de dados. Sem efeito na execução.

---

## P3 — Baixo (especializado ou raramente usado)

### 18. Event-Based Gateway
- Race condition patterns. Maioria dos cenários modelável com timer boundary events.

### 19. Compensation Events
- Saga pattern rollbacks. Raramente usado. Suporte limitado no Camunda 8.

### 20. Link Events
- Conveniência de diagrama (goto visual). Sem semântica runtime.

### 21. Escalation Events
- Propagação de issues não-críticos por hierarquia de subprocessos.

### 22. Text Annotation
- Documentação visual nos diagramas. Sem semântica de execução.

---

## Fora de scope (não suportado no Camunda 8)

- Complex Gateway
- Conditional Events
- Transaction Subprocess
- Ad-Hoc Subprocess

---

## Futuro (quando houver intervenção humana)

### User Task
- **BPMN:** `<bpmn:userTask>` com `<zeebe:assignmentDefinition>`, `<zeebe:formDefinition>`
- Workflows human-in-the-loop, aprovações, task assignment, formulários.

### Pools e Lanes
- **BPMN:** `<bpmn:collaboration>`, `<bpmn:participant>`, `<bpmn:laneSet>`
- Visualização de responsabilidades organizacionais.

---

## Resumo

| Prioridade | # Gaps | Elementos |
|---|---|---|
| **P0** | 7 | Parallel Gateway, Timer Events, Error Boundary, Subprocess, Call Activity, Multi-Instance, Message Events |
| **P1** | 5 | Inclusive Gateway, Send/Receive, Business Rule Task, Terminate End, Error Throw End |
| **P2** | 5 | Event Subprocess, Non-Interrupting Boundary, Signal Events, Intermediate Throw, Data Objects |
| **P3** | 5 | Event-Based Gateway, Compensation, Link Events, Escalation, Text Annotation |
| **Futuro** | 2 | User Task, Pools/Lanes |
| **Fora de scope** | 4 | Complex Gateway, Conditional Events, Transaction Subprocess, Ad-Hoc Subprocess |

## Ficheiros Críticos a Modificar

- `src/bpm_dsl/grammar.lark` — Estender gramática com novos tipos de elementos
- `src/bpm_dsl/ast_nodes.py` — Novos dataclasses AST para cada tipo
- `src/bpm_dsl/parser.py` — Transformer rules para novos elementos
- `src/bpm_dsl/bpmn_generator.py` — Geração BPMN para novos elementos + extensões Zeebe
- `src/bpm_dsl/validator.py` — Adicionar novas regras de validação
- `src/bpm_dsl/layout_engine.py` — Layouts para novos shapes
