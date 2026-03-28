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
        assert zeebe_script.get('expression') == '=processData(input)'  # FEEL expression format
    
    def test_xor_gateway_generation(self):
        """Test generating BPMN for XOR gateways."""
        dsl_content = '''
        process "Gateway Process" {
            id: "gateway-process"
            
            start "Begin" {
                id: "start-1"
            }
            
            gateway "Decision Point" {
                id: "gateway-1"
                when: "amount > 1000"
            }
            
            end "High Amount" {
                id: "end-high"
            }
            
            end "Low Amount" {
                id: "end-low"
            }
            
            flow {
                "start-1" -> "gateway-1"
                "gateway-1" -> "end-high" [when: "amount > 1000"]
                "gateway-1" -> "end-low" [when: "amount <= 1000"]
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

    def test_parallel_gateway_generation(self):
        """Test generating BPMN for parallel gateways."""
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

            scriptCall "Task A" {
                id: "task-a"
                script: "doA()"
                inputVars: ["x"]
                outputVars: ["a"]
            }

            scriptCall "Task B" {
                id: "task-b"
                script: "doB()"
                inputVars: ["x"]
                outputVars: ["b"]
            }

            gateway "Join" {
                id: "join-1"
                type: parallel
            }

            end "Complete" {
                id: "end-1"
            }

            flow {
                "start-1" -> "fork-1"
                "fork-1" -> "task-a"
                "fork-1" -> "task-b"
                "task-a" -> "join-1"
                "task-b" -> "join-1"
                "join-1" -> "end-1"
            }
        }
        '''

        process = parse_bpm_string(dsl_content)
        generator = BPMNGenerator()
        xml_content = generator.generate(process)

        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')
        bpmn_process = [elem for elem in root if elem.tag.endswith('process')][0]

        # Check for parallel gateways (should be 2: fork and join)
        parallel_gateways = [elem for elem in bpmn_process if elem.tag.endswith('parallelGateway')]
        assert len(parallel_gateways) == 2

        fork = next(gw for gw in parallel_gateways if gw.get('id') == 'fork-1')
        assert fork.get('name') == 'Fork'

        join = next(gw for gw in parallel_gateways if gw.get('id') == 'join-1')
        assert join.get('name') == 'Join'

        # Parallel gateways should NOT have a default attribute
        assert fork.get('default') is None
        assert join.get('default') is None

        # No exclusive gateways should be present
        exclusive_gateways = [elem for elem in bpmn_process if elem.tag.endswith('exclusiveGateway')]
        assert len(exclusive_gateways) == 0

        # Verify flows - should have 6 sequence flows
        flows = [elem for elem in bpmn_process if elem.tag.endswith('sequenceFlow')]
        assert len(flows) == 6

    def test_default_flow_generation(self):
        """Test that default flows are correctly generated in BPMN XML."""
        dsl_content = '''
        process "Default Flow Test" {
            id: "default-flow-test"
            
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
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        # Check that the gateway has a default attribute pointing to the default flow
        assert 'default="flow_gateway-1_to_end-b"' in xml_content
        
        # Check that the conditional flow has a condition expression
        assert '<conditionExpression' in xml_content
        assert 'condition = true' in xml_content
        
        # Check that the default flow does NOT have a condition expression
        # Count condition expressions - should be exactly 1 (for the conditional flow)
        condition_count = xml_content.count('<conditionExpression')
        assert condition_count == 1


class TestTimerEventBPMNGeneration:
    """Test BPMN generation for timer intermediate catch events."""

    def _parse_and_generate(self, dsl: str) -> str:
        process = parse_bpm_string(dsl)
        generator = BPMNGenerator()
        return generator.generate(process)

    def _xml_root(self, xml_content: str):
        return fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')

    def _bpmn_process(self, root):
        return [elem for elem in root if elem.tag.endswith('process')][0]

    def test_timer_duration_generates_intermediate_catch_event(self):
        """Timer with duration emits intermediateCatchEvent + timerEventDefinition/timeDuration."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            timer "Wait" { duration: 30s }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "wait"
                "wait" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        ices = [e for e in proc if e.tag.endswith('intermediateCatchEvent')]
        assert len(ices) == 1
        ice = ices[0]
        assert ice.get('id') == 'wait'
        assert ice.get('name') == 'Wait'

        timer_defs = [e for e in ice if e.tag.endswith('timerEventDefinition')]
        assert len(timer_defs) == 1

        durations = [e for e in timer_defs[0] if e.tag.endswith('timeDuration')]
        assert len(durations) == 1
        assert durations[0].text == 'PT30S'

    def test_timer_date_generates_time_date(self):
        """Timer with date emits timerEventDefinition/timeDate."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            timer "Wait Until" { date: "2026-04-01T09:00:00Z" }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "wait-until"
                "wait-until" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        ice = [e for e in proc if e.tag.endswith('intermediateCatchEvent')][0]
        timer_def = [e for e in ice if e.tag.endswith('timerEventDefinition')][0]
        dates = [e for e in timer_def if e.tag.endswith('timeDate')]
        assert len(dates) == 1
        assert dates[0].text == '2026-04-01T09:00:00Z'

    def test_timer_cycle_generates_time_cycle(self):
        """Timer with cycle emits timerEventDefinition/timeCycle."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            timer "Repeat" { cycle: cycle(1h) }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "repeat"
                "repeat" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        ice = [e for e in proc if e.tag.endswith('intermediateCatchEvent')][0]
        timer_def = [e for e in ice if e.tag.endswith('timerEventDefinition')][0]
        cycles = [e for e in timer_def if e.tag.endswith('timeCycle')]
        assert len(cycles) == 1
        assert cycles[0].text == 'R/PT1H'


class TestTimerStartBPMNGeneration:
    """Test BPMN generation for timer start events."""

    def _parse_and_generate(self, dsl: str) -> str:
        process = parse_bpm_string(dsl)
        generator = BPMNGenerator()
        return generator.generate(process)

    def _xml_root(self, xml_content: str):
        return fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')

    def _bpmn_process(self, root):
        return [elem for elem in root if elem.tag.endswith('process')][0]

    def test_timer_start_event_has_timer_definition(self):
        """Start event with timer: cycle(...) emits timerEventDefinition inside startEvent."""
        dsl = '''
        process "T" {
            id: "t"
            start "Every Hour" {
                timer: cycle(1h)
            }
            processEntity "Load" { entityName: "Foo" }
            end "Done" {}
            flow {
                "every-hour" -> "load"
                "load" -> "done"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        starts = [e for e in proc if e.tag.endswith('startEvent')]
        assert len(starts) == 1
        start = starts[0]
        assert start.get('name') == 'Every Hour'

        timer_defs = [e for e in start if e.tag.endswith('timerEventDefinition')]
        assert len(timer_defs) == 1

        cycles = [e for e in timer_defs[0] if e.tag.endswith('timeCycle')]
        assert len(cycles) == 1
        assert cycles[0].text == 'R/PT1H'

    def test_normal_start_event_no_timer_definition(self):
        """Start event without timer has no timerEventDefinition child."""
        dsl = '''
        process "T" {
            id: "t"
            start "Begin" {}
            processEntity "Load" { entityName: "Foo" }
            end "Done" {}
            flow {
                "begin" -> "load"
                "load" -> "done"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        start = [e for e in proc if e.tag.endswith('startEvent')][0]
        timer_defs = [e for e in start if e.tag.endswith('timerEventDefinition')]
        assert len(timer_defs) == 0


class TestBoundaryEventBPMNGeneration:
    """Test BPMN generation for boundary timer and error events."""

    def _parse_and_generate(self, dsl: str) -> str:
        process = parse_bpm_string(dsl)
        generator = BPMNGenerator()
        return generator.generate(process)

    def _xml_root(self, xml_content: str):
        return fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}')

    def _bpmn_process(self, root):
        return [elem for elem in root if elem.tag.endswith('process')][0]

    def test_boundary_timer_event_generation(self):
        """onTimer boundary event generates boundaryEvent with attachedToRef and timerEventDefinition."""
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
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "call-api"
                "call-api" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        boundaries = [e for e in proc if e.tag.endswith('boundaryEvent')]
        assert len(boundaries) == 1

        be = boundaries[0]
        assert be.get('id') == 'timeout'
        assert be.get('name') == 'Timeout'
        assert be.get('attachedToRef') == 'call-api'
        assert be.get('cancelActivity') == 'true'

        timer_defs = [e for e in be if e.tag.endswith('timerEventDefinition')]
        assert len(timer_defs) == 1
        durations = [e for e in timer_defs[0] if e.tag.endswith('timeDuration')]
        assert durations[0].text == 'PT5M'

    def test_boundary_error_event_generation(self):
        """onError boundary event generates boundaryEvent with errorEventDefinition."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Call API" {
                type: "api-call"
                onError "Handle Error" {
                    errorCode: "API_FAILURE"
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
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        boundaries = [e for e in proc if e.tag.endswith('boundaryEvent')]
        assert len(boundaries) == 1

        be = boundaries[0]
        assert be.get('attachedToRef') == 'call-api'
        assert be.get('cancelActivity') == 'true'

        error_defs = [e for e in be if e.tag.endswith('errorEventDefinition')]
        assert len(error_defs) == 1
        assert error_defs[0].get('errorRef') == 'error-API_FAILURE'

    def test_non_interrupting_boundary_cancel_activity_false(self):
        """Non-interrupting boundary event sets cancelActivity='false'."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Call API" {
                type: "api-call"
                onError "Warn" {
                    errorCode: "SOFT_ERROR"
                    interrupting: false
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
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        be = [e for e in proc if e.tag.endswith('boundaryEvent')][0]
        assert be.get('cancelActivity') == 'false'

    def test_multiple_boundary_events_as_siblings(self):
        """Multiple boundary events become sibling boundaryEvent elements with correct attachedToRef."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Call API" {
                type: "api-call"
                onTimer "Timeout" {
                    duration: 10m
                }
                onError "Error Handler" {
                    errorCode: "API_ERROR"
                    interrupting: false
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
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)
        proc = self._bpmn_process(root)

        boundaries = [e for e in proc if e.tag.endswith('boundaryEvent')]
        assert len(boundaries) == 2

        # Both attached to the same parent task
        for be in boundaries:
            assert be.get('attachedToRef') == 'call-api'

        # One timer, one error
        timer_bes = [b for b in boundaries if any(c.tag.endswith('timerEventDefinition') for c in b)]
        error_bes = [b for b in boundaries if any(c.tag.endswith('errorEventDefinition') for c in b)]
        assert len(timer_bes) == 1
        assert len(error_bes) == 1

    def test_error_definitions_at_definitions_level(self):
        """Boundary error events create <error> elements at the definitions level."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Call API" {
                type: "api-call"
                onError "Handle Error" {
                    errorCode: "API_FAILURE"
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
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)

        # Error definitions are children of <definitions>, not <process>
        error_defs = [e for e in root if e.tag.endswith('error')]
        # One from processEntity validation, one from boundary error
        api_error = next((e for e in error_defs if e.get('errorCode') == 'API_FAILURE'), None)
        assert api_error is not None
        assert api_error.get('id') == 'error-API_FAILURE'
        assert api_error.get('name') == 'API_FAILURE'

    def test_duplicate_error_codes_deduplicated(self):
        """Two boundary errors with same errorCode produce only one <error> definition."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Task A" {
                id: "task-a"
                type: "api-call"
                onError "Error A" {
                    errorCode: "SHARED_ERROR"
                }
            }
            serviceTask "Task B" {
                id: "task-b"
                type: "api-call"
                onError "Error B" {
                    errorCode: "SHARED_ERROR"
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "task-a"
                "task-a" -> "task-b"
                "task-b" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        root = self._xml_root(xml)

        error_defs = [e for e in root if e.tag.endswith('error') and e.get('errorCode') == 'SHARED_ERROR']
        assert len(error_defs) == 1

    def test_boundary_event_diagram_shapes(self):
        """Boundary events get their own BPMNShape elements in the diagram."""
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
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "call-api"
                "call-api" -> "e"
            }
        }
        '''
        xml = self._parse_and_generate(dsl)
        # Verify the boundary event has a shape in the diagram
        assert 'shape_timeout' in xml


class TestEndToEndTimerBoundary:
    """End-to-end test combining timer start, timer intermediate, and boundary events."""

    def test_full_timer_and_boundary_process(self):
        """Process with timer start, boundary timeout, and error handling generates valid BPMN."""
        dsl = '''
        process "Order Pipeline" {
            id: "order-pipeline"
            version: "2.0"

            start "Every 5 Minutes" {
                timer: cycle(5m)
            }

            processEntity "Load Order" {
                entityName: "Order"
            }

            timer "Cooling Period" {
                duration: 2h30m
            }

            serviceTask "Process Order" {
                type: "order-processor"
                retries: 5
                onTimer "Processing Timeout" {
                    duration: 30m
                }
                onError "Order Error" {
                    errorCode: "ORDER_FAILED"
                }
                onError "Retry Warning" {
                    errorCode: "RETRY_LIMIT"
                    interrupting: false
                }
            }

            end "Complete" {}

            flow {
                "every-5-minutes" -> "load-order"
                "load-order" -> "cooling-period"
                "cooling-period" -> "process-order"
                "process-order" -> "complete"
            }
        }
        '''
        process = parse_bpm_string(dsl)
        generator = BPMNGenerator()
        xml = generator.generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        # Timer start event
        starts = [e for e in proc if e.tag.endswith('startEvent')]
        assert len(starts) == 1
        start_timer_defs = [e for e in starts[0] if e.tag.endswith('timerEventDefinition')]
        assert len(start_timer_defs) == 1
        cycle_elem = [e for e in start_timer_defs[0] if e.tag.endswith('timeCycle')]
        assert cycle_elem[0].text == 'R/PT5M'

        # Timer intermediate catch event with desugared duration
        ices = [e for e in proc if e.tag.endswith('intermediateCatchEvent')]
        assert len(ices) == 1
        assert ices[0].get('id') == 'cooling-period'
        ice_timer = [e for e in ices[0] if e.tag.endswith('timerEventDefinition')][0]
        ice_duration = [e for e in ice_timer if e.tag.endswith('timeDuration')]
        assert ice_duration[0].text == 'PT2H30M'

        # Service task present
        service_tasks = [e for e in proc if e.tag.endswith('serviceTask')]
        # process-order + load-order (processEntity also generates a serviceTask)
        order_task = next(t for t in service_tasks if t.get('id') == 'process-order')
        assert order_task is not None

        # Boundary events (3 total: 1 timer + 2 errors)
        boundaries = [e for e in proc if e.tag.endswith('boundaryEvent')]
        assert len(boundaries) == 3
        for be in boundaries:
            assert be.get('attachedToRef') == 'process-order'

        # Verify non-interrupting error boundary
        retry_be = next(b for b in boundaries if b.get('id') == 'retry-warning')
        assert retry_be.get('cancelActivity') == 'false'

        # Verify interrupting timer boundary
        timeout_be = next(b for b in boundaries if b.get('id') == 'processing-timeout')
        assert timeout_be.get('cancelActivity') == 'true'

        # Error definitions at definitions level (deduplicated)
        error_defs = [e for e in root if e.tag.endswith('error')]
        error_codes = {e.get('errorCode') for e in error_defs}
        assert 'ORDER_FAILED' in error_codes
        assert 'RETRY_LIMIT' in error_codes

        # Sequence flows exist
        flows = [e for e in proc if e.tag.endswith('sequenceFlow')]
        assert len(flows) >= 4  # At least the 4 explicit flows (processEntity adds more)


if __name__ == "__main__":
    pytest.main([__file__])
