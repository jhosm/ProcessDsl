# OpenAPI File Validation

## Overview

Every BPM process definition (`.bpm` file) **must** have a corresponding OpenAPI specification file (`.yaml` or `.yml`) with the same base name in the same directory.

## Requirement

When parsing a `.bpm` file, the parser automatically validates that a matching OpenAPI YAML file exists. This ensures that every process definition has a well-defined API contract.

## File Naming Convention

For a given `.bpm` file, one of the following must exist:

- `{filename}.yaml`
- `{filename}.yml`

### Examples

| BPM File | Required OpenAPI File |
|----------|----------------------|
| `process_entity_demo.bpm` | `process_entity_demo.yaml` or `process_entity_demo.yml` |
| `order_processing.bpm` | `order_processing.yaml` or `order_processing.yml` |
| `customer_onboarding.bpm` | `customer_onboarding.yaml` or `customer_onboarding.yml` |

## Validation Behavior

### Success Case
```python
from bpm_dsl.parser import parse_bpm_file

# This will succeed if process_entity_demo.yaml exists
process = parse_bpm_file('examples/process_entity_demo.bpm')
```

### Error Case
```python
from bpm_dsl.parser import parse_bpm_file

# This will raise FileNotFoundError if no matching .yaml/.yml file exists
try:
    process = parse_bpm_file('examples/missing_yaml.bpm')
except FileNotFoundError as e:
    print(e)
    # Output: Missing OpenAPI specification file for 'missing_yaml.bpm'. 
    #         Expected 'missing_yaml.yaml' or 'missing_yaml.yml' in the same directory.
```

## OpenAPI File Structure

The OpenAPI specification file should follow the OpenAPI 3.0+ specification format. At minimum, it should include:

```yaml
openapi: 3.0.3
info:
  title: Process API
  description: API specification for the process
  version: 1.0.0

components:
  schemas:
    # Define your data schemas here
    EntityName:
      type: object
      properties:
        # Define properties

paths:
  # Define API endpoints (optional but recommended)
```

## Rationale

This validation ensures:

1. **API-First Design**: Every process has a well-defined API contract
2. **Documentation**: OpenAPI specs serve as living documentation
3. **Validation**: Entity schemas can be validated against the OpenAPI specification
4. **Consistency**: Enforces a standard structure for process definitions
5. **Integration**: Facilitates integration with API gateways and documentation tools

## Implementation Details

The validation is performed in the `BPMParser.parse_file()` method before parsing the DSL content. This ensures:

- Early validation (fail fast)
- Clear error messages
- No partial processing of invalid configurations

## Bypassing Validation

If you need to parse BPM DSL content without file validation (e.g., for testing), use the `parse_string()` method instead:

```python
from bpm_dsl.parser import parse_bpm_string

dsl_content = '''
process "Test Process" {
    start "Begin" {}
    end "Complete" {}
    flow {
        "begin" -> "complete"
    }
}
'''

# No file validation performed
process = parse_bpm_string(dsl_content)
```

## Migration Guide

If you have existing `.bpm` files without matching OpenAPI files:

1. Create a minimal OpenAPI specification file for each `.bpm` file
2. Use the same base filename with `.yaml` or `.yml` extension
3. Define schemas for any entities referenced in `processEntity` elements
4. Run your parser to verify the files are valid

### Minimal OpenAPI Template

```yaml
openapi: 3.0.3
info:
  title: {Process Name} API
  description: API specification for {process name}
  version: 1.0.0

components:
  schemas:
    GenericEntity:
      type: object
      properties:
        id:
          type: string
          description: Entity identifier

paths: {}
```

## Related Features

- **ProcessEntity Validation**: The `processEntity` DSL element references schemas defined in the OpenAPI file
- **Automatic Path Inference**: The OpenAPI file path is automatically inferred from the `.bpm` file name
- **Job Workers**: Job workers receive the OpenAPI file path in the `entityModel` header for runtime validation
