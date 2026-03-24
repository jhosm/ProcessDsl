"""Tests for the BPM DSL parser."""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import BPMParser, parse_bpm_string, desugar_duration
from bpm_dsl.ast_nodes import (
    Process, StartEvent, EndEvent, ScriptCall, Gateway, Flow,
    TimerEvent, TimerDefinition, BoundaryTimerEvent, BoundaryErrorEvent,
    ServiceTask,
)


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
        # Check that inputVars were converted to input_mappings
        assert len(script_call.input_mappings) == 2
        assert script_call.input_mappings[0].source == "input"
        assert script_call.input_mappings[0].target == "input"
        assert script_call.input_mappings[1].source == "config"
        assert script_call.input_mappings[1].target == "config"

        # Check that outputVars were converted to output_mappings
        assert len(script_call.output_mappings) == 2
        assert script_call.output_mappings[0].source == "result"
        assert script_call.output_mappings[0].target == "result"
        assert script_call.output_mappings[1].source == "status"
        assert script_call.output_mappings[1].target == "status"

    def test_gateway(self):
        """Test parsing gateway elements."""
        dsl_content = '''
        process "Gateway Process" {
            id: "gateway-process"

            start "Begin" {
                id: "start-1"
            }

            gateway "Decision Point" {
                id: "gateway-1"
                type: xor
                when: "amount > 1000"
            }

            end "Complete" {
                id: "end-1"
            }

            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-1" [when: "amount <= 1000"]
            }
        }
        '''

        process = parse_bpm_string(dsl_content)

        gateway = process.elements[1]
        assert isinstance(gateway, Gateway)
        assert gateway.name == "Decision Point"
        assert gateway.id == "gateway-1"
        assert gateway.gateway_type == "xor"
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

            gateway "Order Valid?" {
                id: "order-valid-gateway"
                when: "isValid == true"
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
                "order-valid-gateway" -> "process-order" [when: "isValid == true"]
                "order-valid-gateway" -> "handle-invalid" [when: "isValid == false"]
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
        assert "Gateway" in element_types

    def test_otherwise_flow(self):
        """Test parsing of otherwise (default) flows in gateways."""
        dsl_content = '''
        process "Otherwise Flow Test" {
            id: "otherwise-flow-test"

            start "Start" {
                id: "start-1"
            }

            gateway "Decision" {
                id: "gateway-1"
            }

            end "Path A" {
                id: "end-a"
            }

            end "Path B" {
                id: "end-b"
            }

            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-a" [when: "condition == true"]
                "gateway-1" -> "end-b" [otherwise]
            }
        }
        '''

        process = parse_bpm_string(dsl_content)

        # Check that we have 3 flows
        assert len(process.flows) == 3

        # Check the conditional flow
        conditional_flow = next((f for f in process.flows if f.condition), None)
        assert conditional_flow is not None
        assert conditional_flow.source_id == "gateway-1"
        assert conditional_flow.target_id == "end-a"
        assert conditional_flow.condition == "condition == true"
        assert conditional_flow.is_default == False

        # Check the otherwise (default) flow
        default_flow = next((f for f in process.flows if f.is_default), None)
        assert default_flow is not None
        assert default_flow.source_id == "gateway-1"
        assert default_flow.target_id == "end-b"
        assert default_flow.condition is None
        assert default_flow.is_default == True

        # Check the unconditional flow (start to gateway)
        unconditional_flow = next((f for f in process.flows if not f.condition and not f.is_default), None)
        assert unconditional_flow is not None
        assert unconditional_flow.source_id == "start-1"
        assert unconditional_flow.target_id == "gateway-1"


class TestDesugarDuration:
    """Test duration shorthand desugaring."""

    def test_seconds(self):
        assert desugar_duration("30s") == "PT30S"

    def test_minutes(self):
        assert desugar_duration("5m") == "PT5M"

    def test_hours(self):
        assert desugar_duration("2h") == "PT2H"

    def test_days(self):
        assert desugar_duration("1d") == "P1D"

    def test_hours_and_minutes(self):
        assert desugar_duration("2h30m") == "PT2H30M"

    def test_days_and_hours(self):
        assert desugar_duration("1d12h") == "P1DT12H"

    def test_full_combo(self):
        assert desugar_duration("1d2h30m15s") == "P1DT2H30M15S"

    def test_passthrough_iso(self):
        """ISO 8601 strings are returned unchanged."""
        assert desugar_duration("PT30M") == "PT30M"


class TestTimerElement:
    """Test timer intermediate catch event parsing."""

    def test_timer_with_duration_shorthand(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Wait" {
                duration: 30s
            }
            end "E" {}
            flow { "s" -> "wait" "wait" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        timer = p.elements[1]
        assert isinstance(timer, TimerEvent)
        assert timer.name == "Wait"
        assert timer.id == "wait"
        assert timer.timer.duration == "PT30S"
        assert timer.timer.date is None
        assert timer.timer.cycle is None

    def test_timer_with_iso_duration(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Wait" {
                duration: "PT1H"
            }
            end "E" {}
            flow { "s" -> "wait" "wait" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        assert p.elements[1].timer.duration == "PT1H"

    def test_timer_with_date(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Wait Until" {
                date: "2026-04-01T09:00:00Z"
            }
            end "E" {}
            flow { "s" -> "wait-until" "wait-until" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        timer = p.elements[1]
        assert timer.timer.date == "2026-04-01T09:00:00Z"
        assert timer.timer.duration is None

    def test_timer_with_cycle(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Repeat" {
                cycle: cycle(1h)
            }
            end "E" {}
            flow { "s" -> "repeat" "repeat" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        timer = p.elements[1]
        assert timer.timer.cycle == "R/PT1H"
        assert timer.timer.duration is None

    def test_timer_with_complex_cycle(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Repeat" {
                cycle: cycle(2h30m)
            }
            end "E" {}
            flow { "s" -> "repeat" "repeat" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        assert p.elements[1].timer.cycle == "R/PT2H30M"

    def test_timer_with_explicit_id(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            timer "Wait" {
                id: "my-timer"
                duration: 10s
            }
            end "E" {}
            flow { "s" -> "my-timer" "my-timer" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        assert p.elements[1].id == "my-timer"


class TestTimerStartEvent:
    """Test timer start event (start with timer property)."""

    def test_start_with_cycle_timer(self):
        dsl = '''
        process "T" {
            id: "t"
            start "Every Hour" {
                timer: cycle(1h)
            }
            end "Done" {}
            flow { "every-hour" -> "done" }
        }
        '''
        p = parse_bpm_string(dsl)
        start = p.elements[0]
        assert isinstance(start, StartEvent)
        assert start.timer is not None
        assert isinstance(start.timer, TimerDefinition)
        assert start.timer.cycle == "R/PT1H"

    def test_start_without_timer(self):
        dsl = '''
        process "T" {
            id: "t"
            start "Begin" {}
            end "Done" {}
            flow { "begin" -> "done" }
        }
        '''
        p = parse_bpm_string(dsl)
        start = p.elements[0]
        assert start.timer is None


class TestBoundaryEvents:
    """Test boundary events nested inside service tasks."""

    def test_on_timer_boundary(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Call API" {
                type: "api-call"
                onTimer "Timeout" {
                    duration: 5m
                }
            }
            end "E" {}
            flow { "s" -> "call-api" "call-api" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert isinstance(task, ServiceTask)
        assert len(task.boundary_events) == 1

        be = task.boundary_events[0]
        assert isinstance(be, BoundaryTimerEvent)
        assert be.name == "Timeout"
        assert be.id == "timeout"
        assert be.duration == "PT5M"
        assert be.attached_to_ref == "call-api"
        assert be.interrupting is True  # default

    def test_on_error_boundary(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Call API" {
                type: "api-call"
                onError "Handle Error" {
                    errorCode: "API_FAILURE"
                }
            }
            end "E" {}
            flow { "s" -> "call-api" "call-api" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert len(task.boundary_events) == 1

        be = task.boundary_events[0]
        assert isinstance(be, BoundaryErrorEvent)
        assert be.name == "Handle Error"
        assert be.error_code == "API_FAILURE"
        assert be.attached_to_ref == "call-api"
        assert be.interrupting is True

    def test_non_interrupting_boundary(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Call API" {
                type: "api-call"
                onError "Warn" {
                    errorCode: "SOFT_ERROR"
                    interrupting: false
                }
            }
            end "E" {}
            flow { "s" -> "call-api" "call-api" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        be = p.elements[1].boundary_events[0]
        assert be.interrupting is False

    def test_multiple_boundary_events(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Call API" {
                type: "api-call"
                retries: 5
                onTimer "Timeout" {
                    duration: 10m
                }
                onError "Error Handler" {
                    errorCode: "API_ERROR"
                    interrupting: false
                }
            }
            end "E" {}
            flow { "s" -> "call-api" "call-api" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert task.retries == 5
        assert len(task.boundary_events) == 2

        timer_be = task.boundary_events[0]
        assert isinstance(timer_be, BoundaryTimerEvent)
        assert timer_be.duration == "PT10M"
        assert timer_be.attached_to_ref == "call-api"

        error_be = task.boundary_events[1]
        assert isinstance(error_be, BoundaryErrorEvent)
        assert error_be.error_code == "API_ERROR"
        assert error_be.interrupting is False
        assert error_be.attached_to_ref == "call-api"

    def test_service_task_without_boundary_events(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Simple Task" {
                type: "simple"
            }
            end "E" {}
            flow { "s" -> "simple-task" "simple-task" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert len(task.boundary_events) == 0


class TestGateway:
    """Test generic gateway parsing."""

    def test_xor_gateway(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            gateway "Check" {
                type: xor
                when: "x > 0"
            }
            end "E" {}
            flow { "s" -> "check" "check" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        gw = p.elements[1]
        assert isinstance(gw, Gateway)
        assert gw.gateway_type == "xor"
        assert gw.condition == "x > 0"

    def test_parallel_gateway(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            gateway "Fork" {
                type: parallel
            }
            end "E" {}
            flow { "s" -> "fork" "fork" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        gw = p.elements[1]
        assert gw.gateway_type == "parallel"

    def test_gateway_default_type(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            gateway "Check" {}
            end "E" {}
            flow { "s" -> "check" "check" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        gw = p.elements[1]
        assert gw.gateway_type == "xor"  # default


if __name__ == "__main__":
    pytest.main([__file__])
