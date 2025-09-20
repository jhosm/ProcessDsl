"""Tests for the BPM DSL parser."""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import BPMParser, parse_bpm_string
from bpm_dsl.ast_nodes import Process, StartEvent, EndEvent, ScriptCall, XORGateway, Flow


class TestBPMParser:
    """Test cases for BPM DSL parser."""
    
    def test_simple_process(self):
        """Test parsing a simple process."""
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
        
        assert isinstance(process, Process)
        assert process.name == "Simple Process"
        assert process.id == "simple-process"
        assert process.version == "1.0"
        assert len(process.elements) == 2
        assert len(process.flows) == 1
        
        # Check elements
        start_event = process.elements[0]
        assert isinstance(start_event, StartEvent)
        assert start_event.name == "Begin"
        assert start_event.id == "start-1"
        
        end_event = process.elements[1]
        assert isinstance(end_event, EndEvent)
        assert end_event.name == "Complete"
        assert end_event.id == "end-1"
        
        # Check flow
        flow = process.flows[0]
        assert isinstance(flow, Flow)
        assert flow.source_id == "start-1"
        assert flow.target_id == "end-1"
        assert flow.condition is None
    
    def test_script_call(self):
        """Test parsing script call elements."""
        dsl_content = '''
        process "Script Process" {
            id: "script-process"
            
            start "Begin" {
                id: "start-1"
            }
            
            scriptCall "Process Data" {
                id: "script-1"
                script: "processData(input)"
                inputVars: ["input", "config"]
                outputVars: ["result", "status"]
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
        
        script_call = process.elements[1]
        assert isinstance(script_call, ScriptCall)
        assert script_call.name == "Process Data"
        assert script_call.id == "script-1"
        assert script_call.script == "processData(input)"
        assert script_call.input_vars == ["input", "config"]
        assert script_call.output_vars == ["result", "status"]
    
    def test_xor_gateway(self):
        """Test parsing XOR gateway elements."""
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
            
            end "Complete" {
                id: "end-1"
            }
            
            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-1" [condition: "amount <= 1000"]
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        
        gateway = process.elements[1]
        assert isinstance(gateway, XORGateway)
        assert gateway.name == "Decision Point"
        assert gateway.id == "gateway-1"
        assert gateway.condition == "amount > 1000"
        
        # Check conditional flow
        flow = process.flows[1]
        assert flow.condition == "amount <= 1000"
    
    def test_complex_process(self):
        """Test parsing the example complex process."""
        dsl_content = '''
        process "Order Processing" {
            id: "order-process"
            version: "1.0"
            
            start "Order Received" {
                id: "start-order"
            }
            
            scriptCall "Validate Order" {
                id: "validate-order"
                script: "validateOrderData(order)"
                inputVars: ["order"]
                outputVars: ["isValid", "validationErrors"]
            }
            
            xorGateway "Order Valid?" {
                id: "order-valid-gateway"
                condition: "isValid == true"
            }
            
            scriptCall "Process Order" {
                id: "process-order"
                script: "processValidOrder(order)"
                inputVars: ["order"]
                outputVars: ["processedOrder", "orderNumber"]
            }
            
            scriptCall "Handle Invalid Order" {
                id: "handle-invalid"
                script: "handleInvalidOrder(order, validationErrors)"
                inputVars: ["order", "validationErrors"]
                outputVars: ["rejectionReason"]
            }
            
            end "Order Processed" {
                id: "end-processed"
            }
            
            end "Order Rejected" {
                id: "end-rejected"
            }
            
            flow {
                "start-order" -> "validate-order"
                "validate-order" -> "order-valid-gateway"
                "order-valid-gateway" -> "process-order" [condition: "isValid == true"]
                "order-valid-gateway" -> "handle-invalid" [condition: "isValid == false"]
                "process-order" -> "end-processed"
                "handle-invalid" -> "end-rejected"
            }
        }
        '''
        
        process = parse_bpm_string(dsl_content)
        
        assert process.name == "Order Processing"
        assert process.id == "order-process"
        assert process.version == "1.0"
        assert len(process.elements) == 7  # 1 start, 3 script calls, 1 gateway, 2 ends
        assert len(process.flows) == 6
        
        # Verify element types
        element_types = [type(e).__name__ for e in process.elements]
        assert "StartEvent" in element_types
        assert "EndEvent" in element_types
        assert "ScriptCall" in element_types
        assert "XORGateway" in element_types


if __name__ == "__main__":
    pytest.main([__file__])
