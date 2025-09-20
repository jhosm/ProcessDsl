"""Tests for the BPMN generator."""

import pytest
from pathlib import Path
import sys
from xml.etree.ElementTree import fromstring

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import parse_bpm_string
from bpm_dsl.bpmn_generator import BPMNGenerator


class TestBPMNGenerator:
    """Test cases for BPMN XML generator."""
    
    def test_simple_process_generation(self):
        """Test generating BPMN for a simple process."""
        dsl_content = '''
        process "Simple Process" {
            id: "simple-process"
            version: "1.0"
            
            start "Begin" {
                id: "start-1"
            }
            
            end "Complete" {
                id: "end-1"
            }
            
            flow {
                "start-1" -> "end-1"
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        # Parse the generated XML to verify structure
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')
        
        # Check root element
        assert root.tag.endswith('definitions')
        assert root.get('id') == 'definitions_simple-process'
        
        # Find process element
        process_elements = [elem for elem in root if elem.tag.endswith('process')]
        assert len(process_elements) == 1
        
        bpmn_process = process_elements[0]
        assert bpmn_process.get('id') == 'simple-process'
        assert bpmn_process.get('name') == 'Simple Process'
        assert bpmn_process.get('isExecutable') == 'true'
        # versionTag is not part of BPMN 2.0 standard - removed for compatibility
        # assert bpmn_process.get('versionTag') == '1.0'
        
        # Check for start event
        start_events = [elem for elem in bpmn_process if elem.tag.endswith('startEvent')]
        assert len(start_events) == 1
        assert start_events[0].get('id') == 'start-1'
        assert start_events[0].get('name') == 'Begin'
        
        # Check for end event
        end_events = [elem for elem in bpmn_process if elem.tag.endswith('endEvent')]
        assert len(end_events) == 1
        assert end_events[0].get('id') == 'end-1'
        assert end_events[0].get('name') == 'Complete'
        
        # Check for sequence flow
        flows = [elem for elem in bpmn_process if elem.tag.endswith('sequenceFlow')]
        assert len(flows) == 1
        assert flows[0].get('sourceRef') == 'start-1'
        assert flows[0].get('targetRef') == 'end-1'
    
    def test_script_task_generation(self):
        """Test generating BPMN for script tasks."""
        dsl_content = '''
        process "Script Process" {
            id: "script-process"
            
            start "Begin" {
                id: "start-1"
            }
            
            scriptCall "Process Data" {
                id: "script-1"
                script: "processData(input)"
                inputVars: ["input"]
                outputVars: ["result"]
            }
            
            end "Complete" {
                id: "end-1"
            }
            
            flow {
                "start-1" -> "script-1"
                "script-1" -> "end-1"
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')
        bpmn_process = [elem for elem in root if elem.tag.endswith('process')][0]
        
        # Check for script task
        script_tasks = [elem for elem in bpmn_process if elem.tag.endswith('scriptTask')]
        assert len(script_tasks) == 1
        
        script_task = script_tasks[0]
        assert script_task.get('id') == 'script-1'
        assert script_task.get('name') == 'Process Data'
        
        # Check for Zeebe extension elements
        extension_elements = [elem for elem in script_task if elem.tag.endswith('extensionElements')]
        assert len(extension_elements) == 1
        
        # Check for Zeebe script element
        zeebe_scripts = []
        for ext_elem in extension_elements[0]:
            if ext_elem.tag.endswith('script'):
                zeebe_scripts.append(ext_elem)
        
        assert len(zeebe_scripts) == 1
        zeebe_script = zeebe_scripts[0]
        assert zeebe_script.get('expression') == 'processData(input)'
    
    def test_xor_gateway_generation(self):
        """Test generating BPMN for XOR gateways."""
        dsl_content = '''
        process "Gateway Process" {
            id: "gateway-process"
            
            start "Begin" {
                id: "start-1"
            }
            
            xorGateway "Decision Point" {
                id: "gateway-1"
                condition: "amount > 1000"
            }
            
            end "High Amount" {
                id: "end-high"
            }
            
            end "Low Amount" {
                id: "end-low"
            }
            
            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-high" [condition: "amount > 1000"]
                "gateway-1" -> "end-low" [condition: "amount <= 1000"]
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')
        bpmn_process = [elem for elem in root if elem.tag.endswith('process')][0]
        
        # Check for exclusive gateway
        gateways = [elem for elem in bpmn_process if elem.tag.endswith('exclusiveGateway')]
        assert len(gateways) == 1
        
        gateway = gateways[0]
        assert gateway.get('id') == 'gateway-1'
        assert gateway.get('name') == 'Decision Point'
        
        # Check for conditional flows
        flows = [elem for elem in bpmn_process if elem.tag.endswith('sequenceFlow')]
        conditional_flows = []
        
        for flow in flows:
            condition_exprs = [elem for elem in flow if elem.tag.endswith('conditionExpression')]
            if condition_exprs:
                conditional_flows.append((flow, condition_exprs[0]))
        
        assert len(conditional_flows) == 2  # Two conditional flows from gateway
    
    def test_zeebe_namespaces(self):
        """Test that generated BPMN includes proper Zeebe namespaces."""
        dsl_content = '''
        process "Test Process" {
            id: "test-process"
            
            start "Begin" {
                id: "start-1"
            }
            
            end "Complete" {
                id: "end-1"
            }
            
            flow {
                "start-1" -> "end-1"
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        # Check that Zeebe namespace is included
        assert 'xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"' in xml_content
        assert 'http://www.omg.org/spec/BPMN/20100524/MODEL' in xml_content
        assert 'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"' in xml_content


if __name__ == "__main__":
    pytest.main([__file__])
