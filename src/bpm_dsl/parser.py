"""BPM DSL Parser using Lark."""

import os
import re
from pathlib import Path
from typing import List, Optional, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, XORGateway, 
    Flow, Element, ASTNode, VariableMapping
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
    
    def __init__(self):
        super().__init__()
    
    @v_args(inline=True)
    def STRING(self, s):
        """Remove quotes from string literals."""
        return s[1:-1]  # Remove surrounding quotes
    
    @v_args(inline=True)
    def process(self, name: str, body: dict) -> Process:
        """Create a Process node."""
        return Process(
            name=name,
            id=body.get('id', f"process_{name.lower().replace(' ', '_')}"),
            version=body.get('version'),
            elements=body.get('elements', []),
            flows=body.get('flows', [])
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
        
        if len(items) > 2 and isinstance(items[2], str):
            condition = items[2]
        
        return Flow(source_id=source_id, target_id=target_id, condition=condition)
    
    @v_args(inline=True)
    def flow_condition(self, when: str) -> str:
        """Extract flow when condition."""
        return when
    
    def string_array(self, items) -> List[str]:
        """Create string array."""
        return [item for item in items if isinstance(item, str)]
    
    def mapping_array(self, items) -> List[VariableMapping]:
        """Create variable mapping array."""
        return [item for item in items if isinstance(item, VariableMapping)]
    
    @v_args(inline=True)
    def variable_mapping(self, source: str, target: str) -> VariableMapping:
        """Create a variable mapping from arrow syntax: 'source' -> 'target'."""
        return VariableMapping(source=source, target=target)


class BPMParser:
    """Main parser for BPM DSL files."""
    
    def __init__(self):
        """Initialize the parser with the grammar."""
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path, 'r') as f:
            grammar = f.read()
        
        self.parser = Lark(
            grammar,
            parser='lalr',
            transformer=BPMTransformer(),
            start='start'
        )
    
    def parse_file(self, file_path: Union[str, Path]) -> Process:
        """Parse a BPM DSL file and return the AST."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_string(content)
    
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
