"""Process validation for BPM DSL."""

import re
from dataclasses import dataclass
from typing import List, Set, Dict
from collections import defaultdict

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, ServiceTask, ProcessEntity,
    Gateway, Flow, TimerEvent, TimerDefinition,
    BoundaryEvent, BoundaryTimerEvent, BoundaryErrorEvent,
    BoundaryMessageEvent, ReceiveMessageEvent,
    Subprocess, CallActivity,
)


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

        # Timer, message, and boundary event validation
        errors.extend(self._validate_timer_events(process))
        errors.extend(self._validate_message_start_events(process))
        errors.extend(self._validate_boundary_events(process))

        # Composition validation (subprocess, callActivity, multi-instance)
        errors.extend(self._validate_composition(process))

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
            elif isinstance(element, ServiceTask):
                errors.extend(self._validate_service_task(element))
            elif isinstance(element, ProcessEntity):
                errors.extend(self._validate_process_entity(element))
            elif isinstance(element, ReceiveMessageEvent):
                errors.extend(self._validate_receive_message(element))
            elif isinstance(element, Gateway):
                errors.extend(self._validate_gateway(element))
            elif isinstance(element, CallActivity):
                errors.extend(self._validate_call_activity(element))
            # Subprocess and TimerEvent validated separately

        # Check for required start and end events
        if not start_events:
            errors.append("Process must have at least one start event")
        
        if not end_events:
            errors.append("Process must have at least one end event")
        
        # Check for required processEntity - must have EXACTLY one in any flow
        process_entities = [e for e in process.elements if isinstance(e, ProcessEntity)]
        if len(process_entities) == 0:
            errors.append("Process must contain exactly one processEntity element")
        elif len(process_entities) > 1:
            entity_ids = [e.id for e in process_entities]
            errors.append(f"Process must contain exactly one processEntity element, found {len(process_entities)}: {', '.join(entity_ids)}")
        
        return errors
    
    def _validate_script_call(self, script: ScriptCall) -> List[str]:
        """Validate script call element."""
        errors = []
        
        if not script.script or not script.script.strip():
            errors.append(f"Script call {script.id} must have a non-empty script")
        
        # Validate variable mappings
        for mapping in script.input_mappings or []:
            if not self._is_valid_variable_name(mapping.source):
                errors.append(f"Invalid input mapping source variable name '{mapping.source}' in script call {script.id}")
            if not self._is_valid_variable_name(mapping.target):
                errors.append(f"Invalid input mapping target variable name '{mapping.target}' in script call {script.id}")
        
        for mapping in script.output_mappings or []:
            if not self._is_valid_variable_name(mapping.source):
                errors.append(f"Invalid output mapping source variable name '{mapping.source}' in script call {script.id}")
            if not self._is_valid_variable_name(mapping.target):
                errors.append(f"Invalid output mapping target variable name '{mapping.target}' in script call {script.id}")
        
        return errors
    
    def _validate_service_task(self, service: ServiceTask) -> List[str]:
        """Validate service task element."""
        errors = []
        
        if not service.task_type or not service.task_type.strip():
            errors.append(f"Service task {service.id} must have a non-empty type")
        
        # Validate variable mappings
        for mapping in service.input_mappings or []:
            if not self._is_valid_variable_name(mapping.source):
                errors.append(f"Invalid input mapping source variable name '{mapping.source}' in service task {service.id}")
            if not self._is_valid_variable_name(mapping.target):
                errors.append(f"Invalid input mapping target variable name '{mapping.target}' in service task {service.id}")
        
        for mapping in service.output_mappings or []:
            if not self._is_valid_variable_name(mapping.source):
                errors.append(f"Invalid output mapping source variable name '{mapping.source}' in service task {service.id}")
            if not self._is_valid_variable_name(mapping.target):
                errors.append(f"Invalid output mapping target variable name '{mapping.target}' in service task {service.id}")
        
        return errors
    
    def _validate_process_entity(self, entity: ProcessEntity) -> List[str]:
        """Validate process entity element.
        
        Note: entityModel path is automatically inferred from the process's OpenAPI file.
        Only entityName needs validation.
        """
        errors = []
        
        if not entity.entity_name or not entity.entity_name.strip():
            errors.append(f"Process entity {entity.id} must have a non-empty entityName")
        
        return errors
    
    def _validate_receive_message(self, event: ReceiveMessageEvent) -> List[str]:
        """Validate receiveMessage intermediate catch event."""
        errors = []

        if not event.message or not event.message.strip():
            errors.append(
                f"Receive message event '{event.id}' must have a non-empty message name"
            )

        if not event.correlation_key or not event.correlation_key.strip():
            errors.append(
                f"Receive message event '{event.id}' must have a non-empty correlationKey"
            )

        return errors

    def _validate_gateway(self, gateway: Gateway) -> List[str]:
        """Validate gateway element."""
        errors = []

        valid_types = {"xor", "parallel"}
        if gateway.gateway_type not in valid_types:
            errors.append(
                f"Gateway '{gateway.id}' has invalid type '{gateway.gateway_type}'. "
                f"Valid types: {', '.join(sorted(valid_types))}"
            )

        return errors
    
    def _validate_timer_events(self, process: Process) -> List[str]:
        """Validate timer events and timer start events."""
        errors = []

        for element in process.elements:
            if isinstance(element, TimerEvent):
                td = element.timer
                if td is None or not (td.duration or td.date or td.cycle):
                    errors.append(
                        f"Timer event '{element.id}' must specify at least one of "
                        f"duration, date, or cycle"
                    )
                else:
                    errors.extend(self._validate_timer_definition(td, element.id))

            elif isinstance(element, StartEvent) and element.timer is not None:
                td = element.timer
                if not (td.duration or td.date or td.cycle):
                    errors.append(
                        f"Timer start event '{element.id}' must specify at least one of "
                        f"duration, date, or cycle"
                    )
                else:
                    errors.extend(self._validate_timer_definition(td, element.id))

        return errors

    def _validate_message_start_events(self, process: Process) -> List[str]:
        """Validate message start events have a non-empty message name."""
        errors = []

        for element in process.elements:
            if isinstance(element, StartEvent) and element.message is not None:
                if not element.message or not element.message.strip():
                    errors.append(
                        f"Message start event '{element.id}' must have a non-empty message name"
                    )

        return errors

    def _validate_timer_definition(self, td: TimerDefinition, element_id: str) -> List[str]:
        """Validate ISO 8601 values inside a TimerDefinition."""
        errors = []

        if td.duration and not self._is_valid_iso8601_duration(td.duration):
            errors.append(
                f"Timer '{element_id}' has invalid ISO 8601 duration: {td.duration}"
            )

        if td.date and not self._is_valid_iso8601_date(td.date):
            errors.append(
                f"Timer '{element_id}' has invalid ISO 8601 date: {td.date}"
            )

        if td.cycle and not self._is_valid_iso8601_cycle(td.cycle):
            errors.append(
                f"Timer '{element_id}' has invalid ISO 8601 cycle: {td.cycle}"
            )

        return errors

    def _validate_boundary_events(self, process: Process) -> List[str]:
        """Validate boundary events across all service tasks."""
        errors = []
        # Collect all top-level element IDs for uniqueness check
        all_ids: Set[str] = {e.id for e in process.elements}
        boundary_ids: Set[str] = set()
        element_ids: Set[str] = {e.id for e in process.elements}

        for element in process.elements:
            if not isinstance(element, ServiceTask):
                continue

            for be in element.boundary_events or []:
                # ID uniqueness: check against top-level IDs and other boundary IDs
                if be.id in all_ids or be.id in boundary_ids:
                    errors.append(
                        f"Boundary event '{be.id}' has a duplicate ID "
                        f"(conflicts with another element or boundary event)"
                    )
                boundary_ids.add(be.id)

                # attached_to_ref must point to the parent task
                if not be.attached_to_ref:
                    errors.append(
                        f"Boundary event '{be.id}' has no attached_to_ref"
                    )
                elif be.attached_to_ref not in element_ids:
                    errors.append(
                        f"Boundary event '{be.id}' references non-existent "
                        f"parent task: {be.attached_to_ref}"
                    )

                # BoundaryTimerEvent must have a duration
                if isinstance(be, BoundaryTimerEvent):
                    if not be.duration:
                        errors.append(
                            f"Boundary timer event '{be.id}' must specify a duration"
                        )
                    elif not self._is_valid_iso8601_duration(be.duration):
                        errors.append(
                            f"Boundary timer event '{be.id}' has invalid "
                            f"ISO 8601 duration: {be.duration}"
                        )

                # BoundaryErrorEvent must have an error_code
                if isinstance(be, BoundaryErrorEvent):
                    if not be.error_code:
                        errors.append(
                            f"Boundary error event '{be.id}' must specify an errorCode"
                        )

                # BoundaryMessageEvent must have a correlationKey
                if isinstance(be, BoundaryMessageEvent):
                    if not be.correlation_key or not be.correlation_key.strip():
                        errors.append(
                            f"Boundary message event '{be.id}' must specify a correlationKey"
                        )

        return errors

    @staticmethod
    def _is_valid_iso8601_duration(value: str) -> bool:
        """Check if a string is a valid ISO 8601 duration (e.g., PT30M, P1DT2H)."""
        return bool(re.fullmatch(
            r'P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?',
            value,
        )) and value != "P" and value != "PT"

    @staticmethod
    def _is_valid_iso8601_date(value: str) -> bool:
        """Check if a string looks like a valid ISO 8601 date/datetime."""
        return bool(re.fullmatch(
            r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?',
            value,
        ))

    @staticmethod
    def _is_valid_iso8601_cycle(value: str) -> bool:
        """Check if a string is a valid ISO 8601 repeating interval (e.g., R/PT1H, R3/PT5M)."""
        return bool(re.fullmatch(
            r'R\d*/P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?',
            value,
        ))

    def _validate_call_activity(self, ca: 'CallActivity') -> List[str]:
        """Validate callActivity element."""
        errors = []
        if not ca.process_id or not ca.process_id.strip():
            errors.append(
                f"Call activity '{ca.id}' must have a non-empty processId"
            )
        return errors

    def _validate_multi_instance(self, element: 'Element') -> List[str]:
        """Validate multi-instance (forEach) configuration on an element."""
        errors = []
        for_each = getattr(element, 'for_each', None)
        as_var = getattr(element, 'as_var', None)

        if for_each and not as_var:
            errors.append(
                f"Element '{element.id}' has forEach but is missing "
                f"the required 'as' variable"
            )
        return errors

    def _validate_subprocess_internal(self, sub: 'Subprocess', all_ids: Set[str]) -> List[str]:
        """Recursively validate subprocess internal structure."""
        errors = []

        if not sub.elements:
            errors.append(f"Subprocess '{sub.id}' must contain at least one element")
            return errors

        start_events = [e for e in sub.elements if isinstance(e, StartEvent)]
        end_events = [e for e in sub.elements if isinstance(e, EndEvent)]

        if not start_events:
            errors.append(f"Subprocess '{sub.id}' must have at least one start event")
        if not end_events:
            errors.append(f"Subprocess '{sub.id}' must have at least one end event")

        for child in sub.elements:
            # ID uniqueness across subprocess boundaries
            if child.id in all_ids:
                errors.append(
                    f"Duplicate element ID '{child.id}' "
                    f"(conflicts across subprocess boundary in '{sub.id}')"
                )
            all_ids.add(child.id)

            # Validate child element ID format
            if not self._is_valid_xml_id(child.id):
                errors.append(
                    f"Element ID '{child.id}' in subprocess '{sub.id}' "
                    f"is not a valid XML identifier"
                )

            # Validate specific child element types
            if isinstance(child, ScriptCall):
                errors.extend(self._validate_script_call(child))
            elif isinstance(child, ServiceTask):
                errors.extend(self._validate_service_task(child))
                errors.extend(self._validate_multi_instance(child))
            elif isinstance(child, CallActivity):
                errors.extend(self._validate_call_activity(child))
            elif isinstance(child, Gateway):
                errors.extend(self._validate_gateway(child))
            elif isinstance(child, ReceiveMessageEvent):
                errors.extend(self._validate_receive_message(child))
            elif isinstance(child, Subprocess):
                errors.extend(self._validate_multi_instance(child))
                errors.extend(self._validate_subprocess_internal(child, all_ids))

        # Validate internal flows reference existing child element IDs
        child_ids = {e.id for e in sub.elements}
        for flow in sub.flows or []:
            if flow.source_id not in child_ids:
                errors.append(
                    f"Flow in subprocess '{sub.id}' references "
                    f"non-existent source element: {flow.source_id}"
                )
            if flow.target_id not in child_ids:
                errors.append(
                    f"Flow in subprocess '{sub.id}' references "
                    f"non-existent target element: {flow.target_id}"
                )

        return errors

    def _validate_composition(self, process: Process) -> List[str]:
        """Validate composition elements: subprocess, callActivity, multi-instance."""
        errors = []
        # Collect all top-level element IDs for cross-boundary uniqueness
        all_ids: Set[str] = {e.id for e in process.elements}

        for element in process.elements:
            if isinstance(element, Subprocess):
                errors.extend(self._validate_multi_instance(element))
                errors.extend(self._validate_subprocess_internal(element, all_ids))
            elif isinstance(element, ServiceTask):
                errors.extend(self._validate_multi_instance(element))

        return errors

    def _validate_flows(self, process: Process) -> List[str]:
        """Validate sequence flows."""
        errors = []
        element_ids = {element.id for element in process.elements}
        element_lookup = {e.id: e for e in process.elements}

        for flow in process.flows:
            # Check if source and target elements exist
            if flow.source_id not in element_ids:
                errors.append(f"Flow references non-existent source element: {flow.source_id}")

            if flow.target_id not in element_ids:
                errors.append(f"Flow references non-existent target element: {flow.target_id}")

            # Validate condition syntax (basic check)
            if flow.condition and not self._is_valid_condition(flow.condition):
                errors.append(f"Invalid condition syntax in flow {flow.source_id} -> {flow.target_id}: {flow.condition}")

            # Parallel gateways must not have conditional flows
            source = element_lookup.get(flow.source_id)
            if (flow.condition
                    and isinstance(source, Gateway)
                    and source.gateway_type == "parallel"):
                errors.append(
                    f"Parallel gateway '{source.id}' must not have conditional flows. "
                    f"Found condition on flow to '{flow.target_id}': {flow.condition}"
                )

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
        
        # Validate processEntity positioning
        errors.extend(self._validate_process_entity_positioning(process, outgoing))
        
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
    
    def _validate_process_entity_positioning(self, process: Process, outgoing: Dict[str, List[str]]) -> List[str]:
        """Validate that the processEntity element is positioned correctly.
        
        Since there must be exactly one processEntity, it must be the first task after a start task.
        """
        errors = []
        
        # Find all ProcessEntity elements
        process_entities = [e for e in process.elements if isinstance(e, ProcessEntity)]
        if not process_entities:
            return errors  # No processEntity elements to validate (this will be caught by other validation)
        
        # Find all start events
        start_events = [e for e in process.elements if isinstance(e, StartEvent)]
        if not start_events:
            return errors  # No start events (this will be caught by other validation)
        
        # Create element lookup
        element_lookup = {e.id: e for e in process.elements}
        
        # Since there should be exactly one processEntity, validate its positioning
        for entity in process_entities:
            is_valid_position = False
            
            # Check if this processEntity is directly connected from any start event
            for start in start_events:
                if start.id in outgoing:
                    direct_targets = outgoing[start.id]
                    if entity.id in direct_targets:
                        is_valid_position = True
                        break
            
            if not is_valid_position:
                errors.append(f"ProcessEntity '{entity.id}' must be the first task after a start event")
        
        # Check that all start events lead to processEntity (since it must be the first task)
        for start in start_events:
            if start.id in outgoing:
                direct_targets = outgoing[start.id]
                for target_id in direct_targets:
                    target_element = element_lookup.get(target_id)
                    if target_element and not isinstance(target_element, (ProcessEntity, EndEvent)):
                        # There's a non-processEntity, non-EndEvent task directly after start
                        errors.append(f"ProcessEntity must be the first task after start events. Found '{target_element.__class__.__name__}' '{target_id}' directly after start event '{start.id}'")
        
        return errors
    
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
