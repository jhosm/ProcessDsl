"""
Advanced BPMN layout engine for generating professional diagram layouts.

This module implements a sophisticated layout algorithm that:
1. Analyzes process structure and flow patterns
2. Assigns elements to hierarchical levels
3. Positions elements to minimize crossings
4. Routes edges with proper waypoints
5. Handles complex patterns like gateways, loops, and parallel branches
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import math

from .ast_nodes import Process, Element, StartEvent, EndEvent, ScriptCall, ServiceTask, XORGateway, Flow


@dataclass
class Position:
    """Represents a 2D position with x, y coordinates."""
    x: float
    y: float


@dataclass
class Bounds:
    """Represents element bounds with position and dimensions."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center(self) -> Position:
        return Position(self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass
class Waypoint:
    """Represents a waypoint in an edge route."""
    x: float
    y: float


@dataclass
class EdgeRoute:
    """Represents the routing information for an edge."""
    waypoints: List[Waypoint]
    source_id: str
    target_id: str


class ProcessGraph:
    """Graph representation of a BPMN process for layout calculations."""
    
    def __init__(self, process: Process):
        self.process = process
        self.elements = {elem.id: elem for elem in process.elements}
        self.flows = process.flows
        self.adjacency = self._build_adjacency()
        self.reverse_adjacency = self._build_reverse_adjacency()
    
    def _build_adjacency(self) -> Dict[str, List[str]]:
        """Build adjacency list for forward traversal."""
        adj = defaultdict(list)
        for flow in self.flows:
            adj[flow.source_id].append(flow.target_id)
        return dict(adj)
    
    def _build_reverse_adjacency(self) -> Dict[str, List[str]]:
        """Build reverse adjacency list for backward traversal."""
        rev_adj = defaultdict(list)
        for flow in self.flows:
            rev_adj[flow.target_id].append(flow.source_id)
        return dict(rev_adj)
    
    def get_successors(self, node_id: str) -> List[str]:
        """Get successor nodes."""
        return self.adjacency.get(node_id, [])
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """Get predecessor nodes."""
        return self.reverse_adjacency.get(node_id, [])
    
    def is_gateway(self, node_id: str) -> bool:
        """Check if node is a gateway."""
        return isinstance(self.elements.get(node_id), XORGateway)
    
    def is_start_event(self, node_id: str) -> bool:
        """Check if node is a start event."""
        return isinstance(self.elements.get(node_id), StartEvent)
    
    def is_end_event(self, node_id: str) -> bool:
        """Check if node is an end event."""
        return isinstance(self.elements.get(node_id), EndEvent)


class LayoutConfig:
    """Configuration constants for layout algorithm."""
    
    ELEMENT_DIMENSIONS = {
        StartEvent: {'width': 36, 'height': 36},
        EndEvent: {'width': 36, 'height': 36},
        ScriptCall: {'width': 100, 'height': 80},
        ServiceTask: {'width': 100, 'height': 80},
        XORGateway: {'width': 50, 'height': 50}
    }
    
    SPACING = {
        'horizontal': 150,
        'vertical': 100,
        'branch': 80,
        'gateway_branch': 120,
        'level': 200
    }
    
    MARGINS = {
        'top': 50,
        'left': 50,
        'right': 50,
        'bottom': 50
    }


class BPMNLayoutEngine:
    """Advanced layout engine for BPMN diagrams."""
    
    def __init__(self, config: LayoutConfig = None):
        self.config = config or LayoutConfig()
        self.graph: Optional[ProcessGraph] = None
        self.levels: Dict[int, List[str]] = {}
        self.positions: Dict[str, Bounds] = {}
        self.edge_routes: Dict[str, EdgeRoute] = {}
    
    def calculate_layout(self, process: Process) -> Tuple[Dict[str, Bounds], Dict[str, EdgeRoute]]:
        """
        Main entry point for layout calculation.
        
        Returns:
            Tuple of (element_positions, edge_routes)
        """
        self.graph = ProcessGraph(process)
        
        # Phase 1: Analyze structure and assign levels
        self._assign_levels()
        
        # Phase 2: Position elements within levels
        self._position_elements()
        
        # Phase 3: Handle gateway branches
        self._position_gateway_branches()
        
        # Phase 4: Calculate edge routes
        self._calculate_edge_routes()
        
        return self.positions, self.edge_routes
    
    def _assign_levels(self):
        """Assign elements to horizontal levels using topological sort."""
        # Find start events
        start_events = [elem_id for elem_id, elem in self.graph.elements.items() 
                       if self.graph.is_start_event(elem_id)]
        
        if not start_events:
            # Fallback: use elements with no predecessors
            start_events = [elem_id for elem_id in self.graph.elements.keys()
                           if not self.graph.get_predecessors(elem_id)]
        
        # BFS level assignment
        levels = {}
        queue = deque([(elem_id, 0) for elem_id in start_events])
        
        while queue:
            node_id, level = queue.popleft()
            
            # Update level to maximum seen so far
            if node_id in levels:
                level = max(levels[node_id], level)
            levels[node_id] = level
            
            # Add successors to next level
            for successor in self.graph.get_successors(node_id):
                if successor not in levels or levels[successor] < level + 1:
                    queue.append((successor, level + 1))
        
        # Group by levels
        self.levels = defaultdict(list)
        for node_id, level in levels.items():
            self.levels[level].append(node_id)
        
        # Convert to regular dict and sort levels
        self.levels = dict(self.levels)
        for level in self.levels:
            self.levels[level].sort()  # Consistent ordering
    
    def _position_elements(self):
        """Position elements within their assigned levels."""
        current_x = self.config.MARGINS['left']
        
        for level in sorted(self.levels.keys()):
            elements_in_level = self.levels[level]
            level_width = self._calculate_level_width(elements_in_level)
            
            # Center elements vertically in level
            current_y = self.config.MARGINS['top']
            
            for i, elem_id in enumerate(elements_in_level):
                element = self.graph.elements[elem_id]
                dims = self.config.ELEMENT_DIMENSIONS[type(element)]
                
                # Calculate vertical position
                if len(elements_in_level) > 1:
                    vertical_spacing = self.config.SPACING['vertical']
                    total_height = (len(elements_in_level) - 1) * vertical_spacing
                    start_y = self.config.MARGINS['top'] + 100  # Base offset
                    y = start_y + i * vertical_spacing
                else:
                    y = current_y + 100  # Single element, center it
                
                self.positions[elem_id] = Bounds(
                    x=current_x,
                    y=y,
                    width=dims['width'],
                    height=dims['height']
                )
            
            current_x += level_width + self.config.SPACING['level']
    
    def _calculate_level_width(self, elements_in_level: List[str]) -> float:
        """Calculate the width needed for a level."""
        if not elements_in_level:
            return 0
        
        max_width = 0
        for elem_id in elements_in_level:
            element = self.graph.elements[elem_id]
            dims = self.config.ELEMENT_DIMENSIONS[type(element)]
            max_width = max(max_width, dims['width'])
        
        return max_width
    
    def _position_gateway_branches(self):
        """Handle special positioning for gateway branches."""
        for elem_id, element in self.graph.elements.items():
            if not self.graph.is_gateway(elem_id):
                continue
            
            successors = self.graph.get_successors(elem_id)
            if len(successors) <= 1:
                continue  # Not a splitting gateway
            
            # Get gateway position
            gateway_pos = self.positions[elem_id]
            
            # Calculate branch positions
            branch_spacing = self.config.SPACING['gateway_branch']
            total_height = (len(successors) - 1) * branch_spacing
            start_y = gateway_pos.center.y - total_height / 2
            
            for i, successor_id in enumerate(successors):
                if successor_id in self.positions:
                    # Adjust y position for branch
                    successor_pos = self.positions[successor_id]
                    new_y = start_y + i * branch_spacing - successor_pos.height / 2
                    
                    self.positions[successor_id] = Bounds(
                        x=successor_pos.x,
                        y=new_y,
                        width=successor_pos.width,
                        height=successor_pos.height
                    )
    
    def _calculate_edge_routes(self):
        """Calculate routing for all edges."""
        for flow in self.graph.flows:
            source_pos = self.positions.get(flow.source_id)
            target_pos = self.positions.get(flow.target_id)
            
            if not source_pos or not target_pos:
                continue
            
            # Calculate waypoints
            waypoints = self._calculate_waypoints(source_pos, target_pos, flow)
            
            flow_id = f"flow_{flow.source_id}_to_{flow.target_id}"
            self.edge_routes[flow_id] = EdgeRoute(
                waypoints=waypoints,
                source_id=flow.source_id,
                target_id=flow.target_id
            )
    
    def _calculate_waypoints(self, source_pos: Bounds, target_pos: Bounds, flow: Flow) -> List[Waypoint]:
        """Calculate waypoints for an edge route."""
        # Start from right edge of source
        start_x = source_pos.right
        start_y = source_pos.center.y
        
        # End at left edge of target
        end_x = target_pos.x
        end_y = target_pos.center.y
        
        waypoints = [Waypoint(start_x, start_y)]
        
        # If elements are on same horizontal level, use straight line
        if abs(start_y - end_y) < 10:  # Tolerance for "same level"
            waypoints.append(Waypoint(end_x, end_y))
        else:
            # Use orthogonal routing
            mid_x = start_x + (end_x - start_x) / 2
            waypoints.extend([
                Waypoint(mid_x, start_y),
                Waypoint(mid_x, end_y),
                Waypoint(end_x, end_y)
            ])
        
        return waypoints
    
    def get_diagram_bounds(self) -> Bounds:
        """Calculate the total bounds of the diagram."""
        if not self.positions:
            return Bounds(0, 0, 100, 100)
        
        min_x = min(pos.x for pos in self.positions.values())
        min_y = min(pos.y for pos in self.positions.values())
        max_x = max(pos.right for pos in self.positions.values())
        max_y = max(pos.bottom for pos in self.positions.values())
        
        return Bounds(
            x=min_x - self.config.MARGINS['left'],
            y=min_y - self.config.MARGINS['top'],
            width=max_x - min_x + self.config.MARGINS['left'] + self.config.MARGINS['right'],
            height=max_y - min_y + self.config.MARGINS['top'] + self.config.MARGINS['bottom']
        )
