"""Abstract Syntax Tree node definitions for the BPM DSL."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class ASTNode(ABC):
    """Base class for all AST nodes."""
    pass


@dataclass
class Process(ASTNode):
    """Root process definition."""
    name: str
    id: str
    version: Optional[str] = None
    elements: List['Element'] = None
    flows: List['Flow'] = None
    openapi_file_path: Optional[str] = None  # Path to the OpenAPI YAML file
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []
        if self.flows is None:
            self.flows = []


@dataclass
class Element(ASTNode):
    """Base class for process elements."""
    name: str
    id: str


@dataclass
class TimerDefinition(ASTNode):
    """Timer configuration for timer events and timer start events.

    Exactly one of duration, date, or cycle should be set.
    All values are ISO 8601 strings (shorthand is desugared at parse time).
    """
    duration: Optional[str] = None  # e.g., "PT30M"
    date: Optional[str] = None      # e.g., "2026-04-01T09:00:00Z"
    cycle: Optional[str] = None     # e.g., "R/PT1H"


@dataclass
class StartEvent(Element):
    """Start event element.

    When timer is set, this becomes a timer start event that triggers
    on a schedule (typically a cycle).
    """
    timer: Optional[TimerDefinition] = None


@dataclass
class EndEvent(Element):
    """End event element."""
    pass


@dataclass
class VariableMapping(ASTNode):
    """Variable mapping from source to target."""
    source: str
    target: str


@dataclass
class ScriptCall(Element):
    """Script call task element."""
    script: str
    input_mappings: Optional[List[VariableMapping]] = None
    output_mappings: Optional[List[VariableMapping]] = None
    result_variable: Optional[str] = None
    
    def __post_init__(self):
        if self.input_mappings is None:
            self.input_mappings = []
        if self.output_mappings is None:
            self.output_mappings = []
        if self.result_variable is None:
            self.result_variable = "result"


@dataclass
class TaskHeader(ASTNode):
    """Task header key-value pair for service tasks."""
    key: str
    value: str


@dataclass
class BoundaryEvent(Element):
    """Base class for boundary events attached to a task element.

    Boundary events are nested inside task definitions in the DSL but
    rendered as sibling elements in BPMN with an attachedToRef back to
    the parent task.
    """
    attached_to_ref: Optional[str] = None  # ID of the parent task element
    interrupting: bool = True              # cancelActivity in BPMN


@dataclass
class BoundaryTimerEvent(BoundaryEvent):
    """Boundary timer event (onTimer) attached to a service task.

    Triggers after a duration elapses while the parent task is active.
    """
    duration: Optional[str] = None  # ISO 8601 duration, e.g., "PT5M"


@dataclass
class BoundaryErrorEvent(BoundaryEvent):
    """Boundary error event (onError) attached to a service task.

    Catches BPMN errors thrown by the parent task.
    """
    error_code: Optional[str] = None  # e.g., "API_ERROR"


@dataclass
class TimerEvent(Element):
    """Timer intermediate catch event.

    A standalone timer that pauses the process flow for a specified
    duration, until a date, or on a cycle.
    """
    timer: Optional[TimerDefinition] = None

    def __post_init__(self):
        if self.timer is None:
            self.timer = TimerDefinition()


@dataclass
class ServiceTask(Element):
    """Service task element for external job workers."""
    task_type: str
    retries: Optional[int] = None
    headers: Optional[List[TaskHeader]] = None
    input_mappings: Optional[List[VariableMapping]] = None
    output_mappings: Optional[List[VariableMapping]] = None
    boundary_events: Optional[List[BoundaryEvent]] = None

    def __post_init__(self):
        if self.retries is None:
            self.retries = 3
        if self.headers is None:
            self.headers = []
        if self.input_mappings is None:
            self.input_mappings = []
        if self.output_mappings is None:
            self.output_mappings = []
        if self.boundary_events is None:
            self.boundary_events = []


@dataclass
class ProcessEntity(Element):
    """Process entity element that translates to a serviceTask in Camunda.
    
    This element must always be the first task after a start task and contains:
    - id: Element identifier (auto-generated from name in kebab-case)
    - entity_name: Name of the entity
    
    The OpenAPI file path is automatically inferred from the process definition.
    """
    entity_name: str   # Name of the entity


@dataclass
class Gateway(Element):
    """Gateway element with configurable type (xor, parallel)."""
    gateway_type: str = "xor"
    condition: Optional[str] = None


# Backward-compat alias — removed once generator/validator/layout beads migrate
XORGateway = Gateway


@dataclass
class Flow(ASTNode):
    """Sequence flow between elements."""
    source_id: str
    target_id: str
    condition: Optional[str] = None
    is_default: bool = False


@dataclass
class FlowCondition(ASTNode):
    """Flow condition expression."""
    expression: str
