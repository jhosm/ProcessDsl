"""Tests for the BPM DSL validator — gateway-related rules."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import parse_bpm_string
from bpm_dsl.validator import ProcessValidator


class TestGatewayValidation:
    """Validator rules for the generic gateway element."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    # --- XOR gateway (valid) ---

    def test_xor_gateway_valid(self):
        """An xor gateway with conditional flows is valid."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            gateway "Check" { type: xor }
            end "A" { id: "end-a" }
            end "B" { id: "end-b" }
            flow {
                "s" -> "load"
                "load" -> "check"
                "check" -> "end-a" [when: "x > 0"]
                "check" -> "end-b" [otherwise]
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    # --- Parallel gateway (valid) ---

    def test_parallel_gateway_valid(self):
        """A parallel gateway with unconditional flows is valid."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            gateway "Fork" { id: "fork" type: parallel }
            scriptCall "A" {
                id: "task-a"
                script: "doA()"
                inputVars: ["x"]
                outputVars: ["a"]
            }
            scriptCall "B" {
                id: "task-b"
                script: "doB()"
                inputVars: ["x"]
                outputVars: ["b"]
            }
            gateway "Join" { id: "join" type: parallel }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "fork"
                "fork" -> "task-a"
                "fork" -> "task-b"
                "task-a" -> "join"
                "task-b" -> "join"
                "join" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    # --- Parallel gateway with conditional flow (invalid) ---

    def test_parallel_gateway_rejects_conditional_flows(self):
        """Parallel gateways SHALL NOT have conditional (when) flows."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            gateway "Fork" { id: "fork" type: parallel }
            end "A" { id: "end-a" }
            end "B" { id: "end-b" }
            flow {
                "s" -> "load"
                "load" -> "fork"
                "fork" -> "end-a" [when: "x > 0"]
                "fork" -> "end-b"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert not result.is_valid
        assert any("Parallel gateway" in e and "conditional" in e for e in result.errors)

    # --- Invalid gateway type ---

    def test_invalid_gateway_type(self):
        """An unrecognised gateway type triggers a validation error."""
        from bpm_dsl.ast_nodes import Gateway, Process, StartEvent, EndEvent, ProcessEntity, Flow

        process = Process(
            name="T",
            id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                Gateway(name="Bad", id="bad", gateway_type="inclusive"),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="bad"),
                Flow(source_id="bad", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("invalid type" in e for e in result.errors)


class TestTimerValidation:
    """Validator rules for timer events and timer start events."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    def test_timer_with_valid_duration(self):
        """Timer with a valid ISO 8601 duration passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_timer_with_valid_date(self):
        """Timer with a valid ISO 8601 date passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_timer_with_valid_cycle(self):
        """Timer with a valid ISO 8601 cycle passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_timer_missing_definition_is_invalid(self):
        """Timer event with no duration/date/cycle fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, TimerEvent,
            TimerDefinition, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                TimerEvent(name="Empty Timer", id="empty-timer", timer=TimerDefinition()),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="empty-timer"),
                Flow(source_id="empty-timer", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must specify at least one" in e for e in result.errors)

    def test_timer_invalid_duration_format(self):
        """Timer with an invalid duration string fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, TimerEvent,
            TimerDefinition, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                TimerEvent(name="Bad Timer", id="bad-timer",
                           timer=TimerDefinition(duration="not-a-duration")),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="bad-timer"),
                Flow(source_id="bad-timer", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("invalid ISO 8601 duration" in e for e in result.errors)

    def test_timer_start_valid(self):
        """Timer start event with valid cycle passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_timer_start_empty_definition_invalid(self):
        """Timer start event with empty timer definition fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity,
            TimerDefinition, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="Bad Start", id="bad-start",
                           timer=TimerDefinition()),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="bad-start", target_id="load"),
                Flow(source_id="load", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("Timer start event" in e and "must specify" in e for e in result.errors)


class TestBoundaryEventValidation:
    """Validator rules for boundary timer and error events."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    def test_valid_boundary_timer(self):
        """Boundary timer with valid duration passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_valid_boundary_error(self):
        """Boundary error with valid errorCode passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_boundary_timer_missing_duration(self):
        """Boundary timer without duration fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryTimerEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="api",
                    boundary_events=[
                        BoundaryTimerEvent(
                            name="No Duration", id="no-dur",
                            attached_to_ref="task", duration=None
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must specify a duration" in e for e in result.errors)

    def test_boundary_timer_invalid_duration(self):
        """Boundary timer with invalid ISO 8601 duration fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryTimerEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="api",
                    boundary_events=[
                        BoundaryTimerEvent(
                            name="Bad Dur", id="bad-dur",
                            attached_to_ref="task", duration="INVALID"
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("invalid ISO 8601 duration" in e for e in result.errors)

    def test_boundary_error_missing_error_code(self):
        """Boundary error without errorCode fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryErrorEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="api",
                    boundary_events=[
                        BoundaryErrorEvent(
                            name="No Code", id="no-code",
                            attached_to_ref="task", error_code=None
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must specify an errorCode" in e for e in result.errors)

    def test_boundary_event_duplicate_id(self):
        """Boundary event with ID that clashes with a top-level element fails."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryTimerEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="api",
                    boundary_events=[
                        BoundaryTimerEvent(
                            name="Clash", id="s",  # duplicates start event ID
                            attached_to_ref="task", duration="PT5M"
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("duplicate ID" in e for e in result.errors)

    def test_boundary_event_invalid_attached_to_ref(self):
        """Boundary event referencing non-existent parent fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryTimerEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="api",
                    boundary_events=[
                        BoundaryTimerEvent(
                            name="Bad Ref", id="bad-ref",
                            attached_to_ref="nonexistent", duration="PT5M"
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("non-existent" in e for e in result.errors)


class TestMessageEventValidation:
    """Validator rules for message events (start, receive, boundary)."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    # --- Valid message events ---

    def test_message_start_event_valid(self):
        """Message start event with non-empty message name passes validation."""
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
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_receive_message_valid(self):
        """receiveMessage with non-empty message and correlationKey passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            receiveMessage "Wait" {
                message: "payment-received"
                correlationKey: "orderId"
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "wait"
                "wait" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_boundary_message_valid(self):
        """onMessage boundary event with message and correlationKey passes."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Work" {
                type: "worker"
                onMessage "Cancel" {
                    message: "cancel-signal"
                    correlationKey: "taskId"
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "work"
                "work" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    # --- Invalid message events ---

    def test_message_start_event_empty_message(self):
        """Message start event with empty message name fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="Bad Start", id="bad-start", message=""),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="bad-start", target_id="load"),
                Flow(source_id="load", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("Message start event" in e and "non-empty message" in e for e in result.errors)

    def test_receive_message_empty_message_name(self):
        """receiveMessage with empty message name fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity,
            ReceiveMessageEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ReceiveMessageEvent(
                    name="Bad Wait", id="bad-wait",
                    message="", correlation_key="orderId"
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="bad-wait"),
                Flow(source_id="bad-wait", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("non-empty message name" in e for e in result.errors)

    def test_receive_message_empty_correlation_key(self):
        """receiveMessage with empty correlationKey fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity,
            ReceiveMessageEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ReceiveMessageEvent(
                    name="Bad Wait", id="bad-wait",
                    message="signal", correlation_key=""
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="bad-wait"),
                Flow(source_id="bad-wait", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("non-empty correlationKey" in e for e in result.errors)

    def test_boundary_message_empty_correlation_key(self):
        """Boundary message event without correlationKey fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ProcessEntity, ServiceTask,
            BoundaryMessageEvent, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ProcessEntity(name="Load", id="load", entity_name="Foo"),
                ServiceTask(
                    name="Task", id="task", task_type="worker",
                    boundary_events=[
                        BoundaryMessageEvent(
                            name="Bad Msg", id="bad-msg",
                            attached_to_ref="task",
                            message="signal", correlation_key=""
                        ),
                    ],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="load"),
                Flow(source_id="load", target_id="task"),
                Flow(source_id="task", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("correlationKey" in e for e in result.errors)


class TestISO8601Validation:
    """Unit tests for the ISO 8601 validation helpers in ProcessValidator."""

    def test_valid_durations(self):
        v = ProcessValidator()
        assert v._is_valid_iso8601_duration("PT30S")
        assert v._is_valid_iso8601_duration("PT5M")
        assert v._is_valid_iso8601_duration("PT2H")
        assert v._is_valid_iso8601_duration("P1D")
        assert v._is_valid_iso8601_duration("P1DT2H30M15S")
        assert v._is_valid_iso8601_duration("PT0.5S")

    def test_invalid_durations(self):
        v = ProcessValidator()
        assert not v._is_valid_iso8601_duration("P")       # bare P
        assert not v._is_valid_iso8601_duration("PT")      # bare PT
        assert not v._is_valid_iso8601_duration("30s")     # shorthand, not ISO
        assert not v._is_valid_iso8601_duration("hello")
        assert not v._is_valid_iso8601_duration("")

    def test_valid_dates(self):
        v = ProcessValidator()
        assert v._is_valid_iso8601_date("2026-04-01")
        assert v._is_valid_iso8601_date("2026-04-01T09:00:00Z")
        assert v._is_valid_iso8601_date("2026-04-01T09:00:00+02:00")

    def test_invalid_dates(self):
        v = ProcessValidator()
        assert not v._is_valid_iso8601_date("not-a-date")
        assert not v._is_valid_iso8601_date("04/01/2026")

    def test_valid_cycles(self):
        v = ProcessValidator()
        assert v._is_valid_iso8601_cycle("R/PT1H")
        assert v._is_valid_iso8601_cycle("R3/PT5M")
        assert v._is_valid_iso8601_cycle("R/P1DT2H")

    def test_invalid_cycles(self):
        v = ProcessValidator()
        assert not v._is_valid_iso8601_cycle("PT1H")         # no R prefix
        assert not v._is_valid_iso8601_cycle("R/not-valid")
        assert not v._is_valid_iso8601_cycle("")


class TestSubprocessValidation:
    """Validator rules for embedded subprocesses."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    def test_valid_subprocess(self):
        """A subprocess with start, end, and valid internal flow passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            subprocess "Prepare" {
                start "Sub Start" {}
                serviceTask "Do Work" {
                    type: "worker"
                }
                end "Sub End" {}
                flow {
                    "sub-start" -> "do-work"
                    "do-work" -> "sub-end"
                }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "prepare"
                "prepare" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_subprocess_empty_body(self):
        """A subprocess with no elements fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(name="Empty", id="empty", elements=[], flows=[]),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="empty"),
                Flow(source_id="empty", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must contain at least one element" in e for e in result.errors)

    def test_subprocess_missing_start_event(self):
        """A subprocess without a start event fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, ServiceTask, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(
                    name="Bad", id="bad",
                    elements=[
                        ServiceTask(name="Task", id="task", task_type="worker"),
                        EndEvent(name="Sub End", id="sub-end"),
                    ],
                    flows=[Flow(source_id="task", target_id="sub-end")],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="bad"),
                Flow(source_id="bad", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must have at least one start event" in e for e in result.errors)

    def test_subprocess_missing_end_event(self):
        """A subprocess without an end event fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, ServiceTask, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(
                    name="Bad", id="bad",
                    elements=[
                        StartEvent(name="Sub Start", id="sub-start"),
                        ServiceTask(name="Task", id="task", task_type="worker"),
                    ],
                    flows=[Flow(source_id="sub-start", target_id="task")],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="bad"),
                Flow(source_id="bad", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("must have at least one end event" in e for e in result.errors)

    def test_subprocess_duplicate_id_across_boundary(self):
        """An element ID inside a subprocess that duplicates a top-level ID fails."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(
                    name="Sub", id="sub",
                    elements=[
                        StartEvent(name="Sub Start", id="s"),  # duplicates top-level "s"
                        EndEvent(name="Sub End", id="sub-end"),
                    ],
                    flows=[Flow(source_id="s", target_id="sub-end")],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="sub"),
                Flow(source_id="sub", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("Duplicate" in e and "subprocess boundary" in e for e in result.errors)

    def test_subprocess_flow_references_nonexistent_element(self):
        """A flow inside a subprocess referencing a non-existent element fails."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(
                    name="Sub", id="sub",
                    elements=[
                        StartEvent(name="Sub Start", id="sub-start"),
                        EndEvent(name="Sub End", id="sub-end"),
                    ],
                    flows=[Flow(source_id="sub-start", target_id="missing")],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="sub"),
                Flow(source_id="sub", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("non-existent" in e for e in result.errors)


class TestCallActivityValidation:
    """Validator rules for call activities."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def _make_process(self, dsl: str):
        return parse_bpm_string(dsl)

    def test_valid_call_activity(self):
        """A call activity with a non-empty processId passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            callActivity "Invoke Sub" {
                processId: "sub-process-v1"
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "invoke-sub"
                "invoke-sub" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_call_activity_empty_process_id(self):
        """A call activity with empty processId fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, CallActivity, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                CallActivity(name="Bad Call", id="bad-call", process_id=""),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="bad-call"),
                Flow(source_id="bad-call", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("non-empty processId" in e for e in result.errors)

    def test_call_activity_with_mappings_valid(self):
        """A call activity with input/output mappings passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            callActivity "Invoke" {
                processId: "child"
                inputMappings: ["orderId" -> "id"]
                outputMappings: ["result" -> "childResult"]
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "invoke"
                "invoke" -> "e"
            }
        }
        '''
        result = self.validator.validate(self._make_process(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


class TestMultiInstanceValidation:
    """Validator rules for multi-instance (forEach) on service tasks and subprocesses."""

    def setup_method(self):
        self.validator = ProcessValidator()

    def test_service_task_foreach_with_as_valid(self):
        """A service task with forEach + as passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            serviceTask "Send" {
                type: "email-sender"
                forEach: "recipients"
                as: "recipient"
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "send"
                "send" -> "e"
            }
        }
        '''
        result = ProcessValidator().validate(parse_bpm_string(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_service_task_foreach_missing_as(self):
        """A service task with forEach but no as variable fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, ServiceTask, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                ServiceTask(
                    name="Send", id="send", task_type="email-sender",
                    for_each="recipients", as_var=None,
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="send"),
                Flow(source_id="send", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("forEach" in e and "as" in e for e in result.errors)

    def test_subprocess_foreach_missing_as(self):
        """A subprocess with forEach but no as variable fails validation."""
        from bpm_dsl.ast_nodes import (
            Process, StartEvent, EndEvent, Subprocess, Flow,
        )

        process = Process(
            name="T", id="t",
            elements=[
                StartEvent(name="S", id="s"),
                Subprocess(
                    name="Batch", id="batch",
                    for_each="items", as_var=None,
                    elements=[
                        StartEvent(name="Sub Start", id="sub-start"),
                        EndEvent(name="Sub End", id="sub-end"),
                    ],
                    flows=[Flow(source_id="sub-start", target_id="sub-end")],
                ),
                EndEvent(name="E", id="e"),
            ],
            flows=[
                Flow(source_id="s", target_id="batch"),
                Flow(source_id="batch", target_id="e"),
            ],
        )

        result = self.validator.validate(process)
        assert not result.is_valid
        assert any("forEach" in e and "as" in e for e in result.errors)

    def test_subprocess_foreach_with_as_valid(self):
        """A subprocess with forEach + as passes validation."""
        dsl = '''
        process "T" {
            id: "t"
            start "S" {}
            processEntity "Load" { entityName: "Foo" }
            subprocess "Batch" {
                forEach: "orders"
                as: "order"
                start "Begin" {}
                end "Done" {}
                flow { "begin" -> "done" }
            }
            end "E" {}
            flow {
                "s" -> "load"
                "load" -> "batch"
                "batch" -> "e"
            }
        }
        '''
        result = ProcessValidator().validate(parse_bpm_string(dsl))
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


if __name__ == "__main__":
    pytest.main([__file__])
