# BPM DSL Grammar Specification

## Overview
This document defines the grammar for the BPM DSL that generates Zeebe-compatible BPMN files.

## Grammar Rules (EBNF)

```ebnf
process = "process" STRING "{" process_body "}"

process_body = process_metadata element* flow_section

process_metadata = ("id:" STRING)? ("version:" STRING)?

element = start_element | end_element | script_call | xor_gateway

start_element = "start" STRING "{" start_properties "}"
start_properties = "id:" STRING

end_element = "end" STRING "{" end_properties "}"
end_properties = "id:" STRING

script_call = "scriptCall" STRING "{" script_properties "}"
script_properties = "id:" STRING 
                   "script:" STRING
                   ("inputVars:" string_array)?
                   ("outputVars:" string_array)?

xor_gateway = "xorGateway" STRING "{" gateway_properties "}"
gateway_properties = "id:" STRING
                    ("condition:" STRING)?

flow_section = "flow" "{" flow_definition* "}"
flow_definition = STRING "->" STRING ("[" flow_condition "]")?
flow_condition = "condition:" STRING

string_array = "[" (STRING ("," STRING)*)? "]"
STRING = '"' [^"]* '"'
```

## Primitive Elements

### 1. Start Event
- **Syntax**: `start "Event Name" { id: "unique-id" }`
- **Purpose**: Defines the starting point of the process
- **BPMN Mapping**: `<bpmn:startEvent>`

### 2. End Event
- **Syntax**: `end "Event Name" { id: "unique-id" }`
- **Purpose**: Defines an end point of the process
- **BPMN Mapping**: `<bpmn:endEvent>`

### 3. Script Call
- **Syntax**: 
  ```
  scriptCall "Task Name" {
      id: "unique-id"
      script: "javascript_expression"
      inputVars: ["var1", "var2"]
      outputVars: ["result1", "result2"]
  }
  ```
- **Purpose**: Executes a script/expression
- **BPMN Mapping**: `<bpmn:scriptTask>` with Zeebe script job type

### 4. XOR Gateway
- **Syntax**: 
  ```
  xorGateway "Gateway Name" {
      id: "unique-id"
      condition: "boolean_expression"
  }
  ```
- **Purpose**: Exclusive decision point in the process
- **BPMN Mapping**: `<bpmn:exclusiveGateway>`

## Flow Definitions
- **Syntax**: `"source-id" -> "target-id" [condition: "expression"]`
- **Purpose**: Defines sequence flows between elements
- **BPMN Mapping**: `<bpmn:sequenceFlow>`

## Example Usage
See `example_process.bpm` for a complete example demonstrating all primitives.

## Zeebe Compatibility Notes
- Script tasks will use `zeebe:script` extension elements
- Conditions will be mapped to `bpmn:conditionExpression`
- All IDs must be unique within the process
- Variable mappings will use Zeebe's input/output variable mappings
