"""BPM DSL Parser using Lark."""

import os
import re
from pathlib import Path
from typing import List, Optional, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, ServiceTask, ProcessEntity, XORGateway, 
    Flow, Element, ASTNode, VariableMapping, TaskHeader
)


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
        return StartEvent(name=name, id=element_id)
    
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
        """Create a ServiceTask node."""
        element_id = properties.get('id', to_kebab_case(name))
        return ServiceTask(
            name=name,
            id=element_id,
            task_type=properties.get('task_type', ''),
            retries=properties.get('retries'),
            headers=properties.get('headers', []),
            input_mappings=properties.get('input_mappings', []),
            output_mappings=properties.get('output_mappings', [])
        )
    
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
    def xor_gateway(self, name: str, properties: dict) -> XORGateway:
        """Create an XORGateway node."""
        element_id = properties.get('id', to_kebab_case(name))
        return XORGateway(
            name=name,
            id=element_id,
            condition=properties.get('condition')
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
        """Extract service task properties."""
        return self._extract_properties(items)
    
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
    def gateway_condition(self, when: str) -> dict:
        """Extract gateway when condition."""
        return {'condition': when}
    
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
        """Extract flow condition or default marker."""
        if len(items) == 1:
            item = items[0]
            # Check if it's a Token with value "default"
            if hasattr(item, 'value') and item.value == "default":
                return {'is_default': True}
            elif item == "default":
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
