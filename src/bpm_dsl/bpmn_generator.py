"""BPMN XML generator for Zeebe compatibility."""

import uuid
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree, register_namespace
from xml.dom import minidom

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, ServiceTask, ProcessEntity, XORGateway, 
    Flow, Element as BPMElement
)
from .layout_engine import BPMNLayoutEngine, LayoutConfig, Bounds


class BPMNGenerator:
    """Generates BPMN XML from BPM DSL AST."""
    
    def __init__(self, layout_config: LayoutConfig = None):
        """Initialize the BPMN generator."""
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI',
            'zeebe': 'http://camunda.org/schema/zeebe/1.0',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        
        # Initialize layout engine
        self.layout_engine = BPMNLayoutEngine(layout_config)
        
        # Track gateway elements for default flow assignment
        self._gateway_elements = {}
        
        # Don't register namespaces - handle them manually to avoid duplicates
    
    def _ensure_feel_expression(self, expression: str) -> str:
        """Ensure expression starts with '=' for FEEL compatibility and convert operators."""
        if not expression:
            return expression
            
        # Don't modify if already a FEEL expression
        if expression.startswith('='):
            return expression
            
        # Convert JavaScript-style operators to FEEL operators
        feel_expression = expression
        # Convert == to = for FEEL equality
        feel_expression = feel_expression.replace(' == ', ' = ')
        # Convert != to != (this should be fine in FEEL, but let's be explicit)
        feel_expression = feel_expression.replace(' != ', ' != ')
        # Convert single quotes to double quotes for FEEL string literals
        feel_expression = feel_expression.replace("'", '"')
        
        return f'={feel_expression}'
    
    def generate(self, process: Process) -> str:
        """Generate BPMN XML from a Process AST."""
        # Clear gateway elements for fresh generation
        self._gateway_elements = {}
        
        definitions = self._create_definitions(process)
        return self._prettify_xml(definitions)
    
    def _create_definitions(self, process: Process) -> Element:
        """Create the BPMN definitions element."""
        # Create root definitions element without namespace prefix to avoid auto-prefixing
        definitions = Element("definitions")
        definitions.set("id", f"definitions_{process.id}")
        definitions.set("targetNamespace", "http://bpmn.io/schema/bpmn")
        definitions.set("exporter", "BPM DSL")
        definitions.set("exporterVersion", "1.0")
        
        # Set all namespace declarations manually
        definitions.set("xmlns", self.namespaces['bpmn'])
        for prefix, uri in self.namespaces.items():
            if prefix != 'bpmn':
                definitions.set(f"xmlns:{prefix}", uri)
        
        # Add error definitions if processEntity elements exist
        has_process_entity = any(isinstance(elem, ProcessEntity) for elem in process.elements)
        if has_process_entity:
            error_def = SubElement(definitions, "error")
            error_def.set("id", "process-entity-validation-error")
            error_def.set("name", "Process Entity Validation Error")
            error_def.set("errorCode", "PROCESS_ENTITY_VALIDATION_ERROR")
        
        # Create process element
        bpmn_process = SubElement(definitions, "process")
        bpmn_process.set("id", process.id)
        bpmn_process.set("name", process.name)
        bpmn_process.set("isExecutable", "true")
        
        # Version is handled via Zeebe deployment, not as BPMN attribute
        # if process.version:
        #     # versionTag is not part of BPMN 2.0 standard
        
        # Store process reference for flow generation
        self.layout_engine.process = process
        
        # Add process elements
        self._add_elements(bpmn_process, process.elements)
        
        # Add sequence flows
        self._add_flows(bpmn_process, process.flows)
        
        # Create BPMN diagram (basic positioning)
        self._add_diagram(definitions, process)
        
        return definitions
    
    def _add_elements(self, parent: Element, elements: List[BPMElement]) -> None:
        """Add process elements to the BPMN process."""
        for element in elements:
            if isinstance(element, StartEvent):
                self._add_start_event(parent, element)
            elif isinstance(element, EndEvent):
                self._add_end_event(parent, element)
            elif isinstance(element, ScriptCall):
                self._add_script_task(parent, element)
            elif isinstance(element, ServiceTask):
                self._add_service_task(parent, element)
            elif isinstance(element, ProcessEntity):
                self._add_process_entity(parent, element)
            elif isinstance(element, XORGateway):
                self._add_xor_gateway(parent, element)
    
    def _add_start_event(self, parent: Element, start: StartEvent) -> None:
        """Add a start event to the process."""
        start_event = SubElement(parent, "startEvent")
        start_event.set("id", start.id)
        start_event.set("name", start.name)
    
    def _add_end_event(self, parent: Element, end: EndEvent) -> None:
        """Add an end event to the process."""
        end_event = SubElement(parent, "endEvent")
        end_event.set("id", end.id)
        end_event.set("name", end.name)
    
    def _add_script_task(self, parent: Element, script: ScriptCall) -> None:
        """Add a script task to the process."""
        script_task = SubElement(parent, "scriptTask")
        script_task.set("id", script.id)
        script_task.set("name", script.name)
        
        # Add Zeebe extension elements
        extension_elements = SubElement(script_task, "extensionElements")
        
        # Add Zeebe script definition
        zeebe_script = SubElement(extension_elements, "zeebe:script")
        # The XML library will automatically escape quotes in attributes
        zeebe_script.set("expression", self._ensure_feel_expression(script.script))
        zeebe_script.set("resultVariable", script.result_variable)
        
        # Add input/output variable mappings if specified
        if script.input_mappings or script.output_mappings:
            io_mapping = SubElement(extension_elements, "zeebe:ioMapping")
            
            # Input mappings: map process variables to local script variables
            for mapping in script.input_mappings:
                input_param = SubElement(io_mapping, "zeebe:input")
                input_param.set("source", self._ensure_feel_expression(mapping.source))  # Process variable (needs FEEL expression)
                input_param.set("target", mapping.target)  # Local variable
            
            # Output mappings: map local script variables back to process variables
            for mapping in script.output_mappings:
                output_param = SubElement(io_mapping, "zeebe:output")
                output_param.set("source", self._ensure_feel_expression(mapping.source))  # Local variable (needs FEEL expression)
                output_param.set("target", mapping.target)  # Process variable
    
    def _add_service_task(self, parent: Element, service: ServiceTask) -> None:
        """Add a service task to the process."""
        service_task = SubElement(parent, "serviceTask")
        service_task.set("id", service.id)
        service_task.set("name", service.name)
        
        # Add Zeebe extension elements
        extension_elements = SubElement(service_task, "extensionElements")
        
        # Add Zeebe task definition
        zeebe_task_def = SubElement(extension_elements, "zeebe:taskDefinition")
        zeebe_task_def.set("type", service.task_type)
        if service.retries is not None:
            zeebe_task_def.set("retries", str(service.retries))
        
        # Add task headers if specified
        if service.headers:
            zeebe_headers = SubElement(extension_elements, "zeebe:taskHeaders")
            for header in service.headers:
                zeebe_header = SubElement(zeebe_headers, "zeebe:header")
                zeebe_header.set("key", header.key)
                zeebe_header.set("value", header.value)
        
        # Add input/output variable mappings if specified
        if service.input_mappings or service.output_mappings:
            io_mapping = SubElement(extension_elements, "zeebe:ioMapping")
            
            # Input mappings: map process variables to local task variables
            for mapping in service.input_mappings:
                input_param = SubElement(io_mapping, "zeebe:input")
                input_param.set("source", self._ensure_feel_expression(mapping.source))  # Process variable (needs FEEL expression)
                input_param.set("target", mapping.target)  # Local variable
            
            # Output mappings: map local task variables back to process variables
            for mapping in service.output_mappings:
                output_param = SubElement(io_mapping, "zeebe:output")
                output_param.set("source", self._ensure_feel_expression(mapping.source))  # Local variable (needs FEEL expression)
                output_param.set("target", mapping.target)  # Process variable
    
    def _add_process_entity(self, parent: Element, process_entity: ProcessEntity) -> None:
        """Add a process entity as a service task to the process.
        
        ProcessEntity translates to a serviceTask in Camunda with:
        - A default job worker type for entity processing
        - A special header containing the OpenAPI model path
        - An automatic XOR gateway for validation error checking
        - An error end event for validation failures
        """
        # 1. Add the main service task for process entity validation
        service_task = SubElement(parent, "serviceTask")
        service_task.set("id", process_entity.id)
        service_task.set("name", process_entity.name)
        
        # Add Zeebe extension elements
        extension_elements = SubElement(service_task, "extensionElements")
        
        # Add Zeebe task definition with default task type
        zeebe_task_def = SubElement(extension_elements, "zeebe:taskDefinition")
        zeebe_task_def.set("type", "process-entity-validator")
        # ProcessEntity uses default retries (3)
        zeebe_task_def.set("retries", "3")
        
        # Add task headers with the entity model path
        zeebe_headers = SubElement(extension_elements, "zeebe:taskHeaders")
        
        # Add the entityModel header
        entity_model_header = SubElement(zeebe_headers, "zeebe:header")
        entity_model_header.set("key", "entityModel")
        entity_model_header.set("value", process_entity.entity_model)
        
        # Add the entityName header
        entity_name_header = SubElement(zeebe_headers, "zeebe:header")
        entity_name_header.set("key", "entityName")
        entity_name_header.set("value", process_entity.entity_name)
        
        # Add I/O mapping for automatic input/output variables
        io_mapping = SubElement(extension_elements, "zeebe:ioMapping")
        
        # Input: processEntity variable (data to validate)
        input_process_entity = SubElement(io_mapping, "zeebe:input")
        input_process_entity.set("source", "=processEntity")
        input_process_entity.set("target", "processEntity")
        
        # Output: entityValidationResult (validation results)
        output_result = SubElement(io_mapping, "zeebe:output")
        output_result.set("source", "=validationResult")
        output_result.set("target", "entityValidationResult")
        
        # 2. Add XOR gateway for validation error checking
        validation_gateway_id = f"{process_entity.id}-validation-gateway"
        xor_gateway = SubElement(parent, "exclusiveGateway")
        xor_gateway.set("id", validation_gateway_id)
        xor_gateway.set("name", "Validation Check")
        
        # Store reference for setting default flow later
        self._gateway_elements[validation_gateway_id] = xor_gateway
        
        # 3. Add error end event for validation failures
        error_end_id = f"{process_entity.id}-validation-error"
        error_end_event = SubElement(parent, "endEvent")
        error_end_event.set("id", error_end_id)
        error_end_event.set("name", "Validation Error")
        
        # Add error event definition
        error_event_def = SubElement(error_end_event, "errorEventDefinition")
        error_event_def.set("id", f"{error_end_id}-def")
        error_event_def.set("errorRef", "process-entity-validation-error")
        
        # Store the generated element IDs for flow generation
        if not hasattr(process_entity, '_generated_elements'):
            process_entity._generated_elements = {}
        process_entity._generated_elements.update({
            'validation_gateway_id': validation_gateway_id,
            'error_end_id': error_end_id
        })
    
    def _add_xor_gateway(self, parent: Element, gateway: XORGateway) -> None:
        """Add an exclusive gateway to the process."""
        xor_gateway = SubElement(parent, "exclusiveGateway")
        xor_gateway.set("id", gateway.id)
        xor_gateway.set("name", gateway.name)
        
        # Store reference for setting default flow later
        self._gateway_elements[gateway.id] = xor_gateway
    
    def _add_flows(self, parent: Element, flows: List[Flow]) -> None:
        """Add sequence flows to the process, handling processEntity validation flows automatically."""
        # First, collect all processEntity elements and their generated elements
        process_entities = {}
        for element in self.layout_engine.process.elements if hasattr(self.layout_engine, 'process') else []:
            if isinstance(element, ProcessEntity) and hasattr(element, '_generated_elements'):
                process_entities[element.id] = element._generated_elements
        
        for flow in flows:
            # Check if this flow targets a processEntity - if so, we need to handle validation flows
            target_is_process_entity = flow.target_id in process_entities
            source_is_process_entity = flow.source_id in process_entities
            
            if target_is_process_entity:
                # Original flow goes to processEntity as normal
                self._add_single_flow(parent, flow)
                
                # Add automatic flows for processEntity validation
                generated = process_entities[flow.target_id]
                validation_gateway_id = generated['validation_gateway_id']
                error_end_id = generated['error_end_id']
                
                # Flow from processEntity to validation gateway
                validation_flow_id = f"flow_{flow.target_id}_to_{validation_gateway_id}"
                validation_flow = SubElement(parent, "sequenceFlow")
                validation_flow.set("id", validation_flow_id)
                validation_flow.set("sourceRef", flow.target_id)
                validation_flow.set("targetRef", validation_gateway_id)
                
                # Flow from validation gateway to error end (validation failed)
                error_flow_id = f"flow_{validation_gateway_id}_to_{error_end_id}"
                error_flow = SubElement(parent, "sequenceFlow")
                error_flow.set("id", error_flow_id)
                error_flow.set("sourceRef", validation_gateway_id)
                error_flow.set("targetRef", error_end_id)
                
                # Add condition for validation failure
                error_condition_expr = SubElement(error_flow, "conditionExpression")
                error_condition_expr.set("xsi:type", "tFormalExpression")
                error_condition_expr.text = "=entityValidationResult.isValid = false"
                
            elif source_is_process_entity:
                # This flow originates from a processEntity - redirect it to come from the validation gateway instead
                generated = process_entities[flow.source_id]
                validation_gateway_id = generated['validation_gateway_id']
                
                # Create flow from validation gateway to the original target (validation passed)
                success_flow_id = f"flow_{validation_gateway_id}_to_{flow.target_id}"
                success_flow = SubElement(parent, "sequenceFlow")
                success_flow.set("id", success_flow_id)
                success_flow.set("sourceRef", validation_gateway_id)
                success_flow.set("targetRef", flow.target_id)
                
                # This is the default flow (validation passed)
                if validation_gateway_id in self._gateway_elements:
                    gateway_element = self._gateway_elements[validation_gateway_id]
                    gateway_element.set("default", success_flow_id)
                
                # Handle original flow conditions if any
                if flow.condition:
                    condition_expr = SubElement(success_flow, "conditionExpression")
                    condition_expr.set("xsi:type", "tFormalExpression")
                    condition_expr.text = f"=entityValidationResult.isValid = true and ({self._ensure_feel_expression(flow.condition)[1:]})"
                
            else:
                # Regular flow - no processEntity involved
                self._add_single_flow(parent, flow)
    
    def _add_single_flow(self, parent: Element, flow: Flow) -> None:
        """Add a single sequence flow to the process."""
        sequence_flow = SubElement(parent, "sequenceFlow")
        flow_id = f"flow_{flow.source_id}_to_{flow.target_id}"
        sequence_flow.set("id", flow_id)
        sequence_flow.set("sourceRef", flow.source_id)
        sequence_flow.set("targetRef", flow.target_id)
        
        # Handle default flows
        if flow.is_default:
            # Set the default attribute on the source gateway
            if flow.source_id in self._gateway_elements:
                gateway_element = self._gateway_elements[flow.source_id]
                gateway_element.set("default", flow_id)
            # Default flows should not have conditions
        elif flow.condition:
            # Add condition expression for non-default flows
            condition_expr = SubElement(sequence_flow, "conditionExpression")
            condition_expr.set("xsi:type", "tFormalExpression")
            condition_expr.text = self._ensure_feel_expression(flow.condition)
    
    def _add_diagram(self, definitions: Element, process: Process) -> None:
        """Add advanced BPMN diagram information with professional layout."""
        diagram = SubElement(definitions, "bpmndi:BPMNDiagram")
        diagram.set("id", f"diagram_{process.id}")
        
        plane = SubElement(diagram, "bpmndi:BPMNPlane")
        plane.set("id", f"plane_{process.id}")
        plane.set("bpmnElement", process.id)
        
        # Calculate advanced layout using the layout engine
        element_positions, edge_routes = self.layout_engine.calculate_layout(process)
        
        # Add shapes for original elements with calculated positions
        for element in process.elements:
            if element.id not in element_positions:
                continue
                
            shape = SubElement(plane, "bpmndi:BPMNShape")
            shape.set("id", f"shape_{element.id}")
            shape.set("bpmnElement", element.id)
            
            pos = element_positions[element.id]
            bounds = SubElement(shape, "dc:Bounds")
            bounds.set("x", str(int(pos.x)))
            bounds.set("y", str(int(pos.y)))
            bounds.set("width", str(int(pos.width)))
            bounds.set("height", str(int(pos.height)))
        
        # Add shapes for generated processEntity validation elements
        for element in process.elements:
            if isinstance(element, ProcessEntity) and hasattr(element, '_generated_elements'):
                generated = element._generated_elements
                original_pos = element_positions.get(element.id)
                
                if original_pos:
                    # Position validation gateway to the right of the processEntity
                    gateway_x = original_pos.x + original_pos.width + 80
                    gateway_y = original_pos.y + (original_pos.height - 50) / 2  # Center vertically
                    
                    gateway_shape = SubElement(plane, "bpmndi:BPMNShape")
                    gateway_shape.set("id", f"shape_{generated['validation_gateway_id']}")
                    gateway_shape.set("bpmnElement", generated['validation_gateway_id'])
                    
                    gateway_bounds = SubElement(gateway_shape, "dc:Bounds")
                    gateway_bounds.set("x", str(int(gateway_x)))
                    gateway_bounds.set("y", str(int(gateway_y)))
                    gateway_bounds.set("width", "50")
                    gateway_bounds.set("height", "50")
                    
                    # Position error end event below the gateway
                    error_x = gateway_x + (50 - 36) / 2  # Center horizontally with gateway
                    error_y = gateway_y + 50 + 60  # Below gateway with spacing
                    
                    error_shape = SubElement(plane, "bpmndi:BPMNShape")
                    error_shape.set("id", f"shape_{generated['error_end_id']}")
                    error_shape.set("bpmnElement", generated['error_end_id'])
                    
                    error_bounds = SubElement(error_shape, "dc:Bounds")
                    error_bounds.set("x", str(int(error_x)))
                    error_bounds.set("y", str(int(error_y)))
                    error_bounds.set("width", "36")
                    error_bounds.set("height", "36")
        
        # Collect processEntity IDs to skip their outgoing flow diagrams
        process_entity_ids = set()
        for element in process.elements:
            if isinstance(element, ProcessEntity):
                process_entity_ids.add(element.id)
        
        # Add edges with calculated routes for original flows
        for flow in process.flows:
            # Skip diagram generation for flows originating from processEntity
            # (these are handled by _add_generated_flow_diagrams)
            if flow.source_id in process_entity_ids:
                continue
            
            flow_id = f"flow_{flow.source_id}_to_{flow.target_id}"
            
            if flow_id not in edge_routes:
                continue
                
            edge = SubElement(plane, "bpmndi:BPMNEdge")
            edge.set("id", f"edge_{flow_id}")
            edge.set("bpmnElement", flow_id)
            
            # Add waypoints from calculated route
            route = edge_routes[flow_id]
            for waypoint in route.waypoints:
                wp = SubElement(edge, "di:waypoint")
                wp.set("x", str(int(waypoint.x)))
                wp.set("y", str(int(waypoint.y)))
        
        # Add edges for generated processEntity validation flows
        self._add_generated_flow_diagrams(plane, process, element_positions)
    
    def _add_generated_flow_diagrams(self, plane: Element, process: Process, element_positions: Dict[str, Bounds]) -> None:
        """Add diagram information for generated processEntity validation flows."""
        for element in process.elements:
            if isinstance(element, ProcessEntity) and hasattr(element, '_generated_elements'):
                generated = element._generated_elements
                original_pos = element_positions.get(element.id)
                
                if not original_pos:
                    continue
                
                # Calculate positions
                gateway_x = original_pos.x + original_pos.width + 80
                gateway_y = original_pos.y + (original_pos.height - 50) / 2
                error_x = gateway_x + (50 - 36) / 2
                error_y = gateway_y + 50 + 60
                
                # Flow from processEntity to validation gateway
                validation_flow_id = f"flow_{element.id}_to_{generated['validation_gateway_id']}"
                validation_edge = SubElement(plane, "bpmndi:BPMNEdge")
                validation_edge.set("id", f"edge_{validation_flow_id}")
                validation_edge.set("bpmnElement", validation_flow_id)
                
                # Waypoints for processEntity to gateway
                wp1 = SubElement(validation_edge, "di:waypoint")
                wp1.set("x", str(int(original_pos.x + original_pos.width)))
                wp1.set("y", str(int(original_pos.y + original_pos.height / 2)))
                
                wp2 = SubElement(validation_edge, "di:waypoint")
                wp2.set("x", str(int(gateway_x)))
                wp2.set("y", str(int(gateway_y + 25)))
                
                # Flow from validation gateway to error end
                error_flow_id = f"flow_{generated['validation_gateway_id']}_to_{generated['error_end_id']}"
                error_edge = SubElement(plane, "bpmndi:BPMNEdge")
                error_edge.set("id", f"edge_{error_flow_id}")
                error_edge.set("bpmnElement", error_flow_id)
                
                # Waypoints for gateway to error end
                wp3 = SubElement(error_edge, "di:waypoint")
                wp3.set("x", str(int(gateway_x + 25)))
                wp3.set("y", str(int(gateway_y + 50)))
                
                wp4 = SubElement(error_edge, "di:waypoint")
                wp4.set("x", str(int(error_x + 18)))
                wp4.set("y", str(int(error_y)))
                
                # Find flows that originate from this processEntity to add success flow diagrams
                for flow in process.flows:
                    if flow.source_id == element.id:
                        # This is a flow from processEntity - it should now come from the validation gateway
                        success_flow_id = f"flow_{generated['validation_gateway_id']}_to_{flow.target_id}"
                        success_edge = SubElement(plane, "bpmndi:BPMNEdge")
                        success_edge.set("id", f"edge_{success_flow_id}")
                        success_edge.set("bpmnElement", success_flow_id)
                        
                        # Find target position
                        target_pos = element_positions.get(flow.target_id)
                        if target_pos:
                            # Waypoints for gateway to success target
                            wp5 = SubElement(success_edge, "di:waypoint")
                            wp5.set("x", str(int(gateway_x + 50)))
                            wp5.set("y", str(int(gateway_y + 25)))
                            
                            wp6 = SubElement(success_edge, "di:waypoint")
                            wp6.set("x", str(int(target_pos.x)))
                            wp6.set("y", str(int(target_pos.y + target_pos.height / 2)))
    
    def _prettify_xml(self, element: Element) -> str:
        """Convert XML element to pretty-printed string."""
        rough_string = tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ").replace('<?xml version="1.0" ?>\n', '')
        
        # Don't convert &quot; back to quotes - they need to stay escaped in XML attributes
        # The FEEL engine will handle the escaped quotes correctly
        
        return pretty_xml
    
    def save_to_file(self, process: Process, file_path: str) -> None:
        """Generate BPMN XML and save to file."""
        xml_content = self.generate(process)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_content)


# Convenience function
def generate_bpmn(process: Process, output_file: Optional[str] = None) -> str:
    """Generate BPMN XML from a Process AST."""
    generator = BPMNGenerator()
    xml_content = generator.generate(process)
    
    if output_file:
        generator.save_to_file(process, output_file)
    
    return xml_content
