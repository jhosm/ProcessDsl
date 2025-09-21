#!/usr/bin/env python3
"""
Demo script for default flow functionality in BPM DSL.
Shows how to use default flows with XOR gateways.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bpm_dsl.parser import parse_bpm_string
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.validator import ProcessValidator

def main():
    print("🚀 BPM DSL Default Flow Demo")
    print("=" * 50)
    
    # Load and parse the default flow demo
    demo_file = "examples/default_flow_demo.bpm"
    
    try:
        # Parse the DSL file
        print(f"📖 Parsing {demo_file}...")
        
        with open(demo_file, 'r') as f:
            dsl_content = f.read()
        
        process = parse_bpm_string(dsl_content)
        print(f"✅ Successfully parsed process: {process.name}")
        
        # Validate the process
        print("\n🔍 Validating process...")
        validator = ProcessValidator()
        validation_result = validator.validate(process)
        
        if validation_result.is_valid:
            print("✅ Process validation passed")
        else:
            print("❌ Process validation failed:")
            for error in validation_result.errors:
                print(f"  - {error}")
            return
        
        # Show flow analysis
        print("\n📊 Flow Analysis:")
        for flow in process.flows:
            flow_type = "DEFAULT" if flow.is_default else "CONDITIONAL" if flow.condition else "UNCONDITIONAL"
            condition_text = f" (condition: {flow.condition})" if flow.condition else ""
            default_flag = f" (is_default: {flow.is_default})" if hasattr(flow, 'is_default') else ""
            print(f"  {flow.source_id} -> {flow.target_id} [{flow_type}]{condition_text}{default_flag}")
        
        # Generate BPMN
        print("\n🔧 Generating BPMN XML...")
        generator = BPMNGenerator()
        bpmn_xml = generator.generate(process)
        
        # Save the generated BPMN
        output_file = "examples/default_flow_demo.bpmn"
        with open(output_file, 'w') as f:
            f.write(bpmn_xml)
        
        print(f"✅ BPMN XML generated and saved to {output_file}")
        
        # Show key parts of the generated XML
        print("\n📋 Key BPMN Elements:")
        
        # Check for default flow attribute in gateway
        if 'default=' in bpmn_xml:
            print("✅ Default flow attribute found in XOR gateway")
        else:
            print("❌ Default flow attribute not found")
            
        # Check for condition expressions
        condition_count = bpmn_xml.count('<conditionExpression')
        print(f"✅ Found {condition_count} conditional flow(s)")
        
        print("\n🎉 Demo completed successfully!")
        print(f"📁 Generated file: {output_file}")
        print("💡 You can now import this BPMN file into Camunda Modeler or deploy to Zeebe!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
