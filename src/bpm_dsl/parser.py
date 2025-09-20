"""BPM DSL Parser using Lark."""

import os
from pathlib import Path
from typing import List, Optional, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, XORGateway, 
    Flow, Element, ASTNode
)


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
        return StartEvent(name=name, id=properties['id'])
    
    @v_args(inline=True)
    def end_element(self, name: str, properties: dict) -> EndEvent:
        """Create an EndEvent node."""
        return EndEvent(name=name, id=properties['id'])
    
    @v_args(inline=True)
    def script_call(self, name: str, properties: dict) -> ScriptCall:
        """Create a ScriptCall node."""
        return ScriptCall(
            name=name,
            id=properties['id'],
            script=properties['script'],
            input_vars=properties.get('input_vars', []),
            output_vars=properties.get('output_vars', [])
        )
    
    @v_args(inline=True)
    def xor_gateway(self, name: str, properties: dict) -> XORGateway:
        """Create an XORGateway node."""
        return XORGateway(
            name=name,
            id=properties['id'],
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
    def input_vars(self, vars_list: List[str]) -> dict:
        """Extract input variables."""
        return {'input_vars': vars_list}
    
    @v_args(inline=True)
    def output_vars(self, vars_list: List[str]) -> dict:
        """Extract output variables."""
        return {'output_vars': vars_list}
    
    @v_args(inline=True)
    def gateway_condition(self, condition: str) -> dict:
        """Extract gateway condition."""
        return {'condition': condition}
    
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
    def flow_condition(self, condition: str) -> str:
        """Extract flow condition."""
        return condition
    
    def string_array(self, items) -> List[str]:
        """Create string array."""
        return [item for item in items if isinstance(item, str)]


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
