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


if __name__ == "__main__":
    pytest.main([__file__])
