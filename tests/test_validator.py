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


if __name__ == "__main__":
    pytest.main([__file__])
