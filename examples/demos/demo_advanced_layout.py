#!/usr/bin/env python3
"""
Demonstration of the advanced BPMN layout algorithm.

This script shows how the new layout engine creates professional-looking
BPMN diagrams with proper positioning, gateway branch handling, and 
intelligent edge routing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from bpm_dsl.parser import BPMParser
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.layout_engine import LayoutConfig


def demo_simple_process():
    """Demo a simple linear process."""
    print("=== Demo 1: Simple Linear Process ===")
    
    dsl_content = '''
    process "Simple Order Process" {
        id: "simple-order"
        version: "1.0"
        
        start "Order Received" {
            id: "start-order"
        }
        
        scriptCall "Validate Order" {
            id: "validate-order"
            script: "orderValid = order.amount > 0 && order.customer != null"
            inputVars: ["order"]
            outputVars: ["orderValid"]
        }
        
        scriptCall "Process Payment" {
            id: "process-payment"
            script: "paymentResult = processPayment(order.amount, order.paymentMethod)"
            inputVars: ["order"]
            outputVars: ["paymentResult"]
        }
        
        end "Order Completed" {
            id: "end-order"
        }
        
        flow {
            "start-order" -> "validate-order"
            "validate-order" -> "process-payment"
            "process-payment" -> "end-order"
        }
    }
    '''
    
    # Parse and generate
    parser = BPMParser()
    process = parser.parse_string(dsl_content)
    
    generator = BPMNGenerator()
    bpmn_xml = generator.generate(process)
    
    # Save to file
    with open('demo_simple_layout.bpmn', 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(bpmn_xml)
    
    print("✅ Generated: demo_simple_layout.bpmn")
    print("   - Linear layout with proper spacing")
    print("   - Optimized edge routing")


def demo_gateway_process():
    """Demo a process with gateway branches."""
    print("\n=== Demo 2: Process with Gateway Branches ===")
    
    dsl_content = '''
    process "Order Approval Process" {
        id: "order-approval"
        version: "1.0"
        
        start "Order Submitted" {
            id: "start-submit"
        }
        
        scriptCall "Check Order Amount" {
            id: "check-amount"
            script: "needsApproval = order.amount > 1000"
            inputVars: ["order"]
            outputVars: ["needsApproval"]
        }
        
        gateway "Approval Required?" {
            id: "approval-gateway"
            type: xor
        }
        
        scriptCall "Auto Approve" {
            id: "auto-approve"
            script: "status = 'approved'"
            outputVars: ["status"]
        }
        
        scriptCall "Manual Review" {
            id: "manual-review"
            script: "status = 'pending_review'"
            outputVars: ["status"]
        }
        
        scriptCall "Manager Approval" {
            id: "manager-approval"
            script: "status = managerDecision == 'approve' ? 'approved' : 'rejected'"
            inputVars: ["managerDecision"]
            outputVars: ["status"]
        }
        
        gateway "Merge Results" {
            id: "merge-gateway"
            type: xor
        }
        
        end "Process Complete" {
            id: "end-process"
        }
        
        flow {
            "start-submit" -> "check-amount"
            "check-amount" -> "approval-gateway"
            "approval-gateway" -> "auto-approve" [when: "needsApproval == false"]
            "approval-gateway" -> "manual-review" [when: "needsApproval == true"]
            "manual-review" -> "manager-approval"
            "auto-approve" -> "merge-gateway"
            "manager-approval" -> "merge-gateway"
            "merge-gateway" -> "end-process"
        }
    }
    '''
    
    # Parse and generate
    parser = BPMParser()
    process = parser.parse_string(dsl_content)
    
    generator = BPMNGenerator()
    bpmn_xml = generator.generate(process)
    
    # Save to file
    with open('demo_gateway_layout.bpmn', 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(bpmn_xml)
    
    print("✅ Generated: demo_gateway_layout.bpmn")
    print("   - Gateway branches properly spaced vertically")
    print("   - Merge gateway positioned correctly")
    print("   - Conditional flows with proper routing")


def demo_custom_layout_config():
    """Demo with custom layout configuration."""
    print("\n=== Demo 3: Custom Layout Configuration ===")
    
    # Create custom layout config
    custom_config = LayoutConfig()
    custom_config.SPACING['horizontal'] = 200  # More horizontal spacing
    custom_config.SPACING['vertical'] = 120    # More vertical spacing
    custom_config.SPACING['gateway_branch'] = 150  # More branch spacing
    
    dsl_content = '''
    process "Document Review" {
        id: "doc-review"
        version: "1.0"
        
        start "Document Received" {
            id: "start-doc"
        }
        
        scriptCall "Initial Check" {
            id: "initial-check"
            script: "isValid = document.format == 'PDF' && document.size < 10000000"
            inputVars: ["document"]
            outputVars: ["isValid"]
        }
        
        gateway "Valid Document?" {
            id: "valid-gateway"
            type: xor
        }
        
        scriptCall "Reject Document" {
            id: "reject-doc"
            script: "status = 'rejected'"
            outputVars: ["status"]
        }
        
        scriptCall "Technical Review" {
            id: "tech-review"
            script: "techScore = performTechnicalReview(document)"
            inputVars: ["document"]
            outputVars: ["techScore"]
        }
        
        scriptCall "Content Review" {
            id: "content-review"
            script: "contentScore = performContentReview(document)"
            inputVars: ["document"]
            outputVars: ["contentScore"]
        }
        
        scriptCall "Final Decision" {
            id: "final-decision"
            script: "finalStatus = (techScore + contentScore) > 7 ? 'approved' : 'needs_revision'"
            inputVars: ["techScore", "contentScore"]
            outputVars: ["finalStatus"]
        }
        
        end "Review Complete" {
            id: "end-review"
        }
        
        flow {
            "start-doc" -> "initial-check"
            "initial-check" -> "valid-gateway"
            "valid-gateway" -> "reject-doc" [when: "isValid == false"]
            "valid-gateway" -> "tech-review" [when: "isValid == true"]
            "tech-review" -> "content-review"
            "content-review" -> "final-decision"
            "final-decision" -> "end-review"
            "reject-doc" -> "end-review"
        }
    }
    '''
    
    # Parse and generate with custom config
    parser = BPMParser()
    process = parser.parse_string(dsl_content)
    
    generator = BPMNGenerator(layout_config=custom_config)
    bpmn_xml = generator.generate(process)
    
    # Save to file
    with open('demo_custom_layout.bpmn', 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(bpmn_xml)
    
    print("✅ Generated: demo_custom_layout.bpmn")
    print("   - Custom spacing configuration applied")
    print("   - More spacious layout for better readability")


def analyze_layout_features():
    """Analyze and explain the layout algorithm features."""
    print("\n=== Layout Algorithm Features ===")
    print("🔧 STRUCTURAL ANALYSIS:")
    print("   • Builds process graph with adjacency lists")
    print("   • Identifies start/end events, gateways, and decision points")
    print("   • Detects parallel branches and potential loops")
    
    print("\n📐 LEVEL ASSIGNMENT:")
    print("   • Uses modified topological sort for horizontal positioning")
    print("   • Handles cycles and back-edges gracefully")
    print("   • Ensures proper flow direction (left to right)")
    
    print("\n🎯 ELEMENT POSITIONING:")
    print("   • Groups elements into hierarchical levels")
    print("   • Centers elements vertically within levels")
    print("   • Applies consistent spacing based on element types")
    
    print("\n🔀 GATEWAY HANDLING:")
    print("   • Detects splitting and merging gateways")
    print("   • Positions branches with appropriate vertical spacing")
    print("   • Maintains visual clarity for decision flows")
    
    print("\n🛤️  EDGE ROUTING:")
    print("   • Calculates optimal waypoints for connections")
    print("   • Uses orthogonal routing for complex paths")
    print("   • Avoids overlaps and maintains readability")
    
    print("\n⚙️  CONFIGURATION:")
    print("   • Customizable spacing and dimensions")
    print("   • Element-type-specific sizing")
    print("   • Configurable margins and layout parameters")


if __name__ == "__main__":
    print("🎨 Advanced BPMN Layout Algorithm Demonstration")
    print("=" * 50)
    
    try:
        demo_simple_process()
        demo_gateway_process()
        demo_custom_layout_config()
        analyze_layout_features()
        
        print("\n🎉 All demos completed successfully!")
        print("\nGenerated files:")
        print("  • demo_simple_layout.bpmn")
        print("  • demo_gateway_layout.bpmn") 
        print("  • demo_custom_layout.bpmn")
        print("\nOpen these files in a BPMN viewer to see the improved layouts!")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
