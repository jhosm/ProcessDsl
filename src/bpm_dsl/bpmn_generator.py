"""BPMN XML generator for Zeebe compatibility."""

import uuid
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree, register_namespace
from xml.dom import minidom

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, XORGateway, 
    Flow, Element as BPMElement
)
from .layout_engine import BPMNLayoutEngine, LayoutConfig


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
        
        # Create process element
        bpmn_process = SubElement(definitions, "process")
        bpmn_process.set("id", process.id)
        bpmn_process.set("name", process.name)
        bpmn_process.set("isExecutable", "true")
        
        # Version is handled via Zeebe deployment, not as BPMN attribute
        # if process.version:
        #     # versionTag is not part of BPMN 2.0 standard
        
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
    
    def _add_xor_gateway(self, parent: Element, gateway: XORGateway) -> None:
        """Add an exclusive gateway to the process."""
        xor_gateway = SubElement(parent, "exclusiveGateway")
        xor_gateway.set("id", gateway.id)
        xor_gateway.set("name", gateway.name)
        
        # Store reference for setting default flow later
        self._gateway_elements[gateway.id] = xor_gateway
    
    def _add_flows(self, parent: Element, flows: List[Flow]) -> None:
        """Add sequence flows to the process."""
        for flow in flows:
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
        
        # Add shapes for elements with calculated positions
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
        
        # Add edges with calculated routes
        for flow in process.flows:
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
