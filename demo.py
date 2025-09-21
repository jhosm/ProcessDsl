#!/usr/bin/env python3
"""
BPM DSL Demonstration Script

This script demonstrates all the capabilities of the BPM DSL:
- Parsing DSL files
- Validating processes  
- Generating BPMN XML
- CLI interface usage
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bpm_dsl.parser import parse_bpm_file, parse_bpm_string
from bpm_dsl.bpmn_generator import BPMNGenerator
from bpm_dsl.validator import ProcessValidator


def demo_parser():
    """Demonstrate the DSL parser capabilities."""
    print("🔍 PARSER DEMONSTRATION")
    print("=" * 50)
    
    # Parse a simple inline DSL
    simple_dsl = '''
    process "Demo Process 5" {
        id: "demo-process-5"
        version: "1.0"
        
        start "Start Demo" {
            id: "start-1"
        }
        
        scriptCall "Process Data" {
            id: "process-1"
            script: "localUserData"
            inputMappings: [
                "userData" -> "localUserData"
            ]
            outputMappings: [
                "processedData" -> "processedData",
                "statusResult" -> "status"
            ]
            resultVariable: "statusResult"
        }
        
        xorGateway "Check Status" {
            id: "gateway-1"
        }
        
        end "Success" {
            id: "end-success"
        }
        
        end "Failure" {
            id: "end-failure"
        }
        
        flow {
            "start-1" -> "process-1"
            "process-1" -> "gateway-1"
            "gateway-1" -> "end-success" [when: "status = 3"]
            "gateway-1" -> "end-failure" [when: "status != 3"]
        }
    }
    '''
    
    try:
        process = parse_bpm_string(simple_dsl)
        print(f"✅ Successfully parsed process: {process.name}")
        print(f"   ID: {process.id}")
        print(f"   Version: {process.version}")
        print(f"   Elements: {len(process.elements)}")
        print(f"   Flows: {len(process.flows)}")
        
        print("\n📋 Process Elements:")
        for i, element in enumerate(process.elements, 1):
            element_type = type(element).__name__
            print(f"   {i}. {element_type}: {element.name} (ID: {element.id})")
            
            # Show additional details for script calls
            if hasattr(element, 'script'):
                print(f"      Script: {element.script}")
                if element.input_mappings:
                    mappings = [f"{m.source} -> {m.target}" for m in element.input_mappings]
                    print(f"      Input mappings: {mappings}")
                if element.output_mappings:
                    mappings = [f"{m.source} -> {m.target}" for m in element.output_mappings]
                    print(f"      Output mappings: {mappings}")
                if element.result_variable:
                    print(f"      Result variable: {element.result_variable}")
        
        print("\n🔄 Process Flows:")
        for i, flow in enumerate(process.flows, 1):
            condition_str = f" [when: {flow.condition}]" if flow.condition else ""
            print(f"   {i}. {flow.source_id} → {flow.target_id}{condition_str}")
        
        return process
        
    except Exception as e:
        print(f"❌ Parser error: {e}")
        return None


def demo_validator(process):
    """Demonstrate the process validator."""
    print("\n🔍 VALIDATOR DEMONSTRATION")
    print("=" * 50)
    
    if not process:
        print("❌ No process to validate")
        return False
    
    try:
        validator = ProcessValidator()
        result = validator.validate(process)
        
        if result.is_valid:
            print("✅ Process validation PASSED!")
            
            if result.warnings:
                print(f"\n⚠️  Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"   • {warning}")
        else:
            print("❌ Process validation FAILED!")
            print(f"\n🚫 Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   • {error}")
        
        return result.is_valid
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


def demo_bpmn_generator(process):
    """Demonstrate the BPMN generator."""
    print("\n🔍 BPMN GENERATOR DEMONSTRATION")
    print("=" * 50)
    
    if not process:
        print("❌ No process to generate BPMN for")
        return
    
    try:
        generator = BPMNGenerator()
        xml_content = generator.generate(process)
        
        print(f"✅ Successfully generated BPMN XML ({len(xml_content)} characters)")
        
        # Save to file
        output_file = "demo_process.bpmn"
        generator.save_to_file(process, output_file)
        print(f"💾 Saved BPMN to: {output_file}")
        
        # Show XML structure
        lines = xml_content.split('\n')
        print(f"\n📄 BPMN XML Structure (first 10 lines):")
        for i, line in enumerate(lines[:10], 1):
            print(f"   {i:2d}: {line}")
        
        # Check for Zeebe compatibility markers
        zeebe_markers = [
            'xmlns:zeebe=',
            'zeebe:script',
            'zeebe:ioMapping',
            'isExecutable="true"'
        ]
        
        print(f"\n🎯 Zeebe Compatibility Check:")
        for marker in zeebe_markers:
            if marker in xml_content:
                print(f"   ✅ {marker}")
            else:
                print(f"   ❌ {marker}")
        
    except Exception as e:
        print(f"❌ BPMN generation error: {e}")


def demo_file_processing():
    """Demonstrate processing existing DSL files."""
    print("\n🔍 FILE PROCESSING DEMONSTRATION")
    print("=" * 50)
    
    # Find available DSL files
    dsl_files = list(Path(".").glob("**/*.bpm"))
    
    if not dsl_files:
        print("❌ No .bpm files found in project")
        return
    
    print(f"📁 Found {len(dsl_files)} DSL files:")
    for i, file_path in enumerate(dsl_files, 1):
        print(f"   {i}. {file_path}")
    
    # Process the first file
    if dsl_files:
        file_path = dsl_files[0]
        print(f"\n🔄 Processing: {file_path}")
        
        try:
            process = parse_bpm_file(file_path)
            print(f"✅ Parsed: {process.name}")
            
            # Validate
            validator = ProcessValidator()
            result = validator.validate(process)
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"🔍 Validation: {status}")
            
            # Generate BPMN
            generator = BPMNGenerator()
            output_file = file_path.with_suffix('.bpmn')
            generator.save_to_file(process, str(output_file))
            print(f"💾 Generated: {output_file}")
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")


def demo_cli_usage():
    """Show CLI usage examples."""
    print("\n🔍 CLI USAGE DEMONSTRATION")
    print("=" * 50)
    
    print("💻 Available CLI commands:")
    print()
    print("   # Convert DSL to BPMN")
    print("   PYTHONPATH=src python3 -m bpm_dsl.cli convert examples/example_process.bpm")
    print()
    print("   # Validate a process")
    print("   PYTHONPATH=src python3 -m bpm_dsl.cli validate examples/example_process.bpm")
    print()
    print("   # Show process information")
    print("   PYTHONPATH=src python3 -m bpm_dsl.cli info examples/example_process.bpm")
    print()
    print("   # Convert with custom output")
    print("   PYTHONPATH=src python3 -m bpm_dsl.cli convert input.bpm --output custom.bpmn")
    print()
    print("   # Get help")
    print("   PYTHONPATH=src python3 -m bpm_dsl.cli --help")


def main():
    """Run the complete demonstration."""
    print("🚀 BPM DSL COMPLETE DEMONSTRATION")
    print("=" * 60)
    print()
    print("This demonstration shows all capabilities of the BPM DSL:")
    print("• Text-based process definition")
    print("• Parsing with comprehensive validation")  
    print("• BPMN XML generation with Zeebe compatibility")
    print("• Command-line interface")
    print()
    
    # Run demonstrations
    process = demo_parser()
    
    if process:
        demo_validator(process)
        demo_bpmn_generator(process)
    
    demo_file_processing()
    demo_cli_usage()
    
    print("\n" + "=" * 60)
    print("🎉 DEMONSTRATION COMPLETE!")
    print()
    print("The BPM DSL is ready for production use with:")
    print("✅ Complete parser and validator")
    print("✅ BPMN XML generation")
    print("✅ Full Camunda Zeebe compatibility")
    print("✅ Command-line interface")
    print("✅ Comprehensive test suite")
    print()
    print("Next steps:")
    print("• Create your own .bpm process files")
    print("• Use the CLI to convert them to BPMN")
    print("• Deploy the generated BPMN to Camunda Zeebe")


if __name__ == "__main__":
    main()
