"""BPM DSL - A text-based domain-specific language for business process modeling."""

__version__ = "0.1.0"
__author__ = "BPM DSL Team"

from .parser import BPMParser
from .bpmn_generator import BPMNGenerator
from .ast_nodes import *

__all__ = ["BPMParser", "BPMNGenerator"]
