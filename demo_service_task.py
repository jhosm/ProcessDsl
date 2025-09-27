#!/usr/bin/env python3
"""
Demo script for serviceTask functionality in BPM DSL.

This script demonstrates:
1. Parsing a BPM file with serviceTask elements
2. Generating BPMN XML with Zeebe serviceTask extensions
3. Validating the generated XML structure
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bpm_dsl.parser import parse_bpm_file
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.validator import ProcessValidator
from bpm_dsl.ast_nodes import ServiceTask


def main():
    """Run the serviceTask demo."""
    print("🚀 BPM DSL ServiceTask Demo")
    print("=" * 50)
    
    # Parse the serviceTask demo file
    demo_file = Path("examples/service_task_demo.bpm")
    
    if not demo_file.exists():
        print(f"❌ Demo file not found: {demo_file}")
        return 1
    
    print(f"📄 Parsing: {demo_file}")
    try:
        process = parse_bpm_file(demo_file)
        print(f"✅ Successfully parsed process: '{process.name}' (ID: {process.id})")
        
        # Count serviceTask elements
        service_tasks = [elem for elem in process.elements if isinstance(elem, ServiceTask)]
        print(f"🔧 Found {len(service_tasks)} serviceTask elements:")
        
        for task in service_tasks:
            print(f"   • {task.name} (type: {task.task_type}, retries: {task.retries})")
            if task.headers:
                print(f"     Headers: {[(h.key, h.value) for h in task.headers]}")
            if task.input_mappings:
                print(f"     Input vars: {[m.source for m in task.input_mappings]}")
            if task.output_mappings:
                print(f"     Output vars: {[m.target for m in task.output_mappings]}")
        
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return 1
    
    # Generate BPMN XML
    print("\n🏗️  Generating BPMN XML...")
    try:
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        # Save to file
        output_file = Path("examples/service_task_demo.bpmn")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_content)
        
        print(f"✅ Generated BPMN XML: {output_file}")
        
        # Show key XML snippets
        print("\n📋 Key XML Elements:")
        lines = xml_content.split('\n')
        
        # Find serviceTask elements
        in_service_task = False
        service_task_lines = []
        
        for line in lines:
            if '<serviceTask' in line:
                in_service_task = True
                service_task_lines = [line]
            elif in_service_task:
                service_task_lines.append(line)
                if '</serviceTask>' in line:
                    # Print this serviceTask
                    print("   ServiceTask XML:")
                    for task_line in service_task_lines:
                        print(f"     {task_line.strip()}")
                    print()
                    in_service_task = False
                    service_task_lines = []
        
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return 1
    
    # Validate the process
    print("🔍 Validating process...")
    try:
        validator = ProcessValidator()
        validation_result = validator.validate(process)
        
        if validation_result.is_valid:
            print("✅ Process validation passed!")
        else:
            print("⚠️  Process validation issues:")
            for error in validation_result.errors:
                print(f"   • {error}")
            for warning in validation_result.warnings:
                print(f"   ⚠️  {warning}")
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 1
    
    print("\n🎉 ServiceTask demo completed successfully!")
    print(f"📁 Generated files:")
    print(f"   • {output_file}")
    print("\n💡 You can now deploy this BPMN file to Camunda Zeebe!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
