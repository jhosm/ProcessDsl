# BPM DSL - Text-based Business Process Modeling

A powerful domain-specific language (DSL) for defining business processes that generates professional BPMN files compatible with Camunda's Zeebe engine.

## Features

- **🎯 Simple Text-based Syntax**: Write business processes in a clean, readable format
- **🔧 Essential BPM Primitives**: Focus on core elements (start, end, xor gateway, scriptCall)
- **⚡ Full Zeebe Compatibility**: Generates BPMN XML with proper FEEL expressions and Zeebe extensions
- **🎨 Professional Layout Engine**: Automatic diagram positioning with intelligent gateway handling
- **✅ Comprehensive Validation**: Built-in process validation with detailed error reporting
- **💻 CLI Interface**: Complete command-line tools for conversion, validation, and analysis
- **🔄 Variable Mapping**: Advanced input/output mappings with custom result variables

## Supported Primitives

- **Start Event**: Process entry points with configurable properties
- **End Event**: Process termination points with multiple outcomes
- **Script Call**: Execute JavaScript/FEEL expressions with advanced variable I/O mapping
- **Service Task**: External job workers with headers and retries
- **Process Entity**: Entity validation with OpenAPI schemas
- **XOR Gateway**: Exclusive decision points with conditional routing

## Important Requirements

**⚠️ OpenAPI Specification Required**: Every `.bpm` file **must** have a corresponding OpenAPI specification file (`.yaml` or `.yml`) with the same base name in the same directory. This ensures API-first design and enables entity validation.

See **[OPENAPI_VALIDATION.md](OPENAPI_VALIDATION.md)** for detailed requirements and examples.

## Quick Start

### 1. Define a Process

Create a `.bpm` file with your process definition:

```bpm
process "Order Processing" {
    id: "order-process"
    version: "1.0"
    
    start "Order Received" {
        id: "start-order"
    }
    
    scriptCall "Validate Order" {
        id: "validate-order"
        script: "validateOrderData(order)"
        inputMappings: [
            {source: "order" target: "order"}
        ]
        outputMappings: [
            {source: "isValid" target: "isValid"},
            {source: "validationErrors" target: "validationErrors"}
        ]
        resultVariable: "validationResult"
    }
    
    xorGateway "Order Valid?" {
        id: "order-valid-gateway"
    }
    
    scriptCall "Process Order" {
        id: "process-order"
        script: "processValidOrder(order)"
        inputMappings: [
            {source: "order" target: "order"}
        ]
        outputMappings: [
            {source: "processedOrder" target: "processedOrder"}
        ]
    }
    
    end "Order Processed" {
        id: "end-processed"
    }
    
    end "Order Rejected" {
        id: "end-rejected"
    }
    
    flow {
        "start-order" -> "validate-order"
        "validate-order" -> "order-valid-gateway"
        "order-valid-gateway" -> "process-order" [condition: "isValid == true"]
        "order-valid-gateway" -> "end-rejected" [condition: "isValid == false"]
        "process-order" -> "end-processed"
    }
}
```

### 2. Generate BPMN

```bash
# Convert DSL to BPMN
python -m bpm_dsl.cli convert order_process.bpm

# Convert with custom output
python -m bpm_dsl.cli convert order_process.bpm --output custom_name.bpmn

# Validate without generating
python -m bpm_dsl.cli validate order_process.bpm

# Show process information
python -m bpm_dsl.cli info order_process.bpm
```

### 3. Deploy to Zeebe

The generated BPMN files include proper Zeebe extensions and FEEL expressions, making them ready for direct deployment to Camunda's Zeebe engine.

## Advanced Features

### Professional Layout Engine

The BPM DSL includes a sophisticated layout algorithm that automatically positions BPMN elements for optimal readability:

- **Intelligent Positioning**: Hierarchical element placement with proper spacing
- **Gateway Branch Handling**: Automatic vertical spacing for decision branches
- **Edge Routing**: Orthogonal routing with waypoint optimization
- **Customizable Configuration**: Adjustable spacing, dimensions, and layout parameters

```python
from src.bpm_dsl.layout_engine import LayoutConfig

# Custom layout configuration
config = LayoutConfig()
config.SPACING['horizontal'] = 200
config.SPACING['vertical'] = 120

generator = BPMNGenerator(layout_config=config)
```

### Variable Mapping System

Advanced variable handling with full Zeebe compatibility:

```bmp
scriptCall "Process Data" {
    id: "process-task"
    script: "result = processUserData(userData)"
    inputMappings: [
        {source: "userData" target: "localUserData"}
    ]
    outputMappings: [
        {source: "processedData" target: "processedData"},
        {source: "status" target: "taskStatus"}
    ]
    resultVariable: "customResult"  // Optional, defaults to "result"
}
```

### CLI Interface

Complete command-line interface with multiple commands:

```bash
# Convert DSL to BPMN with validation
python -m bpm_dsl.cli convert process.bpm --output result.bpmn

# Validate process without generating BPMN
python -m bpm_dsl.cli validate process.bpm

# Show detailed process information
python -m bpm_dsl.cli info process.bpm

# Get help
python -m bpm_dsl.cli --help
```

## Project Structure

```
bpm_dsl/
├── src/bpm_dsl/
│   ├── __init__.py
│   ├── parser.py          # Lark-based DSL parser
│   ├── ast_nodes.py       # AST node definitions
│   ├── bpmn_generator.py  # BPMN XML generator with layout
│   ├── layout_engine.py   # Professional layout algorithm
│   ├── validator.py       # Process validation engine
│   ├── cli.py            # Command-line interface
│   └── grammar.lark      # EBNF grammar specification
├── tests/                 # Comprehensive test suite
├── examples/             # Sample process definitions
├── demo.py              # Feature demonstration script
├── demo_advanced_layout.py  # Layout algorithm demos
├── DSL_GRAMMAR.md       # Formal grammar documentation
├── LAYOUT_ALGORITHM.md  # Layout engine documentation
└── README.md
```

## Grammar & Documentation

- **[DSL_GRAMMAR.md](DSL_GRAMMAR.md)**: Complete EBNF grammar specification
- **[LAYOUT_ALGORITHM.md](LAYOUT_ALGORITHM.md)**: Detailed layout engine documentation
- **[OPENAPI_VALIDATION.md](OPENAPI_VALIDATION.md)**: OpenAPI file requirements and validation
- **[QUICKSTART.md](QUICKSTART.md)**: Quick start guide with examples

## Examples

The `examples/` directory contains sample processes demonstrating various patterns:

- **simple_approval.bpm**: Basic approval workflow with gateways
- **order_processing**: Complex order processing with multiple decision points
- **document_review**: Multi-stage review process with parallel branches

Run the demonstration scripts to see all features in action:

```bash
# Basic feature demonstration
python demo.py

# Advanced layout algorithm demonstration  
python demo_advanced_layout.py
```

## Development

### Prerequisites

- Python 3.8+
- Dependencies: `lark-parser`, `lxml`, `click`

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage
python -m pytest tests/ --cov=src/bpm_dsl --cov-report=html
```

### Project Status

✅ **Complete Features:**
- Text-based DSL with comprehensive parser
- BPMN XML generation with Zeebe compatibility
- Professional layout engine with gateway handling
- Process validation with detailed error reporting
- CLI interface with convert/validate/info commands
- Comprehensive test suite (100% passing)
- Variable mapping with FEEL expressions
- Custom result variable support

🚀 **Ready for Production:**
- Deploy generated BPMN files directly to Camunda Zeebe
- Use in CI/CD pipelines for process automation
- Integrate with existing business process workflows

## License

MIT License
