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
class XORGateway(Element):
    """Exclusive (XOR) gateway element."""
    condition: Optional[str] = None


@dataclass
class Flow(ASTNode):
    """Sequence flow between elements."""
    source_id: str
    target_id: str
    condition: Optional[str] = None


@dataclass
class FlowCondition(ASTNode):
    """Flow condition expression."""
    expression: str
