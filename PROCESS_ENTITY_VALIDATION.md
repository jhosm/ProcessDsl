# ProcessEntity Automatic Validation Pattern

## Overview
ProcessEntity elements now automatically generate an **XOR gateway pattern** that checks for validation errors and terminates the workflow if validation fails, while continuing the normal flow when validation succeeds.

## Generated BPMN Structure

When a `processEntity` is defined in the DSL, the BPMN generator automatically creates:

1. **ServiceTask** - The processEntity validation task
2. **XOR Gateway** - Checks `entityValidationResult.isValid`
3. **Error End Event** - Terminates workflow on validation failure
4. **Sequence Flows**:
   - processEntity → validation gateway
   - validation gateway → error end (condition: `entityValidationResult.isValid = false`)
   - validation gateway → next task (default flow when validation succeeds)

## DSL Syntax

```bpm
processEntity "Load Customer Data" {
    entityName: "Customer"
}
```

**Note**: The `entityModel` path is automatically inferred from the matching OpenAPI YAML file (with the same name as the `.bpm` file). See [OPENAPI_VALIDATION.md](OPENAPI_VALIDATION.md) for details.

## Generated BPMN XML

### Error Definition (at Definitions Level)
```xml
<error id="process-entity-validation-error" name="Process Entity Validation Error" errorCode="PROCESS_ENTITY_VALIDATION_ERROR"/>
```

### ServiceTask
```xml
<serviceTask id="load-customer-data" name="Load Customer Data">
  <extensionElements>
    <zeebe:taskDefinition type="process-entity-validator" retries="3"/>
    <zeebe:taskHeaders>
      <zeebe:header key="entityModel" value="customer-api.yaml"/>
      <zeebe:header key="entityName" value="Customer"/>
    </zeebe:taskHeaders>
    <zeebe:ioMapping>
      <zeebe:input source="=processEntity" target="processEntity"/>
      <zeebe:output source="=validationResult" target="entityValidationResult"/>
    </zeebe:ioMapping>
  </extensionElements>
</serviceTask>
```

### XOR Gateway
```xml
<exclusiveGateway 
  id="load-customer-data-validation-gateway" 
  name="Validation Check" 
  default="flow_load-customer-data-validation-gateway_to_process-customer"/>
```

### Error End Event
```xml
<endEvent id="load-customer-data-validation-error" name="Validation Error">
  <errorEventDefinition 
    id="load-customer-data-validation-error-def" 
    errorRef="process-entity-validation-error"/>
</endEvent>
```

### Sequence Flows

**Flow to Gateway:**
```xml
<sequenceFlow 
  id="flow_load-customer-data_to_load-customer-data-validation-gateway" 
  sourceRef="load-customer-data" 
  targetRef="load-customer-data-validation-gateway"/>
```

**Flow to Error (Validation Failed):**
```xml
<sequenceFlow 
  id="flow_load-customer-data-validation-gateway_to_load-customer-data-validation-error" 
  sourceRef="load-customer-data-validation-gateway" 
  targetRef="load-customer-data-validation-error">
  <conditionExpression xsi:type="tFormalExpression">
    =entityValidationResult.isValid = false
  </conditionExpression>
</sequenceFlow>
```

**Flow to Next Task (Validation Passed - Default):**
```xml
<sequenceFlow 
  id="flow_load-customer-data-validation-gateway_to_process-customer" 
  sourceRef="load-customer-data-validation-gateway" 
  targetRef="process-customer"/>
```

## Implementation Details

### Modified Files

#### `src/bpm_dsl/bpmn_generator.py`

1. **`_add_process_entity()`** - Enhanced to generate:
   - Original serviceTask
   - XOR gateway with ID: `{process-entity-id}-validation-gateway`
   - Error end event with ID: `{process-entity-id}-validation-error`
   - Error event definition referencing `validation-error`

2. **`_add_flows()`** - Enhanced to automatically handle processEntity flows:
   - Detects flows targeting processEntity
   - Creates validation flows automatically
   - Redirects flows from processEntity to come from validation gateway instead
   - Sets default flow on gateway for success case

3. **`_add_diagram()`** - Enhanced to position generated elements:
   - Gateway positioned 80px to the right of processEntity
   - Error end positioned 60px below gateway
   - Generates diagram edges for all validation flows

4. **`_add_generated_flow_diagrams()`** - New method:
   - Creates diagram information for validation flows
   - Calculates waypoints for proper edge routing
   - Skips original flow diagrams from processEntity (handled here instead)

### Element Naming Convention

Generated elements follow a consistent naming pattern:
- **Gateway ID**: `{process-entity-id}-validation-gateway`
- **Gateway Name**: `"Validation Check"`
- **Error End ID**: `{process-entity-id}-validation-error`
- **Error End Name**: `"Validation Error"`

### Diagram Layout

```
[ProcessEntity] ---> [XOR Gateway] ---> [Next Task]
                           |
                           v
                    [Error End Event]
```

**Spacing:**
- Gateway: 80px right of processEntity
- Error End: 60px below gateway, centered horizontally

## Example Process Flow

**DSL Input:**
```bpm
process "Process Entity Demo" {
    id: "process-entity-demo"
    
    start "Start Process" {
        id: "start-event"
    }
    
    processEntity "Load Customer Data" {
        entityName: "Customer"
    }
    
    scriptCall "Process Customer" {
        id: "process-customer"
        script: "customerScore = calculateScore(customerData)"
    }
    
    end "End Process" {
        id: "end-event"
    }
    
    flow {
        "start-event" -> "load-customer-data"
        "load-customer-data" -> "process-customer"
        "process-customer" -> "end-event"
    }
}
```

**Generated Flow:**
1. `start-event` → `load-customer-data`
2. `load-customer-data` → `load-customer-data-validation-gateway`
3. `load-customer-data-validation-gateway` → `load-customer-data-validation-error` (if invalid)
4. `load-customer-data-validation-gateway` → `process-customer` (if valid, default)
5. `process-customer` → `end-event`

## Validation Result Structure

The job worker must return `validationResult` with the following structure:

```json
{
  "isValid": true|false,
  "errors": [
    {
      "field": "fieldName",
      "message": "Error message"
    }
  ]
}
```

## Benefits

1. **Automatic Error Handling** - No need to manually add validation gateways
2. **Consistent Pattern** - All processEntity elements follow the same validation pattern
3. **Clean DSL Syntax** - Validation logic is implicit, keeping DSL files simple
4. **Type Safety** - Uses proper BPMN error events for validation failures
5. **Workflow Transparency** - Generated BPMN clearly shows validation paths

## Constraints

- Only **one processEntity** allowed per process
- ProcessEntity must be the **first task after start event**
- These constraints are enforced by the validator

## Compatibility

- ✅ Camunda Zeebe compatible
- ✅ BPMN 2.0 compliant
- ✅ Works with all existing DSL features
- ✅ Maintains backward compatibility with error event handling
