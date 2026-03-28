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
    BoundaryMessageEvent, ReceiveMessageEvent, ServiceTask,
    Subprocess, CallActivity,
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
        """Test parsing gateway elements with xor type."""
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

    def test_gateway_parallel(self):
        """Test parsing gateway elements with parallel type."""
        dsl_content = '''
        process "Parallel Process" {
            id: "parallel-process"

            start "Begin" {
                id: "start-1"
            }

            gateway "Fork" {
                id: "fork-1"
                type: parallel
            }

            end "Complete" {
                id: "end-1"
            }

            flow {
                "start-1" -> "fork-1"
                "fork-1" -> "end-1"
            }
        }
        '''

        process = parse_bpm_string(dsl_content)

        gw = process.elements[1]
        assert isinstance(gw, Gateway)
        assert gw.gateway_type == "parallel"

    def test_gateway_default_type(self):
        """Test that gateway defaults to xor when type is omitted."""
        dsl_content = '''
        process "Default Type Process" {
            id: "default-type-process"

            start "Begin" {
                id: "start-1"
            }

            gateway "Decision" {
                id: "gateway-1"
            }

            end "Complete" {
                id: "end-1"
            }

            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-1"
            }
        }
        '''

        process = parse_bpm_string(dsl_content)

        gw = process.elements[1]
        assert isinstance(gw, Gateway)
        assert gw.gateway_type == "xor"

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
                type: xor
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
                type: xor
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
        assert conditional_flow.is_default is False

        # Check the otherwise flow (maps to is_default=True)
        default_flow = next((f for f in process.flows if f.is_default), None)
        assert default_flow is not None
        assert default_flow.source_id == "gateway-1"
        assert default_flow.target_id == "end-b"
        assert default_flow.condition is None
        assert default_flow.is_default is True

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


class TestSubprocessGrammar:
    """Test subprocess grammar rules parse correctly at the Lark level.

    These tests verify grammar acceptance only — AST transformer support
    is tracked in pd-bc15d3bf.
    """

    @pytest.fixture
    def grammar_parser(self):
        """Create a raw Lark parser (no transformer) for grammar-level tests."""
        from lark import Lark
        grammar_path = Path(__file__).parent.parent / "src" / "bpm_dsl" / "grammar.lark"
        return Lark(grammar_path.read_text(), parser="lalr")

    def test_subprocess_with_child_elements_and_flow(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Order Processing" {
                serviceTask "Validate" { type: "validate" }
                serviceTask "Ship" { type: "ship" }
                flow { "validate" -> "ship" }
            }
            end "E" {}
            flow { "s" -> "order-processing" "order-processing" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_subprocess_with_explicit_id(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Work" { id: "my-sub" }
            end "E" {}
            flow { "s" -> "my-sub" "my-sub" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_nested_subprocess(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Outer" {
                subprocess "Inner" {
                    serviceTask "Work" { type: "do" }
                }
            }
            end "E" {}
            flow { "s" -> "outer" "outer" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_subprocess_with_boundary_events(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Risky" {
                serviceTask "Call" { type: "api" }
                onTimer "Timeout" { duration: 30m }
                onError "Fail" { errorCode: "ERR" }
            }
            end "E" {}
            flow { "s" -> "risky" "risky" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_subprocess_empty_body(self, grammar_parser):
        """Subprocess with no child elements or flow."""
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Empty" {}
            end "E" {}
            flow { "s" -> "empty" "empty" -> "e" }
        }
        ''')
        assert tree.data == "process"


class TestCallActivityGrammar:
    """Test callActivity grammar rules."""

    @pytest.fixture
    def grammar_parser(self):
        from lark import Lark
        grammar_path = Path(__file__).parent.parent / "src" / "bpm_dsl" / "grammar.lark"
        return Lark(grammar_path.read_text(), parser="lalr")

    def test_call_activity_minimal(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" { processId: "other-process" }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_call_activity_with_propagate(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                processId: "sub"
                propagateAllVariables: true
            }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_call_activity_with_mappings(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                id: "call-sub"
                processId: "sub-process"
                propagateAllVariables: false
                inputMappings: ["a" -> "b", "c" -> "d"]
                outputMappings: ["x" -> "y"]
            }
            end "E" {}
            flow { "s" -> "call-sub" "call-sub" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_call_activity_with_vars(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                processId: "sub"
                inputVars: ["a", "b"]
                outputVars: ["x"]
            }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        ''')
        assert tree.data == "process"


class TestMultiInstanceGrammar:
    """Test forEach/as/parallel multi-instance grammar rules."""

    @pytest.fixture
    def grammar_parser(self):
        from lark import Lark
        grammar_path = Path(__file__).parent.parent / "src" / "bpm_dsl" / "grammar.lark"
        return Lark(grammar_path.read_text(), parser="lalr")

    def test_service_task_foreach(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_service_task_foreach_as_parallel(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
                as: "item"
                parallel: true
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_subprocess_with_multi_instance(self, grammar_parser):
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Batch" {
                forEach: "orders"
                as: "order"
                parallel: false
                serviceTask "Process" { type: "proc" }
            }
            end "E" {}
            flow { "s" -> "batch" "batch" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_multi_instance_with_boundary_events(self, grammar_parser):
        """Multi-instance serviceTask with boundary events."""
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
                as: "item"
                onTimer "Timeout" { duration: 5m }
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        ''')
        assert tree.data == "process"

    def test_sequential_multi_instance(self, grammar_parser):
        """forEach without parallel defaults to sequential."""
        tree = grammar_parser.parse('''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "records"
                as: "record"
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        ''')
        assert tree.data == "process"


class TestMessageStartEvent:
    """Test message start event (start with message property)."""

    def test_start_with_message(self):
        dsl = '''
        process "T" {
            id: "t"
            start "On Order" {
                message: "order-placed"
            }
            processEntity "Load" { entityName: "Order" }
            end "Done" {}
            flow {
                "on-order" -> "load"
                "load" -> "done"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        start = p.elements[0]
        assert isinstance(start, StartEvent)
        assert start.message == "order-placed"
        assert start.timer is None

    def test_start_without_message(self):
        dsl = '''
        process "T" {
            id: "t"
            start "Begin" {}
            processEntity "Load" { entityName: "Foo" }
            end "Done" {}
            flow { "begin" -> "load" "load" -> "done" }
        }
        '''
        p = parse_bpm_string(dsl)
        start = p.elements[0]
        assert start.message is None

    def test_start_with_message_auto_id(self):
        """Message start event generates kebab-case ID from name."""
        dsl = '''
        process "T" {
            id: "t"
            start "Webhook Received" {
                message: "webhook-event"
            }
            processEntity "Load" { entityName: "Foo" }
            end "Done" {}
            flow { "webhook-received" -> "load" "load" -> "done" }
        }
        '''
        p = parse_bpm_string(dsl)
        start = p.elements[0]
        assert start.id == "webhook-received"
        assert start.message == "webhook-event"


class TestReceiveMessageEvent:
    """Test receiveMessage intermediate catch event parsing."""

    def test_receive_message_basic(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            receiveMessage "Wait For Payment" {
                message: "payment-received"
                correlationKey: "orderId"
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "wait-for-payment"
                "wait-for-payment" -> "e"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        rm = p.elements[2]
        assert isinstance(rm, ReceiveMessageEvent)
        assert rm.name == "Wait For Payment"
        assert rm.id == "wait-for-payment"
        assert rm.message == "payment-received"
        assert rm.correlation_key == "orderId"

    def test_receive_message_with_explicit_id(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            receiveMessage "Wait" {
                id: "my-wait"
                message: "signal"
                correlationKey: "processId"
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "my-wait"
                "my-wait" -> "e"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        rm = p.elements[2]
        assert rm.id == "my-wait"
        assert rm.message == "signal"
        assert rm.correlation_key == "processId"


class TestBoundaryMessageEvent:
    """Test onMessage boundary event parsing."""

    def test_on_message_boundary(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Process Order" {
                type: "order-processor"
                onMessage "Payment Update" {
                    message: "payment-status"
                    correlationKey: "orderId"
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "process-order"
                "process-order" -> "e"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[2]
        assert isinstance(task, ServiceTask)
        assert len(task.boundary_events) == 1

        be = task.boundary_events[0]
        assert isinstance(be, BoundaryMessageEvent)
        assert be.name == "Payment Update"
        assert be.id == "payment-update"
        assert be.message == "payment-status"
        assert be.correlation_key == "orderId"
        assert be.attached_to_ref == "process-order"
        assert be.interrupting is True

    def test_on_message_non_interrupting(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Long Task" {
                type: "worker"
                onMessage "Status Check" {
                    message: "check-status"
                    correlationKey: "taskId"
                    interrupting: false
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "long-task"
                "long-task" -> "e"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        be = p.elements[2].boundary_events[0]
        assert isinstance(be, BoundaryMessageEvent)
        assert be.interrupting is False

    def test_mixed_boundary_events_with_message(self):
        """Service task with timer, error, and message boundary events."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Call API" {
                type: "api-call"
                onTimer "Timeout" {
                    duration: 5m
                }
                onError "Error Handler" {
                    errorCode: "API_ERROR"
                }
                onMessage "Cancel Signal" {
                    message: "cancel-request"
                    correlationKey: "requestId"
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "call-api"
                "call-api" -> "e"
            }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[2]
        assert len(task.boundary_events) == 3

        assert isinstance(task.boundary_events[0], BoundaryTimerEvent)
        assert isinstance(task.boundary_events[1], BoundaryErrorEvent)
        assert isinstance(task.boundary_events[2], BoundaryMessageEvent)
        assert task.boundary_events[2].message == "cancel-request"
        assert task.boundary_events[2].correlation_key == "requestId"


class TestSubprocessTransformer:
    """Test subprocess AST transformer (pd-bc15d3bf)."""

    def test_subprocess_with_child_elements_and_flow(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Order Processing" {
                serviceTask "Validate" { type: "validate" }
                serviceTask "Ship" { type: "ship" }
                flow { "validate" -> "ship" }
            }
            end "E" {}
            flow { "s" -> "order-processing" "order-processing" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        sub = p.elements[1]
        assert isinstance(sub, Subprocess)
        assert sub.name == "Order Processing"
        assert sub.id == "order-processing"
        assert len(sub.elements) == 2
        assert isinstance(sub.elements[0], ServiceTask)
        assert sub.elements[0].task_type == "validate"
        assert isinstance(sub.elements[1], ServiceTask)
        assert sub.elements[1].task_type == "ship"
        assert len(sub.flows) == 1
        assert sub.flows[0].source_id == "validate"
        assert sub.flows[0].target_id == "ship"

    def test_subprocess_with_explicit_id(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Work" { id: "my-sub" }
            end "E" {}
            flow { "s" -> "my-sub" "my-sub" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        sub = p.elements[1]
        assert isinstance(sub, Subprocess)
        assert sub.id == "my-sub"
        assert sub.elements == []
        assert sub.flows == []

    def test_nested_subprocess(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Outer" {
                subprocess "Inner" {
                    serviceTask "Work" { type: "do" }
                }
            }
            end "E" {}
            flow { "s" -> "outer" "outer" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        outer = p.elements[1]
        assert isinstance(outer, Subprocess)
        assert outer.id == "outer"
        assert len(outer.elements) == 1
        inner = outer.elements[0]
        assert isinstance(inner, Subprocess)
        assert inner.id == "inner"
        assert len(inner.elements) == 1
        assert isinstance(inner.elements[0], ServiceTask)

    def test_subprocess_with_boundary_events(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Risky" {
                serviceTask "Call" { type: "api" }
                onTimer "Timeout" { duration: 30m }
                onError "Fail" { errorCode: "ERR" }
            }
            end "E" {}
            flow { "s" -> "risky" "risky" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        sub = p.elements[1]
        assert isinstance(sub, Subprocess)
        assert len(sub.elements) == 1
        assert len(sub.boundary_events) == 2
        assert isinstance(sub.boundary_events[0], BoundaryTimerEvent)
        assert sub.boundary_events[0].attached_to_ref == "risky"
        assert isinstance(sub.boundary_events[1], BoundaryErrorEvent)
        assert sub.boundary_events[1].attached_to_ref == "risky"

    def test_subprocess_with_multi_instance(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Batch" {
                forEach: "orders"
                as: "order"
                parallel: false
                serviceTask "Process" { type: "proc" }
            }
            end "E" {}
            flow { "s" -> "batch" "batch" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        sub = p.elements[1]
        assert isinstance(sub, Subprocess)
        assert sub.for_each == "orders"
        assert sub.as_var == "order"
        assert sub.parallel is False
        assert len(sub.elements) == 1

    def test_subprocess_empty_body(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            subprocess "Empty" {}
            end "E" {}
            flow { "s" -> "empty" "empty" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        sub = p.elements[1]
        assert isinstance(sub, Subprocess)
        assert sub.elements == []
        assert sub.flows == []
        assert sub.boundary_events == []


class TestCallActivityTransformer:
    """Test callActivity AST transformer (pd-bc15d3bf)."""

    def test_call_activity_minimal(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" { processId: "other-process" }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        ca = p.elements[1]
        assert isinstance(ca, CallActivity)
        assert ca.name == "Invoke"
        assert ca.id == "invoke"
        assert ca.process_id == "other-process"
        assert ca.input_mappings == []
        assert ca.output_mappings == []

    def test_call_activity_with_explicit_id(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                id: "call-sub"
                processId: "sub-process"
            }
            end "E" {}
            flow { "s" -> "call-sub" "call-sub" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        ca = p.elements[1]
        assert ca.id == "call-sub"
        assert ca.process_id == "sub-process"

    def test_call_activity_with_mappings(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                processId: "sub-process"
                inputMappings: ["a" -> "b", "c" -> "d"]
                outputMappings: ["x" -> "y"]
            }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        ca = p.elements[1]
        assert len(ca.input_mappings) == 2
        assert ca.input_mappings[0].source == "a"
        assert ca.input_mappings[0].target == "b"
        assert len(ca.output_mappings) == 1
        assert ca.output_mappings[0].source == "x"

    def test_call_activity_with_vars(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            callActivity "Invoke" {
                processId: "sub"
                inputVars: ["a", "b"]
                outputVars: ["x"]
            }
            end "E" {}
            flow { "s" -> "invoke" "invoke" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        ca = p.elements[1]
        assert len(ca.input_mappings) == 2
        assert ca.input_mappings[0].source == "a"
        assert ca.input_mappings[0].target == "a"
        assert len(ca.output_mappings) == 1


class TestMultiInstanceTransformer:
    """Test multi-instance (forEach/as/parallel) AST transformer (pd-bc15d3bf)."""

    def test_service_task_foreach(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert isinstance(task, ServiceTask)
        assert task.for_each == "items"
        assert task.as_var is None
        assert task.parallel is False

    def test_service_task_foreach_as_parallel(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
                as: "item"
                parallel: true
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert task.for_each == "items"
        assert task.as_var == "item"
        assert task.parallel is True

    def test_service_task_foreach_defaults_sequential(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "records"
                as: "record"
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert task.for_each == "records"
        assert task.as_var == "record"
        assert task.parallel is False

    def test_multi_instance_with_boundary_events(self):
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Each" {
                type: "process"
                forEach: "items"
                as: "item"
                onTimer "Timeout" { duration: 5m }
            }
            end "E" {}
            flow { "s" -> "each" "each" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert task.for_each == "items"
        assert task.as_var == "item"
        assert len(task.boundary_events) == 1
        assert isinstance(task.boundary_events[0], BoundaryTimerEvent)

    def test_service_task_without_multi_instance(self):
        """Verify existing service tasks still default to no multi-instance."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            serviceTask "Simple" { type: "basic" }
            end "E" {}
            flow { "s" -> "simple" "simple" -> "e" }
        }
        '''
        p = parse_bpm_string(dsl)
        task = p.elements[1]
        assert task.for_each is None
        assert task.as_var is None
        assert task.parallel is False


class TestXorGatewayRejected:
    """Test that the legacy xorGateway keyword is rejected by the parser."""

    def test_xor_gateway_keyword_rejected(self):
        """xorGateway is no longer valid syntax and must cause a parse error."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            xorGateway "Check" {
                when: "x > 0"
            }
            end "E" {}
            flow { "s" -> "check" "check" -> "e" }
        }
        '''
        with pytest.raises(Exception):
            parse_bpm_string(dsl)


if __name__ == "__main__":
    pytest.main([__file__])
