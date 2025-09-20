# BPM DSL Quick Start Guide

## Installation

1. **Install dependencies:**
   ```bash
   pip install lark-parser lxml click
   ```

2. **Clone/download the project:**
   ```bash
   # The project is ready to use from this directory
   cd windsurf-project
   ```

## Basic Usage

### 1. Create a Process Definition

Create a `.bpm` file with your process:

```bpm
process "My First Process" {
    id: "my-first-process"
    version: "1.0"
    
    start "Process Started" {
        id: "start-1"
    }
    
    scriptCall "Do Something" {
        id: "task-1"
        script: "doSomething(input)"
        inputVars: ["input"]
        outputVars: ["result"]
    }
    
    end "Process Complete" {
        id: "end-1"
    }
    
    flow {
        "start-1" -> "task-1"
        "task-1" -> "end-1"
    }
}
```

### 2. Convert to BPMN

```bash
PYTHONPATH=src python3 -m bpm_dsl.cli convert my-process.bpm
```

This generates `my-process.bpmn` ready for Camunda Zeebe!

### 3. Validate Your Process

```bash
PYTHONPATH=src python3 -m bpm_dsl.cli validate my-process.bpm
```

### 4. Get Process Information

```bash
PYTHONPATH=src python3 -m bpm_dsl.cli info my-process.bpm
```

## DSL Syntax Reference

### Process Structure
```bmp
process "Process Name" {
    id: "unique-process-id"
    version: "1.0"
    
    // Elements go here
    
    flow {
        // Flow definitions go here
    }
}
```

### Elements

#### Start Event
```bpm
start "Event Name" {
    id: "unique-id"
}
```

#### End Event
```bpm
end "Event Name" {
    id: "unique-id"
}
```

#### Script Call
```bpm
scriptCall "Task Name" {
    id: "unique-id"
    script: "javascript_expression"
    inputVars: ["var1", "var2"]
    outputVars: ["result1", "result2"]
}
```

#### XOR Gateway
```bpm
xorGateway "Decision Name" {
    id: "unique-id"
    condition: "boolean_expression"
}
```

### Flows
```bpm
flow {
    "source-id" -> "target-id"
    "gateway-id" -> "task-id" [condition: "variable == value"]
}
```

## Examples

The project includes several examples:

- `example_process.bpm` - Complex order processing workflow
- `examples/simple_approval.bpm` - Document approval process
- `test_simple.bpm` - Minimal example

## Programmatic Usage

```python
from bpm_dsl.parser import parse_bpm_file
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.validator import ProcessValidator

# Parse a DSL file
process = parse_bpm_file("my-process.bpm")

# Validate the process
validator = ProcessValidator()
result = validator.validate(process)

if result.is_valid:
    # Generate BPMN
    generator = BPMNGenerator()
    xml_content = generator.generate(process)
    
    # Save to file
    generator.save_to_file(process, "output.bpmn")
```

## Zeebe Deployment

The generated BPMN files are fully compatible with Camunda Zeebe:

1. **Deploy using Zeebe CLI:**
   ```bash
   zbctl deploy my-process.bpmn
   ```

2. **Deploy using Camunda Modeler:**
   - Open the generated `.bpmn` file
   - Deploy to your Zeebe cluster

3. **Deploy programmatically:**
   ```python
   from zeebe_grpc import ZeebeClient
   
   client = ZeebeClient()
   client.deploy_process("my-process.bpmn")
   ```

## Features

✅ **Complete DSL** with 4 primitive elements  
✅ **BPMN 2.0 XML** generation  
✅ **Zeebe compatibility** with proper extensions  
✅ **Process validation** with error reporting  
✅ **CLI interface** for easy usage  
✅ **Programmatic API** for integration  
✅ **Comprehensive tests** ensuring reliability  

## Troubleshooting

### Common Issues

1. **Module not found errors:**
   ```bash
   # Make sure to set PYTHONPATH
   PYTHONPATH=src python3 -m bpm_dsl.cli --help
   ```

2. **Parse errors:**
   - Check syntax against the grammar in `DSL_GRAMMAR.md`
   - Ensure all IDs are unique
   - Verify all quotes are properly closed

3. **Validation errors:**
   - Run `validate` command to see specific issues
   - Check that all flow references point to existing elements
   - Ensure process has at least one start and end event

### Getting Help

- Check `DSL_GRAMMAR.md` for complete syntax reference
- Run `python3 demo.py` for a complete demonstration
- Look at example files in `examples/` directory
- Run tests with `PYTHONPATH=src python3 -m pytest tests/`

## Next Steps

1. **Create your own processes** using the DSL syntax
2. **Integrate with your workflow** using the programmatic API
3. **Deploy to Camunda Zeebe** for execution
4. **Extend the DSL** by adding new primitives as needed

Happy process modeling! 🚀
