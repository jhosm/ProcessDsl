"""BPM DSL Parser using Lark."""

import os
import re
from pathlib import Path
from typing import List, Optional, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, ServiceTask, ProcessEntity, Gateway,
    Flow, Element, ASTNode, VariableMapping, TaskHeader,
    TimerDefinition, TimerEvent, BoundaryTimerEvent, BoundaryErrorEvent,
    BoundaryEvent,
)


def desugar_duration(shorthand: str) -> str:
    """Convert duration shorthand to ISO 8601 duration.

    Examples:
        "30s"    -> "PT30S"
        "5m"     -> "PT5M"
        "2h"     -> "PT2H"
        "1d"     -> "P1D"
        "2h30m"  -> "PT2H30M"
        "1d12h"  -> "P1DT12H"

    The ISO 8601 duration format uses P for the period designator and T to
    separate the date portion (days) from the time portion (hours, minutes,
    seconds).  E.g. P1DT2H30M means 1 day, 2 hours, 30 minutes.
    """
    # Parse individual components from the shorthand
    parts = re.findall(r'(\d+)([dhms])', shorthand)
    if not parts:
        return shorthand  # Not shorthand, return as-is

    date_part = ""  # Before T (days)
    time_part = ""  # After T (hours, minutes, seconds)

    for value, unit in parts:
        if unit == 'd':
            date_part += f"{value}D"
        elif unit == 'h':
            time_part += f"{value}H"
        elif unit == 'm':
            time_part += f"{value}M"
        elif unit == 's':
            time_part += f"{value}S"

    result = "P"
    if date_part:
        result += date_part
    if time_part:
        result += "T" + time_part
    elif not date_part:
        # Edge case: no components matched
        return shorthand

    return result


def to_kebab_case(name: str) -> str:
    """Convert a name to kebab-case for use as an ID.
    
    Examples:
        "Process Data" -> "process-data"
        "Order Valid?" -> "order-valid"
        "Start Demo" -> "start-demo"
    """
    # Remove quotes and special characters, keep alphanumeric and spaces
    clean_name = re.sub(r'[^\w\s]', '', name)
    # Replace spaces and underscores with hyphens, convert to lowercase
    kebab_name = re.sub(r'[\s_]+', '-', clean_name.strip()).lower()
    return kebab_name


class BPMTransformer(Transformer):
    """Transforms the parse tree into AST nodes."""
    
    def __init__(self, openapi_file_path: Optional[str] = None):
        super().__init__()
        self.openapi_file_path = openapi_file_path
    
    @v_args(inline=True)
    def STRING(self, s):
        """Remove quotes from string literals."""
        return s[1:-1]  # Remove surrounding quotes
    
    @v_args(inline=True)
    def NUMBER(self, n):
        """Convert number token to integer."""
        return int(n)

    @v_args(inline=True)
    def DURATION_SHORTHAND(self, s):
        """Keep raw shorthand token as a string (desugared later)."""
        return str(s)

    @v_args(inline=True)
    def BOOLEAN(self, s):
        """Convert boolean token to Python bool."""
        return str(s) == "true"

    @v_args(inline=True)
    def GATEWAY_TYPE(self, s):
        """Keep gateway type as a string."""
        return str(s)

    @v_args(inline=True)
    def OTHERWISE(self, s):
        """Mark otherwise token."""
        return {"is_default": True}
    
    @v_args(inline=True)
    def process(self, name: str, body: dict) -> Process:
        """Create a Process node."""
        return Process(
            name=name,
            id=body.get('id', f"process_{name.lower().replace(' ', '_')}"),
            version=body.get('version'),
            elements=body.get('elements', []),
            flows=body.get('flows', []),
            openapi_file_path=self.openapi_file_path
        )
    
    def process_body(self, items) -> dict:
        """Collect process body components."""
        result = {
            'id': None,
            'version': None,
            'elements': [],
            'flows': []
        }
        
        for item in items:
            if isinstance(item, dict):
                if 'flows' in item:
                    result['flows'] = item['flows']
                else:
                    result.update(item)
            elif isinstance(item, Element):
                result['elements'].append(item)
        
        return result
    
    def process_metadata(self, items) -> dict:
        """Extract process metadata."""
        result = {}
        for item in items:
            if isinstance(item, dict):
                result.update(item)
        return result
    
    @v_args(inline=True)
    def process_id(self, id_value: str) -> dict:
        """Extract process ID."""
        return {'id': id_value}
    
    @v_args(inline=True)
    def process_version(self, version: str) -> dict:
        """Extract process version."""
        return {'version': version}
    
    def element(self, items) -> Element:
        """Extract element from parse tree."""
        # The element rule should contain exactly one element
        return items[0]
    
    @v_args(inline=True)
    def start_element(self, name: str, properties: dict) -> StartEvent:
        """Create a StartEvent node."""
        element_id = properties.get('id', to_kebab_case(name))
        timer = properties.get('timer')
        return StartEvent(name=name, id=element_id, timer=timer)
    
    @v_args(inline=True)
    def end_element(self, name: str, properties: dict) -> EndEvent:
        """Create an EndEvent node."""
        element_id = properties.get('id', to_kebab_case(name))
        return EndEvent(name=name, id=element_id)
    
    @v_args(inline=True)
    def script_call(self, name: str, properties: dict) -> ScriptCall:
        """Create a ScriptCall node."""
        element_id = properties.get('id', to_kebab_case(name))
        return ScriptCall(
            name=name,
            id=element_id,
            script=properties.get('script', ''),
            input_mappings=properties.get('input_mappings', []),
            output_mappings=properties.get('output_mappings', []),
            result_variable=properties.get('result_variable')
        )
    
    @v_args(inline=True)
    def service_task(self, name: str, properties: dict) -> ServiceTask:
        """Create a ServiceTask node.

        Boundary events arrive in the properties dict as a list.  After
        constructing the ServiceTask we patch each boundary event's
        ``attached_to_ref`` to point back to this task's ID — this is
        the nesting-to-sibling transformation described in the AST node
        docstring.
        """
        element_id = properties.get('id', to_kebab_case(name))
        boundary_events = properties.get('boundary_events', [])
        task = ServiceTask(
            name=name,
            id=element_id,
            task_type=properties.get('task_type', ''),
            retries=properties.get('retries'),
            headers=properties.get('headers', []),
            input_mappings=properties.get('input_mappings', []),
            output_mappings=properties.get('output_mappings', []),
            boundary_events=boundary_events,
        )
        # Back-link each boundary event to this parent task
        for be in task.boundary_events:
            be.attached_to_ref = element_id
        return task
    
    @v_args(inline=True)
    def process_entity(self, name: str, properties: dict) -> ProcessEntity:
        """Create a ProcessEntity node."""
        # Always use kebab-case for the id
        element_id = to_kebab_case(name)
        return ProcessEntity(
            name=name,
            id=element_id,
            entity_name=properties.get('entity_name', '')
        )
    
    @v_args(inline=True)
    def gateway(self, name: str, properties: dict) -> Gateway:
        """Create a Gateway node."""
        element_id = properties.get('id', to_kebab_case(name))
        return Gateway(
            name=name,
            id=element_id,
            gateway_type=properties.get('gateway_type', 'xor'),
            condition=properties.get('condition'),
        )
    
    def start_properties(self, items) -> dict:
        """Extract start element properties."""
        return self._extract_properties(items)
    
    def end_properties(self, items) -> dict:
        """Extract end element properties."""
        return self._extract_properties(items)
    
    def script_properties(self, items) -> dict:
        """Extract script call properties."""
        return self._extract_properties(items)
    
    def service_properties(self, items) -> dict:
        """Extract service task properties, collecting boundary events."""
        properties = {}
        boundary_events = []
        for item in items:
            if isinstance(item, BoundaryEvent):
                boundary_events.append(item)
            elif isinstance(item, dict):
                properties.update(item)
        if boundary_events:
            properties['boundary_events'] = boundary_events
        return properties
    
    def process_entity_properties(self, items) -> dict:
        """Extract process entity properties."""
        return self._extract_properties(items)
    
    def gateway_properties(self, items) -> dict:
        """Extract gateway properties."""
        return self._extract_properties(items)
    
    def _extract_properties(self, items) -> dict:
        """Helper to extract properties from items."""
        properties = {}
        for item in items:
            if isinstance(item, dict):
                properties.update(item)
        return properties
    
    @v_args(inline=True)
    def element_id(self, id_value: str) -> dict:
        """Extract element ID."""
        return {'id': id_value}
    
    @v_args(inline=True)
    def script_code(self, script: str) -> dict:
        """Extract script code."""
        return {'script': script}
    
    @v_args(inline=True)
    def input_mappings(self, mappings_list: List[VariableMapping]) -> dict:
        """Extract input variable mappings."""
        return {'input_mappings': mappings_list}
    
    @v_args(inline=True)
    def output_mappings(self, mappings_list: List[VariableMapping]) -> dict:
        """Extract output variable mappings."""
        return {'output_mappings': mappings_list}
    
    @v_args(inline=True)
    def input_vars(self, vars_list: List[str]) -> dict:
        """Extract input variables and convert to simple mappings."""
        mappings = [VariableMapping(source=var, target=var) for var in vars_list]
        return {'input_mappings': mappings}
    
    @v_args(inline=True)
    def output_vars(self, vars_list: List[str]) -> dict:
        """Extract output variables and convert to simple mappings."""
        mappings = [VariableMapping(source=var, target=var) for var in vars_list]
        return {'output_mappings': mappings}
    
    @v_args(inline=True)
    def result_variable(self, result_var: str) -> dict:
        """Extract result variable."""
        return {'result_variable': result_var}
    
    @v_args(inline=True)
    def task_type(self, type_value: str) -> dict:
        """Extract service task type."""
        return {'task_type': type_value}
    
    @v_args(inline=True)
    def task_retries(self, retries_value) -> dict:
        """Extract service task retries."""
        return {'retries': int(retries_value)}
    
    @v_args(inline=True)
    def task_headers(self, headers_list: List[TaskHeader]) -> dict:
        """Extract service task headers."""
        return {'headers': headers_list}
    
    @v_args(inline=True)
    def entity_type(self, type_value: str) -> dict:
        """Extract process entity type."""
        return {'entity_type': type_value}
    
    
    @v_args(inline=True)
    def entity_name(self, name_value: str) -> dict:
        """Extract process entity name."""
        return {'entity_name': name_value}
    
    @v_args(inline=True)
    def gateway_type(self, type_value) -> dict:
        """Extract gateway type (xor, parallel)."""
        return {'gateway_type': str(type_value)}

    @v_args(inline=True)
    def gateway_condition(self, when: str) -> dict:
        """Extract gateway when condition."""
        return {'condition': when}

    @v_args(inline=True)
    def gateway_type(self, type_value: str) -> dict:
        """Extract gateway type (xor, parallel)."""
        return {'gateway_type': type_value}

    # ── Timer element transformers ──────────────────────────────────

    def duration_value(self, items) -> str:
        """Extract and desugar a duration value.

        The grammar rule ``duration_value: STRING | DURATION_SHORTHAND``
        produces exactly one child.  If it is a DURATION_SHORTHAND token
        we convert it to ISO 8601 via ``desugar_duration``.  Quoted
        strings are assumed to already be ISO 8601 and passed through.
        """
        raw = items[0]
        # DURATION_SHORTHAND tokens match /\d+[dhms](\d+[hms]){0,3}/
        if re.fullmatch(r'\d+[dhms](\d+[hms]){0,3}', str(raw)):
            return desugar_duration(str(raw))
        return str(raw)

    @v_args(inline=True)
    def timer_duration(self, duration: str) -> dict:
        """Extract timer duration property."""
        return {'duration': duration}

    @v_args(inline=True)
    def timer_date(self, date: str) -> dict:
        """Extract timer date property."""
        return {'date': date}

    @v_args(inline=True)
    def timer_cycle(self, cycle: str) -> dict:
        """Extract timer cycle property."""
        return {'cycle': cycle}

    @v_args(inline=True)
    def cycle_expr(self, duration: str) -> str:
        """Transform cycle(duration) into an ISO 8601 repeating interval.

        ``cycle("PT1H")`` or ``cycle(1h)`` both become ``"R/PT1H"``.
        """
        return f"R/{duration}"

    def timer_properties(self, items) -> dict:
        """Collect timer element properties."""
        return self._extract_properties(items)

    @v_args(inline=True)
    def timer_element(self, name: str, properties: dict) -> TimerEvent:
        """Create a TimerEvent node."""
        element_id = properties.get('id', to_kebab_case(name))
        timer_def = TimerDefinition(
            duration=properties.get('duration'),
            date=properties.get('date'),
            cycle=properties.get('cycle'),
        )
        return TimerEvent(name=name, id=element_id, timer=timer_def)

    @v_args(inline=True)
    def start_timer(self, cycle: str) -> dict:
        """Extract timer for a start event (always a cycle)."""
        return {'timer': TimerDefinition(cycle=cycle)}

    # ── Boundary event transformers ──────────────────────────────────

    @v_args(inline=True)
    def boundary_interrupting(self, value: bool) -> dict:
        """Extract the interrupting flag."""
        return {'interrupting': value}

    @v_args(inline=True)
    def error_code(self, code: str) -> dict:
        """Extract the errorCode property."""
        return {'error_code': code}

    def on_timer_properties(self, items) -> dict:
        """Collect onTimer boundary event properties."""
        return self._extract_properties(items)

    def on_error_properties(self, items) -> dict:
        """Collect onError boundary event properties."""
        return self._extract_properties(items)

    @v_args(inline=True)
    def on_timer(self, name: str, properties: dict) -> BoundaryTimerEvent:
        """Create a BoundaryTimerEvent node.

        ``attached_to_ref`` is set later by the parent ``service_task``
        transformer once it knows its own ID.
        """
        element_id = to_kebab_case(name)
        return BoundaryTimerEvent(
            name=name,
            id=element_id,
            interrupting=properties.get('interrupting', True),
            duration=properties.get('duration'),
        )

    @v_args(inline=True)
    def on_error(self, name: str, properties: dict) -> BoundaryErrorEvent:
        """Create a BoundaryErrorEvent node."""
        element_id = to_kebab_case(name)
        return BoundaryErrorEvent(
            name=name,
            id=element_id,
            interrupting=properties.get('interrupting', True),
            error_code=properties.get('error_code'),
        )

    def boundary_event(self, items):
        """Pass through the boundary event node."""
        return items[0]

    def flow_section(self, items) -> dict:
        """Create flow section."""
        flows = [item for item in items if isinstance(item, Flow)]
        return {'flows': flows}
    
    def flow_definition(self, items) -> Flow:
        """Create a Flow node."""
        source_id = items[0]
        target_id = items[1]
        condition = None
        is_default = False
        
        if len(items) > 2:
            flow_condition_result = items[2]
            if isinstance(flow_condition_result, dict):
                if flow_condition_result.get('is_default'):
                    is_default = True
                else:
                    condition = flow_condition_result.get('condition')
            elif isinstance(flow_condition_result, str):
                condition = flow_condition_result
        
        return Flow(source_id=source_id, target_id=target_id, condition=condition, is_default=is_default)
    
    def flow_condition(self, items):
        """Extract flow condition or otherwise (default) marker."""
        if len(items) == 1:
            item = items[0]
            # OTHERWISE terminal is transformed into {'is_default': True}
            if isinstance(item, dict) and item.get('is_default'):
                return {'is_default': True}
            # Fallback: check for OTHERWISE token type
            if hasattr(item, 'type') and item.type == "OTHERWISE":
                return {'is_default': True}
            elif hasattr(item, 'value') and item.value == "otherwise":
                return {'is_default': True}
            else:
                return {'condition': item}
        return {'condition': None}
    
    def string_array(self, items) -> List[str]:
        """Create string array."""
        return [item for item in items if isinstance(item, str)]
    
    def mapping_array(self, items) -> List[VariableMapping]:
        """Create variable mapping array."""
        return [item for item in items if isinstance(item, VariableMapping)]
    
    def header_array(self, items) -> List[TaskHeader]:
        """Create task header array."""
        return [item for item in items if isinstance(item, TaskHeader)]
    
    @v_args(inline=True)
    def variable_mapping(self, source: str, target: str) -> VariableMapping:
        """Create a variable mapping from arrow syntax: 'source' -> 'target'."""
        return VariableMapping(source=source, target=target)
    
    @v_args(inline=True)
    def task_header(self, key: str, value: str) -> TaskHeader:
        """Create a task header from arrow syntax: 'key' -> 'value'."""
        return TaskHeader(key=key, value=value)


class BPMParser:
    """Main parser for BPM DSL files."""
    
    def __init__(self, openapi_file_path: Optional[str] = None):
        """Initialize the parser with the grammar."""
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path, 'r') as f:
            grammar = f.read()
        
        self.parser = Lark(
            grammar,
            parser='lalr',
            transformer=BPMTransformer(openapi_file_path),
            start='start'
        )
    
    def parse_file(self, file_path: Union[str, Path]) -> Process:
        """Parse a BPM DSL file and return the AST.
        
        Validates that a corresponding OpenAPI YAML file exists with the same base name.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate and get the OpenAPI YAML file path
        openapi_file_path = self._validate_openapi_file(file_path)
        
        # Re-initialize parser with the OpenAPI file path
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path, 'r') as f:
            grammar = f.read()
        
        self.parser = Lark(
            grammar,
            parser='lalr',
            transformer=BPMTransformer(str(openapi_file_path)),
            start='start'
        )
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_string(content)
    
    def _validate_openapi_file(self, bpm_file_path: Path) -> Path:
        """Validate that a matching OpenAPI YAML file exists for the .bpm file.
        
        Args:
            bpm_file_path: Path to the .bpm file
            
        Returns:
            Path: The path to the matching OpenAPI file
            
        Raises:
            FileNotFoundError: If no matching .yaml or .yml file is found
        """
        base_name = bpm_file_path.stem  # Get filename without extension
        parent_dir = bpm_file_path.parent
        
        # Check for .yaml or .yml extensions
        yaml_file = parent_dir / f"{base_name}.yaml"
        yml_file = parent_dir / f"{base_name}.yml"
        
        if yaml_file.exists():
            return yaml_file
        elif yml_file.exists():
            return yml_file
        else:
            raise FileNotFoundError(
                f"Missing OpenAPI specification file for '{bpm_file_path.name}'. "
                f"Expected '{yaml_file.name}' or '{yml_file.name}' in the same directory."
            )
    
    def parse_string(self, content: str) -> Process:
        """Parse a BPM DSL string and return the AST."""
        try:
            result = self.parser.parse(content)
            return result
        except LarkError as e:
            raise ValueError(f"Parse error: {e}")


# Convenience function
def parse_bpm_file(file_path: Union[str, Path]) -> Process:
    """Parse a BPM file and return the process AST."""
    parser = BPMParser()
    return parser.parse_file(file_path)


def parse_bpm_string(content: str) -> Process:
    """Parse a BPM string and return the process AST."""
    parser = BPMParser()
    return parser.parse_string(content)
