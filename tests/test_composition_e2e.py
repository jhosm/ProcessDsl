"""End-to-end tests for composition features: subprocess, callActivity, multi-instance.

Tests the full pipeline: DSL text → parse → validate → generate BPMN → verify XML.
"""

import pytest
from pathlib import Path
import sys
from xml.etree.ElementTree import fromstring

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import parse_bpm_string
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.validator import ProcessValidator


class TestBatchProcessingE2E:
    """End-to-end: batch processing with a multi-instance subprocess.

    Scenario: An order processing pipeline receives a batch of orders,
    iterates over each order in a parallel multi-instance subprocess,
    validates the order, calls an external payment process, then completes.
    """

    BATCH_PROCESS_DSL = '''
    process "Batch Order Processing" {
        id: "batch-order-processing"
        version: "1.0"

        start "Receive Batch" {}

        processEntity "Load Batch" { entityName: "OrderBatch" }

        subprocess "Process Orders" {
            forEach: "orders"
            as: "order"
            parallel: true

            start "Begin Order" {}

            serviceTask "Validate Order" {
                type: "order-validator"
            }

            gateway "Check Valid" {
                type: xor
            }

            serviceTask "Enrich Order" {
                type: "order-enricher"
            }

            end "Order Complete" {}
            end "Order Rejected" { id: "order-rejected" }

            flow {
                "begin-order" -> "validate-order"
                "validate-order" -> "check-valid"
                "check-valid" -> "enrich-order" [when: "order.valid = true"]
                "check-valid" -> "order-rejected" [otherwise]
                "enrich-order" -> "order-complete"
            }
        }

        callActivity "Process Payment" {
            processId: "payment-process-v2"
            inputMappings: ["orders" -> "paymentOrders"]
            outputMappings: ["paymentResult" -> "batchPaymentStatus"]
        }

        end "Batch Complete" {}

        flow {
            "receive-batch" -> "load-batch"
            "load-batch" -> "process-orders"
            "process-orders" -> "process-payment"
            "process-payment" -> "batch-complete"
        }
    }
    '''

    def test_full_pipeline_validates(self):
        """The batch process DSL parses and passes all validation rules."""
        process = parse_bpm_string(self.BATCH_PROCESS_DSL)
        validator = ProcessValidator()
        result = validator.validate(process)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_full_pipeline_generates_valid_bpmn(self):
        """The batch process generates well-formed BPMN XML."""
        process = parse_bpm_string(self.BATCH_PROCESS_DSL)
        generator = BPMNGenerator()
        xml = generator.generate(process)

        # Should not raise — validates well-formedness
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        assert root.tag.endswith('definitions')

    def test_subprocess_structure(self):
        """The subprocess contains expected nested elements and flows."""
        process = parse_bpm_string(self.BATCH_PROCESS_DSL)
        xml = BPMNGenerator().generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        subprocesses = [e for e in proc if e.tag.endswith('subProcess')]
        assert len(subprocesses) == 1

        sub = subprocesses[0]
        assert sub.get('id') == 'process-orders'
        assert sub.get('name') == 'Process Orders'

        # Multi-instance (parallel)
        mi = [e for e in sub if e.tag.endswith('multiInstanceLoopCharacteristics')]
        assert len(mi) == 1
        assert mi[0].get('isSequential') is None  # parallel = no isSequential

        ext = [e for e in mi[0] if e.tag.endswith('extensionElements')][0]
        loop_chars = [e for e in ext if e.tag.endswith('loopCharacteristics')]
        assert loop_chars[0].get('inputCollection') == '=orders'
        assert loop_chars[0].get('inputElement') == 'order'

        # Nested elements
        sub_starts = [e for e in sub if e.tag.endswith('startEvent')]
        sub_ends = [e for e in sub if e.tag.endswith('endEvent')]
        sub_tasks = [e for e in sub if e.tag.endswith('serviceTask')]
        sub_gateways = [e for e in sub if e.tag.endswith('exclusiveGateway')]
        sub_flows = [e for e in sub if e.tag.endswith('sequenceFlow')]

        assert len(sub_starts) == 1
        assert len(sub_ends) == 2
        assert len(sub_tasks) == 2
        assert len(sub_gateways) == 1
        assert len(sub_flows) == 5

    def test_call_activity_structure(self):
        """The call activity has correct zeebe:calledElement and IO mappings."""
        process = parse_bpm_string(self.BATCH_PROCESS_DSL)
        xml = BPMNGenerator().generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        cas = [e for e in proc if e.tag.endswith('callActivity')]
        assert len(cas) == 1

        ca = cas[0]
        assert ca.get('id') == 'process-payment'
        assert ca.get('name') == 'Process Payment'

        ext = [e for e in ca if e.tag.endswith('extensionElements')][0]
        called = [e for e in ext if e.tag.endswith('calledElement')]
        assert called[0].get('processId') == 'payment-process-v2'

        io = [e for e in ext if e.tag.endswith('ioMapping')]
        assert len(io) == 1

        inputs = [e for e in io[0] if e.tag.endswith('input')]
        outputs = [e for e in io[0] if e.tag.endswith('output')]
        assert len(inputs) == 1
        assert len(outputs) == 1
        assert inputs[0].get('target') == 'paymentOrders'
        assert outputs[0].get('target') == 'batchPaymentStatus'

    def test_top_level_flow_structure(self):
        """Top-level flows connect start → subprocess → callActivity → end."""
        process = parse_bpm_string(self.BATCH_PROCESS_DSL)
        xml = BPMNGenerator().generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        # Top-level sequence flows (not inside subprocess)
        all_flows = [e for e in proc if e.tag.endswith('sequenceFlow')]
        # processEntity expands to extra service task + error gateway flows
        assert len(all_flows) >= 4

        flow_pairs = [(f.get('sourceRef'), f.get('targetRef')) for f in all_flows]
        assert ('process-orders', 'process-payment') in flow_pairs
        assert ('process-payment', 'batch-complete') in flow_pairs

    def test_ast_structure(self):
        """The parsed AST has correct composition node types and properties."""
        from bpm_dsl.ast_nodes import Subprocess, CallActivity

        process = parse_bpm_string(self.BATCH_PROCESS_DSL)

        # Find subprocess
        subs = [e for e in process.elements if isinstance(e, Subprocess)]
        assert len(subs) == 1
        sub = subs[0]
        assert sub.name == "Process Orders"
        assert sub.for_each == "orders"
        assert sub.as_var == "order"
        assert sub.parallel is True
        assert len(sub.elements) == 6  # start + 2 tasks + gateway + 2 ends
        assert len(sub.flows) == 5

        # Find call activity
        cas = [e for e in process.elements if isinstance(e, CallActivity)]
        assert len(cas) == 1
        ca = cas[0]
        assert ca.process_id == "payment-process-v2"
        assert len(ca.input_mappings) == 1
        assert len(ca.output_mappings) == 1


class TestNestedSubprocessE2E:
    """End-to-end: nested subprocess (subprocess within subprocess)."""

    NESTED_DSL = '''
    process "Nested Processing" {
        id: "nested"

        start "Begin" {}

        processEntity "Load" { entityName: "Foo" }

        subprocess "Outer" {
            start "Outer Start" {}

            subprocess "Inner" {
                start "Inner Start" {}
                serviceTask "Core Work" {
                    type: "core-worker"
                }
                end "Inner End" {}
                flow {
                    "inner-start" -> "core-work"
                    "core-work" -> "inner-end"
                }
            }

            end "Outer End" {}
            flow {
                "outer-start" -> "inner"
                "inner" -> "outer-end"
            }
        }

        end "Done" {}
        flow {
            "begin" -> "load"
            "load" -> "outer"
            "outer" -> "done"
        }
    }
    '''

    def test_nested_subprocess_validates(self):
        """Nested subprocesses pass validation."""
        process = parse_bpm_string(self.NESTED_DSL)
        result = ProcessValidator().validate(process)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_nested_subprocess_bpmn(self):
        """Nested subprocesses generate correctly nested BPMN XML."""
        process = parse_bpm_string(self.NESTED_DSL)
        xml = BPMNGenerator().generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        # Outer subprocess
        outer_subs = [e for e in proc if e.tag.endswith('subProcess')]
        assert len(outer_subs) == 1
        outer = outer_subs[0]
        assert outer.get('id') == 'outer'

        # Inner subprocess nested inside outer
        inner_subs = [e for e in outer if e.tag.endswith('subProcess')]
        assert len(inner_subs) == 1
        inner = inner_subs[0]
        assert inner.get('id') == 'inner'

        # Service task nested inside inner
        tasks = [e for e in inner if e.tag.endswith('serviceTask')]
        assert len(tasks) == 1
        assert tasks[0].get('id') == 'core-work'


class TestMultiInstanceServiceTaskE2E:
    """End-to-end: service task with multi-instance (no subprocess)."""

    def test_sequential_multi_instance_service_task(self):
        """ServiceTask with sequential forEach validates and generates correctly."""
        dsl = '''
        process "Notification" {
            id: "notification"

            start "Begin" {}

            processEntity "Load" { entityName: "Foo" }

            serviceTask "Send Notifications" {
                type: "notification-sender"
                forEach: "users"
                as: "user"
            }

            end "Done" {}

            flow {
                "begin" -> "load"
                "load" -> "send-notifications"
                "send-notifications" -> "done"
            }
        }
        '''
        process = parse_bpm_string(dsl)
        result = ProcessValidator().validate(process)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

        xml = BPMNGenerator().generate(process)
        root = fromstring(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}')
        proc = [e for e in root if e.tag.endswith('process')][0]

        task = next(e for e in proc if e.tag.endswith('serviceTask') and e.get('id') == 'send-notifications')
        mi = [e for e in task if e.tag.endswith('multiInstanceLoopCharacteristics')]
        assert len(mi) == 1
        assert mi[0].get('isSequential') == 'true'


if __name__ == "__main__":
    pytest.main([__file__])
