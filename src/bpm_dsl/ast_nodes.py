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
class StartEvent(Element):
    """Start event element."""
    pass


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
class ServiceTask(Element):
    """Service task element for external job workers."""
    task_type: str
    retries: Optional[int] = None
    headers: Optional[List[TaskHeader]] = None
    input_mappings: Optional[List[VariableMapping]] = None
    output_mappings: Optional[List[VariableMapping]] = None
    
    def __post_init__(self):
        if self.retries is None:
            self.retries = 3
        if self.headers is None:
            self.headers = []
        if self.input_mappings is None:
            self.input_mappings = []
        if self.output_mappings is None:
            self.output_mappings = []


@dataclass
class ProcessEntity(Element):
    """Process entity element that translates to a serviceTask in Camunda.
    
    This element must always be the first task after a start task and contains:
    - id: Element identifier
    - type: Job worker type
    - entity_model: Path to OpenAPI file
    - entity_name: Name of the entity
    """
    task_type: str
    entity_model: str  # Path to OpenAPI file
    entity_name: str   # Name of the entity


@dataclass
class XORGateway(Element):
    """Exclusive (XOR) gateway element."""
    condition: Optional[str] = None


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
