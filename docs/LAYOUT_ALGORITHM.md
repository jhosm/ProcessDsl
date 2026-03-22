# BPMN Visual Layout Algorithm

This document describes the advanced layout algorithm implemented for generating professional BPMN diagrams from the BPM DSL.

## Overview

The layout algorithm transforms a process definition into a visually appealing BPMN diagram with proper element positioning, intelligent edge routing, and gateway-aware branch handling.

## Algorithm Phases

### Phase 1: Graph Analysis
```
Input: Process AST (elements + flows)
Output: ProcessGraph with adjacency lists and structural patterns
```

**Steps:**
1. **Build Graph Structure**: Create adjacency lists for forward/backward traversal
2. **Identify Patterns**: Detect start/end events, gateways, parallel branches, loops
3. **Analyze Complexity**: Determine layout strategy based on process structure

**Key Data Structures:**
- `adjacency`: Forward connections (source → targets)
- `reverse_adjacency`: Backward connections (target → sources)
- `patterns`: Structural elements (gateways, branches, decision points)

### Phase 2: Level Assignment
```
Input: ProcessGraph
Output: Elements grouped by horizontal levels
```

**Algorithm: Modified Topological Sort**
```python
def assign_levels_topologically(graph, start_events):
    levels = {}
    queue = [(event.id, 0) for event in start_events]
    
    while queue:
        node_id, level = queue.pop(0)
        levels[node_id] = max(levels.get(node_id, 0), level)
        
        for successor in graph.get_successors(node_id):
            queue.append((successor, level + 1))
    
    return group_by_levels(levels)
```

**Features:**
- Handles multiple start events
- Resolves level conflicts (takes maximum level)
- Groups elements by horizontal position
- Maintains proper flow direction (left → right)

### Phase 3: Element Positioning
```
Input: Level assignments
Output: Precise x,y coordinates for each element
```

**Horizontal Positioning:**
- Elements in same level share x-coordinate
- Level spacing: configurable (default: 200px)
- Left margin applied consistently

**Vertical Positioning:**
- Elements within level distributed vertically
- Vertical spacing: configurable (default: 100px)
- Center alignment for single elements

**Element Dimensions:**
```python
ELEMENT_DIMENSIONS = {
    StartEvent: {'width': 36, 'height': 36},
    EndEvent: {'width': 36, 'height': 36},
    ScriptCall: {'width': 100, 'height': 80},
    XORGateway: {'width': 50, 'height': 50}
}
```

### Phase 4: Gateway Branch Handling
```
Input: Element positions + gateway information
Output: Adjusted positions for gateway branches
```

**Gateway Detection:**
- Identify splitting gateways (multiple outgoing flows)
- Identify merging gateways (multiple incoming flows)

**Branch Positioning Algorithm:**
```python
def position_gateway_branches(gateway, branches, base_y):
    branch_spacing = config.SPACING['gateway_branch']  # 120px
    total_height = (len(branches) - 1) * branch_spacing
    start_y = base_y - total_height / 2
    
    for i, branch in enumerate(branches):
        branch_y = start_y + i * branch_spacing
        adjust_branch_position(branch, branch_y)
```

**Features:**
- Symmetric branch distribution around gateway center
- Configurable branch spacing
- Maintains visual balance
- Handles complex gateway patterns

### Phase 5: Edge Routing
```
Input: Final element positions
Output: Waypoint sequences for each edge
```

**Routing Strategies:**

1. **Straight Line Routing** (same horizontal level):
   ```
   Source ──────────► Target
   ```

2. **Orthogonal Routing** (different levels):
   ```
   Source ──┐
            │
            └──► Target
   ```

**Waypoint Calculation:**
```python
def calculate_waypoints(source_pos, target_pos):
    start_x = source_pos.right  # Right edge of source
    start_y = source_pos.center.y
    end_x = target_pos.x        # Left edge of target
    end_y = target_pos.center.y
    
    if abs(start_y - end_y) < 10:  # Same level
        return [Waypoint(start_x, start_y), Waypoint(end_x, end_y)]
    else:  # Orthogonal routing
        mid_x = start_x + (end_x - start_x) / 2
        return [
            Waypoint(start_x, start_y),
            Waypoint(mid_x, start_y),
            Waypoint(mid_x, end_y),
            Waypoint(end_x, end_y)
        ]
```

## Configuration System

### Layout Configuration
```python
class LayoutConfig:
    ELEMENT_DIMENSIONS = {
        StartEvent: {'width': 36, 'height': 36},
        EndEvent: {'width': 36, 'height': 36},
        ScriptCall: {'width': 100, 'height': 80},
        XORGateway: {'width': 50, 'height': 50}
    }
    
    SPACING = {
        'horizontal': 150,      # Between elements in flow
        'vertical': 100,        # Between elements in same level
        'branch': 80,           # Between parallel branches
        'gateway_branch': 120,  # Between gateway branches
        'level': 200           # Between levels
    }
    
    MARGINS = {
        'top': 50, 'left': 50, 'right': 50, 'bottom': 50
    }
```

### Customization Example
```python
custom_config = LayoutConfig()
custom_config.SPACING['horizontal'] = 200  # More spacing
custom_config.SPACING['gateway_branch'] = 150  # Wider branches

generator = BPMNGenerator(layout_config=custom_config)
```

## Advanced Features

### 1. Cycle Detection and Handling
- Detects back-edges in process flow
- Adjusts level assignments to prevent visual conflicts
- Maintains topological ordering where possible

### 2. Crossing Minimization
- Uses barycenter method for reducing edge crossings
- Iterative improvement of element ordering within levels
- Optimizes visual clarity

### 3. Dynamic Spacing
- Adjusts spacing based on element types
- Considers label lengths and content
- Maintains consistent visual rhythm

### 4. Multi-Gateway Support
- Handles nested gateway structures
- Supports complex branching patterns
- Maintains visual hierarchy

## Integration with BPMN Generator

### Usage in BPMNGenerator
```python
class BPMNGenerator:
    def __init__(self, layout_config: LayoutConfig = None):
        self.layout_engine = BPMNLayoutEngine(layout_config)
    
    def _add_diagram(self, definitions, process):
        # Calculate layout
        positions, routes = self.layout_engine.calculate_layout(process)
        
        # Generate BPMN DI elements
        for element in process.elements:
            pos = positions[element.id]
            # Create bpmndi:BPMNShape with calculated bounds
        
        for flow in process.flows:
            route = routes[flow_id]
            # Create bpmndi:BPMNEdge with calculated waypoints
```

### Generated BPMN Structure
```xml
<bpmndi:BPMNDiagram>
  <bpmndi:BPMNPlane>
    <bpmndi:BPMNShape bpmnElement="element-id">
      <dc:Bounds x="150" y="100" width="100" height="80"/>
    </bpmndi:BPMNShape>
    <bpmndi:BPMNEdge bpmnElement="flow-id">
      <di:waypoint x="250" y="140"/>
      <di:waypoint x="300" y="140"/>
      <di:waypoint x="300" y="200"/>
      <di:waypoint x="350" y="200"/>
    </bpmndi:BPMNEdge>
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

## Performance Characteristics

- **Time Complexity**: O(V + E) where V = elements, E = flows
- **Space Complexity**: O(V + E) for graph representation
- **Scalability**: Handles processes with hundreds of elements efficiently
- **Memory Usage**: Minimal overhead, positions calculated on-demand

## Comparison with Simple Layout

| Feature | Simple Layout | Advanced Layout |
|---------|---------------|-----------------|
| Positioning | Fixed horizontal line | Hierarchical levels |
| Gateway Handling | No special handling | Branch-aware positioning |
| Edge Routing | Straight lines only | Orthogonal routing |
| Customization | None | Full configuration |
| Visual Quality | Basic | Professional |
| Performance | O(n) | O(V + E) |

## Future Enhancements

### Planned Features
1. **Swimlane Support**: Vertical partitioning for different actors
2. **Curved Edges**: Bezier curves for smoother connections
3. **Label Positioning**: Intelligent placement of element labels
4. **Compact Layout**: Space-optimized layout for large processes
5. **Interactive Layout**: User-adjustable positioning hints

### Advanced Algorithms
1. **Force-Directed Layout**: Physics-based positioning
2. **Hierarchical Clustering**: Group related elements
3. **Multi-Objective Optimization**: Balance multiple layout criteria
4. **Machine Learning**: Learn layout preferences from examples

## Conclusion

The advanced BPMN layout algorithm provides a significant improvement over basic positioning approaches. It creates professional, readable diagrams that properly represent the process structure while maintaining visual clarity and consistency.

The algorithm is designed to be:
- **Extensible**: Easy to add new element types and layout strategies
- **Configurable**: Customizable spacing, dimensions, and behavior
- **Efficient**: Scales well with process complexity
- **Standards-Compliant**: Generates valid BPMN DI elements

This foundation enables the BPM DSL to produce publication-quality BPMN diagrams suitable for documentation, analysis, and execution in BPMN engines like Camunda Zeebe.
