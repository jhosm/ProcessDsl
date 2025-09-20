"""Process validation for BPM DSL."""

from dataclasses import dataclass
from typing import List, Set, Dict
from collections import defaultdict

from .ast_nodes import Process, StartEvent, EndEvent, ScriptCall, XORGateway, Flow


@dataclass
class ValidationResult:
    """Result of process validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ProcessValidator:
    """Validates BPM DSL processes for correctness."""
    
    def validate(self, process: Process) -> ValidationResult:
        """Validate a process and return validation result."""
        errors = []
        warnings = []
        
        # Basic process validation
        errors.extend(self._validate_process_basic(process))
        
        # Element validation
        errors.extend(self._validate_elements(process))
        
        # Flow validation
        errors.extend(self._validate_flows(process))
        
        # Structural validation
        errors.extend(self._validate_structure(process))
        
        # Zeebe-specific validation
        errors.extend(self._validate_zeebe_compatibility(process))
        
        # Generate warnings
        warnings.extend(self._generate_warnings(process))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_process_basic(self, process: Process) -> List[str]:
        """Validate basic process properties."""
        errors = []
        
        if not process.name or not process.name.strip():
            errors.append("Process must have a non-empty name")
        
        if not process.id or not process.id.strip():
            errors.append("Process must have a non-empty ID")
        
        # Validate ID format (should be valid XML ID)
        if process.id and not self._is_valid_xml_id(process.id):
            errors.append(f"Process ID '{process.id}' is not a valid XML identifier")
        
        return errors
    
    def _validate_elements(self, process: Process) -> List[str]:
        """Validate process elements."""
        errors = []
        element_ids = set()
        start_events = []
        end_events = []
        
        for element in process.elements:
            # Check for duplicate IDs
            if element.id in element_ids:
                errors.append(f"Duplicate element ID: {element.id}")
            element_ids.add(element.id)
            
            # Validate element ID format
            if not self._is_valid_xml_id(element.id):
                errors.append(f"Element ID '{element.id}' is not a valid XML identifier")
            
            # Validate element name
            if not element.name or not element.name.strip():
                errors.append(f"Element {element.id} must have a non-empty name")
            
            # Collect start and end events
            if isinstance(element, StartEvent):
                start_events.append(element)
            elif isinstance(element, EndEvent):
                end_events.append(element)
            elif isinstance(element, ScriptCall):
                errors.extend(self._validate_script_call(element))
            elif isinstance(element, XORGateway):
                errors.extend(self._validate_xor_gateway(element))
        
        # Check for required start and end events
        if not start_events:
            errors.append("Process must have at least one start event")
        
        if not end_events:
            errors.append("Process must have at least one end event")
        
        return errors
    
    def _validate_script_call(self, script: ScriptCall) -> List[str]:
        """Validate script call element."""
        errors = []
        
        if not script.script or not script.script.strip():
            errors.append(f"Script call {script.id} must have a non-empty script")
        
        # Validate variable names
        for var in script.input_vars or []:
            if not self._is_valid_variable_name(var):
                errors.append(f"Invalid input variable name '{var}' in script call {script.id}")
        
        for var in script.output_vars or []:
            if not self._is_valid_variable_name(var):
                errors.append(f"Invalid output variable name '{var}' in script call {script.id}")
        
        return errors
    
    def _validate_xor_gateway(self, gateway: XORGateway) -> List[str]:
        """Validate XOR gateway element."""
        errors = []
        
        # XOR gateways should have conditions on outgoing flows
        # This will be validated in flow validation
        
        return errors
    
    def _validate_flows(self, process: Process) -> List[str]:
        """Validate sequence flows."""
        errors = []
        element_ids = {element.id for element in process.elements}
        
        for flow in process.flows:
            # Check if source and target elements exist
            if flow.source_id not in element_ids:
                errors.append(f"Flow references non-existent source element: {flow.source_id}")
            
            if flow.target_id not in element_ids:
                errors.append(f"Flow references non-existent target element: {flow.target_id}")
            
            # Validate condition syntax (basic check)
            if flow.condition and not self._is_valid_condition(flow.condition):
                errors.append(f"Invalid condition syntax in flow {flow.source_id} -> {flow.target_id}: {flow.condition}")
        
        return errors
    
    def _validate_structure(self, process: Process) -> List[str]:
        """Validate process structure and connectivity."""
        errors = []
        
        # Build adjacency lists
        outgoing = defaultdict(list)
        incoming = defaultdict(list)
        
        for flow in process.flows:
            outgoing[flow.source_id].append(flow.target_id)
            incoming[flow.target_id].append(flow.source_id)
        
        # Find start and end events
        start_events = [e for e in process.elements if isinstance(e, StartEvent)]
        end_events = [e for e in process.elements if isinstance(e, EndEvent)]
        
        # Check start events have no incoming flows
        for start in start_events:
            if start.id in incoming:
                errors.append(f"Start event {start.id} cannot have incoming flows")
        
        # Check end events have no outgoing flows
        for end in end_events:
            if end.id in outgoing:
                errors.append(f"End event {end.id} cannot have outgoing flows")
        
        # Check connectivity (simplified - each element should be reachable)
        if start_events:
            reachable = self._find_reachable_elements(start_events[0].id, outgoing)
            all_element_ids = {e.id for e in process.elements}
            unreachable = all_element_ids - reachable
            
            if unreachable:
                errors.append(f"Unreachable elements: {', '.join(unreachable)}")
        
        return errors
    
    def _validate_zeebe_compatibility(self, process: Process) -> List[str]:
        """Validate Zeebe-specific requirements."""
        errors = []
        
        # Check for Zeebe-specific limitations
        for element in process.elements:
            if isinstance(element, ScriptCall):
                # Zeebe requires specific script formats
                if element.script and not self._is_valid_zeebe_expression(element.script):
                    errors.append(f"Script in {element.id} may not be compatible with Zeebe: {element.script}")
        
        return errors
    
    def _generate_warnings(self, process: Process) -> List[str]:
        """Generate warnings for potential issues."""
        warnings = []
        
        # Check for unused elements
        flow_elements = set()
        for flow in process.flows:
            flow_elements.add(flow.source_id)
            flow_elements.add(flow.target_id)
        
        all_elements = {e.id for e in process.elements}
        unused_elements = all_elements - flow_elements
        
        if unused_elements:
            warnings.append(f"Elements not connected by flows: {', '.join(unused_elements)}")
        
        # Check for processes without version
        if not process.version:
            warnings.append("Process version not specified - consider adding a version for better tracking")
        
        return warnings
    
    def _find_reachable_elements(self, start_id: str, outgoing: Dict[str, List[str]]) -> Set[str]:
        """Find all elements reachable from a start element."""
        visited = set()
        stack = [start_id]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            
            visited.add(current)
            stack.extend(outgoing.get(current, []))
        
        return visited
    
    def _is_valid_xml_id(self, id_str: str) -> bool:
        """Check if string is a valid XML ID."""
        if not id_str:
            return False
        
        # XML ID must start with letter or underscore
        if not (id_str[0].isalpha() or id_str[0] == '_'):
            return False
        
        # Rest can be letters, digits, hyphens, underscores, or periods
        for char in id_str[1:]:
            if not (char.isalnum() or char in '-_.'):
                return False
        
        return True
    
    def _is_valid_variable_name(self, var_name: str) -> bool:
        """Check if string is a valid variable name."""
        if not var_name:
            return False
        
        # Variable names should be valid identifiers
        return var_name.isidentifier()
    
    def _is_valid_condition(self, condition: str) -> bool:
        """Basic validation of condition expressions."""
        if not condition or not condition.strip():
            return False
        
        # Basic syntax check - should contain some comparison or boolean logic
        # This is a simplified check - in practice, you might want to parse the expression
        return any(op in condition for op in ['==', '!=', '>', '<', '>=', '<=', '&&', '||', 'true', 'false'])
    
    def _is_valid_zeebe_expression(self, expression: str) -> bool:
        """Check if expression is valid for Zeebe."""
        if not expression:
            return False
        
        # Zeebe supports FEEL expressions and some JavaScript
        # This is a basic check - in practice, you'd want more sophisticated validation
        return len(expression.strip()) > 0
