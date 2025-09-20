# BPM DSL - Text-based Business Process Modeling

A domain-specific language (DSL) for defining business processes that generates BPMN files compatible with Camunda's Zeebe engine.

## Features

- **Simple Text-based Syntax**: Write business processes in a clean, readable format
- **Limited Primitive Set**: Focus on essential BPM elements (start, end, xor gateway, scriptCall)
- **Zeebe Compatible**: Generates BPMN XML that works with Camunda's Zeebe workflow engine
- **Type Safety**: Built-in validation for process definitions

## Supported Primitives

- **Start Event**: Process entry points
- **End Event**: Process termination points  
- **Script Call**: Execute JavaScript expressions with variable I/O
- **XOR Gateway**: Exclusive decision points with conditions

## Quick Start

### 1. Define a Process

Create a `.bpm` file with your process definition:

```bpm
process "My Process" {
    id: "my-process"
    version: "1.0"
    
    start "Begin" {
        id: "start-1"
    }
    
    scriptCall "Do Work" {
        id: "task-1"
        script: "processData(input)"
        inputVars: ["input"]
        outputVars: ["result"]
    }
    
    end "Complete" {
        id: "end-1"
    }
    
    flow {
        "start-1" -> "task-1"
        "task-1" -> "end-1"
    }
}
```

### 2. Generate BPMN

```bash
python -m bpm_dsl.cli convert my_process.bpm --output my_process.bpmn
```

### 3. Deploy to Zeebe

The generated BPMN file can be deployed directly to Camunda's Zeebe engine.

## Project Structure

```
bpm_dsl/
├── src/bmp_dsl/
│   ├── __init__.py
│   ├── parser.py          # DSL parser
│   ├── ast_nodes.py       # AST node definitions
│   ├── bpmn_generator.py  # BPMN XML generator
│   ├── validator.py       # Process validation
│   └── cli.py            # Command-line interface
├── tests/
├── examples/
├── DSL_GRAMMAR.md        # Formal grammar specification
└── README.md
```

## Grammar

See [DSL_GRAMMAR.md](DSL_GRAMMAR.md) for the complete grammar specification.

## Examples

Check the `examples/` directory for sample process definitions demonstrating various patterns.

## Development

### Prerequisites

- Python 3.8+
- Required packages: `lark-parser`, `lxml`

### Installation

```bash
pip install -r requirements.txt
```

### Running Tests

```bash
python -m pytest tests/
```

## License

MIT License
