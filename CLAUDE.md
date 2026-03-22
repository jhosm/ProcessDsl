# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Project Overview

**ProcessDsl** is a multi-language Business Process Management (BPM) platform that lets developers define workflows in a text-based DSL (`.bpm` files) paired with OpenAPI specs (`.yaml`), then automatically generates:

- **BPMN XML** deployable to Camunda Zeebe
- **C# microservices** from OpenAPI specifications
- **TypeScript job workers** for entity validation
- **Automatic diagram layouts** with professional positioning

### Architecture

```
.bpm file + .yaml spec
        │
        ▼
  Lark Parser (Python)
        │
        ▼
    AST Nodes
        │
    ┌───┴───┐
    ▼       ▼
Validator  BPMN Generator → Layout Engine → .bpmn XML
                                              │
                                              ▼
                                        Camunda Zeebe
                                              │
                              ┌───────────────┼──────────────┐
                              ▼               ▼              ▼
                     C# Orchestration   TypeScript       Generated
                       Library          Job Workers     Microservices
```

## Repository Structure

```
ProcessDsl/
├── src/
│   ├── bpm_dsl/                      # Core Python DSL engine
│   │   ├── grammar.lark              #   EBNF grammar definition
│   │   ├── parser.py                 #   Lark parser + AST transformer
│   │   ├── ast_nodes.py              #   Dataclass AST node definitions
│   │   ├── bpmn_generator.py         #   BPMN XML generation (Zeebe namespaces)
│   │   ├── layout_engine.py          #   Graph-based automatic layout
│   │   ├── validator.py              #   Multi-level process validation
│   │   └── cli.py                    #   Click CLI (convert, validate, info)
│   │
│   ├── ProcessDsl.Orchestration/     # C# NuGet library (v1.1.0, .NET 8.0)
│   │   ├── CamundaClient.cs          #   Zeebe gRPC client wrapper
│   │   ├── ProcessOrchestrator.cs    #   High-level orchestration service
│   │   ├── ICamundaClient.cs         #   Client interface
│   │   ├── IProcessOrchestrator.cs   #   Orchestrator interface
│   │   ├── ServiceCollectionExtensions.cs  # DI registration
│   │   └── Models/                   #   Configuration, request, response types
│   │
│   ├── ProcessDsl.EntityValidation/  # C# Zeebe job worker (entity validation)
│   │   ├── EntitySchemaValidator.cs  #   NJsonSchema-based entity validation
│   │   ├── ProcessEntityValidatorWorker.cs  # Zeebe worker hosted service
│   │   └── Models/                   #   Configuration, validation result types
│   │
│   └── microservices/                # Auto-generated C# APIs (gitignored)
│
├── tests/
│   ├── test_parser.py                # Python parser tests
│   ├── test_bpmn_generator.py        # BPMN generation tests
│   └── ProcessDsl.Orchestration.Tests/  # C# xUnit tests (27 tests)
│
├── examples/                         # Sample .bpm processes and .yaml specs
│   └── demos/                        # Python demo scripts
│       ├── demo.py
│       ├── demo_advanced_layout.py
│       ├── demo_default_flows.py
│       └── demo_service_task.py
│
├── templates/                        # OpenAPI Generator custom templates
│   ├── aspnetcore-default/
│   └── aspnetcore-processdsl/
│
├── scripts/                          # Deployment and generation scripts
│   ├── generate_microservice.sh
│   ├── deploy_to_camunda.sh
│   ├── test_microservice.sh
│   └── extract_process_metadata.py
│
└── docs/
    ├── DSL_GRAMMAR.md                # Grammar specification
    ├── DSL_V2_DESIGN.md              # DSL v2 design proposal
    ├── LAYOUT_ALGORITHM.md           # Layout engine details
    ├── PROCESS_ENTITY_VALIDATION.md  # Validation pattern
    ├── OPENAPI_VALIDATION.md         # OpenAPI pairing rules
    ├── MICROSERVICES_WORKFLOW.md      # Microservice generation
    ├── END_TO_END_TESTING.md         # E2E testing guide
    ├── QUICKSTART.md                 # Quick start guide
    └── roadmap.md                    # Project roadmap
```

## Languages & Frameworks

| Component | Language | Key Dependencies |
|-----------|----------|-----------------|
| DSL Engine | Python 3.8+ | lark 1.1.7, lxml 4.9.3, PyYAML 6.0.1, click 8.1.7 |
| Orchestration Library | C# / .NET 8.0 | zb-client 2.9.0, Newtonsoft.Json 13.0.3, Microsoft.Extensions.* |
| Job Workers | TypeScript 5.0 | zeebe-node 8.3.0, ajv 8.12.0, js-yaml 4.1.0 |

## Build & Test Commands

### Python (DSL Engine)

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .                        # Dev mode install

# Run tests
python -m pytest tests/ -v
python -m pytest tests/ --cov=src/bpm_dsl --cov-report=html

# Linting & formatting
black src/ tests/
flake8 src/ tests/
mypy src/

# CLI usage
python -m bpm_dsl.cli convert examples/process_entity_demo.bpm --output result.bpmn
python -m bpm_dsl.cli validate examples/process_entity_demo.bpm
python -m bpm_dsl.cli info examples/process_entity_demo.bpm
```

### C# (Orchestration)

```bash
# Build
dotnet build src/ProcessDsl.Orchestration/

# Test (27 unit tests)
dotnet test tests/ProcessDsl.Orchestration.Tests/
dotnet test tests/ProcessDsl.Orchestration.Tests/ /p:CollectCoverage=true
```

### Entity Validation Worker (C#)

```bash
cd src/ProcessDsl.EntityValidation
dotnet run                    # Run locally
dotnet publish -c Release     # Build for deployment
```

### Microservice Generation

```bash
# Generate a C# microservice from OpenAPI spec
./scripts/generate_microservice.sh examples/process_entity_demo.yaml ProcessEntityDemo
```

## DSL Syntax Quick Reference

```
process "My Process" {
    id: "my-process"
    version: "1.0"

    start "Begin" {}

    processEntity "Load Data" {         # Auto-generates validation flow
        entityName: "Customer"
    }

    scriptCall "Calculate" {
        script: "result = compute(input)"
        inputVars: ["input"]
        outputVars: ["result"]
    }

    serviceTask "Call API" {
        taskType: "api-call"
        retries: 3
        headers: { "url": "https://api.example.com" }
    }

    xorGateway "Check Result" {}

    end "Done" {}

    flow {
        "begin" -> "load-data"
        "load-data" -> "calculate"
        "calculate" -> "call-api"
        "call-api" -> "check-result"
        "check-result" -> "done" when "result > 0"
        "check-result" -> "begin" default
    }
}
```

Key rules:
- Every `.bpm` file must have a matching `.yaml` (OpenAPI) file with the same basename
- Element IDs are auto-generated from names in kebab-case
- `processEntity` elements automatically generate validation service tasks and error-handling XOR gateways in BPMN output

## Key Design Patterns

- **Pipeline**: DSL text → Lark parse → AST transform → validate → generate BPMN → layout
- **Visitor/Transformer**: Lark transformer walks parse tree into AST dataclasses
- **Builder**: BPMNGenerator constructs XML element by element
- **DI**: C# orchestration uses Microsoft.Extensions.DependencyInjection
- **Job Worker**: TypeScript workers subscribe to Zeebe task types

## Conventions

- **Python**: formatted with `black`, linted with `flake8`, type-checked with `mypy`
- **C#**: nullable enabled, implicit usings, .NET 8.0
- **IDs**: kebab-case auto-generated from display names (e.g., "Load Customer" → `load-customer`)
- **Tests**: pytest for Python, xUnit for C#
- **Commit messages**: prefixed with `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Version-controlled: Built on Dolt with cell-level merge
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
