"""BPMN XML generator for Zeebe compatibility."""

import uuid
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree, register_namespace
from xml.dom import minidom

from .ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, XORGateway, 
    Flow, Element as BPMElement
)


class BPMNGenerator:
    """Generates BPMN XML from BPM DSL AST."""
    
    def __init__(self):
        """Initialize the BPMN generator."""
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI',
            'zeebe': 'http://camunda.org/schema/zeebe/1.0'
        }
        
        # Don't register namespaces - handle them manually to avoid duplicates
    
    def generate(self, process: Process) -> str:
        """Generate BPMN XML from a Process AST."""
        definitions = self._create_definitions(process)
        return self._prettify_xml(definitions)
    
    def _create_definitions(self, process: Process) -> Element:
        """Create the BPMN definitions element."""
        # Create root definitions element
        definitions = Element(f"{{{self.namespaces['bpmn']}}}definitions")
        definitions.set("id", f"definitions_{process.id}")
        definitions.set("targetNamespace", "http://bpmn.io/schema/bpmn")
        definitions.set("exporter", "BPM DSL")
        definitions.set("exporterVersion", "1.0")
        
        # Set default namespace and add other namespace declarations
        definitions.set("xmlns", self.namespaces['bpmn'])
        for prefix, uri in self.namespaces.items():
            if prefix != 'bpmn':
                definitions.set(f"xmlns:{prefix}", uri)
        
        # Create process element
        bpmn_process = SubElement(definitions, f"{{{self.namespaces['bpmn']}}}process")
        bpmn_process.set("id", process.id)
        bpmn_process.set("name", process.name)
        bpmn_process.set("isExecutable", "true")
        
        if process.version:
            bpmn_process.set("versionTag", process.version)
        
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
        start_event = SubElement(parent, f"{{{self.namespaces['bpmn']}}}startEvent")
        start_event.set("id", start.id)
        start_event.set("name", start.name)
    
    def _add_end_event(self, parent: Element, end: EndEvent) -> None:
        """Add an end event to the process."""
        end_event = SubElement(parent, f"{{{self.namespaces['bpmn']}}}endEvent")
        end_event.set("id", end.id)
        end_event.set("name", end.name)
    
    def _add_script_task(self, parent: Element, script: ScriptCall) -> None:
        """Add a script task to the process."""
        script_task = SubElement(parent, f"{{{self.namespaces['bpmn']}}}scriptTask")
        script_task.set("id", script.id)
        script_task.set("name", script.name)
        
        # Add Zeebe extension elements
        extension_elements = SubElement(script_task, f"{{{self.namespaces['bpmn']}}}extensionElements")
        
        # Add Zeebe script definition
        zeebe_script = SubElement(extension_elements, f"{{{self.namespaces['zeebe']}}}script")
        zeebe_script.set("expression", script.script)
        zeebe_script.set("resultVariable", "result")
        
        # Add input/output variable mappings if specified
        if script.input_vars or script.output_vars:
            io_mapping = SubElement(extension_elements, f"{{{self.namespaces['zeebe']}}}ioMapping")
            
            # Input mappings
            for var in script.input_vars:
                input_param = SubElement(io_mapping, f"{{{self.namespaces['zeebe']}}}input")
                input_param.set("source", var)
                input_param.set("target", var)
            
            # Output mappings  
            for var in script.output_vars:
                output_param = SubElement(io_mapping, f"{{{self.namespaces['zeebe']}}}output")
                output_param.set("source", var)
                output_param.set("target", var)
    
    def _add_xor_gateway(self, parent: Element, gateway: XORGateway) -> None:
        """Add an exclusive gateway to the process."""
        xor_gateway = SubElement(parent, f"{{{self.namespaces['bpmn']}}}exclusiveGateway")
        xor_gateway.set("id", gateway.id)
        xor_gateway.set("name", gateway.name)
        
        # Set default flow if condition is specified
        if gateway.condition:
            xor_gateway.set("default", f"{gateway.id}_default_flow")
    
    def _add_flows(self, parent: Element, flows: List[Flow]) -> None:
        """Add sequence flows to the process."""
        for flow in flows:
            sequence_flow = SubElement(parent, f"{{{self.namespaces['bpmn']}}}sequenceFlow")
            flow_id = f"flow_{flow.source_id}_to_{flow.target_id}"
            sequence_flow.set("id", flow_id)
            sequence_flow.set("sourceRef", flow.source_id)
            sequence_flow.set("targetRef", flow.target_id)
            
            # Add condition expression if specified
            if flow.condition:
                condition_expr = SubElement(sequence_flow, f"{{{self.namespaces['bpmn']}}}conditionExpression")
                condition_expr.set(f"{{{self.namespaces['bpmn']}}}type", "tFormalExpression")
                condition_expr.text = flow.condition
    
    def _add_diagram(self, definitions: Element, process: Process) -> None:
        """Add basic BPMN diagram information for visualization."""
        diagram = SubElement(definitions, f"{{{self.namespaces['bpmndi']}}}BPMNDiagram")
        diagram.set("id", f"diagram_{process.id}")
        
        plane = SubElement(diagram, f"{{{self.namespaces['bpmndi']}}}BPMNPlane")
        plane.set("id", f"plane_{process.id}")
        plane.set("bpmnElement", process.id)
        
        # Add basic shapes for elements (simple horizontal layout)
        x_pos = 100
        y_pos = 100
        element_width = 100
        element_height = 80
        spacing = 150
        
        for element in process.elements:
            shape = SubElement(plane, f"{{{self.namespaces['bpmndi']}}}BPMNShape")
            shape.set("id", f"shape_{element.id}")
            shape.set("bpmnElement", element.id)
            
            bounds = SubElement(shape, f"{{{self.namespaces['dc']}}}Bounds")
            bounds.set("x", str(x_pos))
            bounds.set("y", str(y_pos))
            bounds.set("width", str(element_width))
            bounds.set("height", str(element_height))
            
            x_pos += spacing
        
        # Add basic edges for flows
        for flow in process.flows:
            edge = SubElement(plane, f"{{{self.namespaces['bpmndi']}}}BPMNEdge")
            flow_id = f"flow_{flow.source_id}_to_{flow.target_id}"
            edge.set("id", f"edge_{flow_id}")
            edge.set("bpmnElement", flow_id)
            
            # Add waypoints (simplified)
            waypoint1 = SubElement(edge, f"{{{self.namespaces['di']}}}waypoint")
            waypoint1.set("x", "200")
            waypoint1.set("y", "140")
            
            waypoint2 = SubElement(edge, f"{{{self.namespaces['di']}}}waypoint")
            waypoint2.set("x", "250")
            waypoint2.set("y", "140")
    
    def _prettify_xml(self, element: Element) -> str:
        """Convert XML element to pretty-printed string."""
        rough_string = tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ").replace('<?xml version="1.0" ?>\n', '')
    
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
