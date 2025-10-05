#!/usr/bin/env python3
"""
Extract process metadata from .bpm files for microservice generation.

This script parses .bpm files to extract:
- Process ID
- Entity name from processEntity declarations
- Paired OpenAPI YAML file path
- POST endpoint path

Generates process-mappings.json for runtime process discovery.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bpm_dsl.parser import parse_bpm_file
from bpm_dsl.ast_nodes import ProcessEntity


def find_yaml_file(bpm_file_path: Path) -> Optional[Path]:
    """Find the paired OpenAPI YAML file for a .bpm file."""
    yaml_path = bpm_file_path.with_suffix('.yaml')
    yml_path = bpm_file_path.with_suffix('.yml')
    
    if yaml_path.exists():
        return yaml_path
    elif yml_path.exists():
        return yml_path
    return None


def extract_post_endpoint_from_yaml(yaml_file_path: Path) -> Optional[str]:
    """Extract the POST endpoint path from OpenAPI YAML file."""
    try:
        with open(yaml_file_path, 'r') as f:
            spec = yaml.safe_load(f)
        
        # Find the first POST endpoint in paths
        if 'paths' in spec:
            for path, methods in spec['paths'].items():
                if 'post' in methods:
                    return path
        
        return None
    except Exception as e:
        print(f"Warning: Could not parse {yaml_file_path}: {e}")
        return None


def extract_entity_name_from_process(process) -> Optional[str]:
    """Extract entity name from processEntity element in the process."""
    for element in process.elements:
        if isinstance(element, ProcessEntity):
            return element.entity_name
    return None


def extract_metadata_from_bpm(bpm_file_path: Path) -> Optional[Dict]:
    """Extract metadata from a single .bpm file."""
    try:
        # Parse the .bpm file
        process = parse_bpm_file(str(bpm_file_path))
        
        # Find paired YAML file
        yaml_file = find_yaml_file(bpm_file_path)
        if not yaml_file:
            print(f"Warning: No paired YAML file found for {bpm_file_path}")
            return None
        
        # Extract entity name from processEntity
        entity_name = extract_entity_name_from_process(process)
        if not entity_name:
            print(f"Warning: No processEntity found in {bpm_file_path}")
            return None
        
        # Extract POST endpoint from YAML
        post_endpoint = extract_post_endpoint_from_yaml(yaml_file)
        if not post_endpoint:
            print(f"Warning: No POST endpoint found in {yaml_file}")
            return None
        
        # Build metadata
        metadata = {
            "processId": process.id,
            "processName": process.name,
            "entityName": entity_name,
            "bpmFile": str(bpm_file_path.relative_to(bpm_file_path.parent.parent)),
            "yamlFile": str(yaml_file.relative_to(yaml_file.parent.parent)),
            "postEndpoint": post_endpoint,
            "version": process.version or "1.0"
        }
        
        return metadata
    
    except Exception as e:
        print(f"Error processing {bpm_file_path}: {e}")
        return None


def scan_directory_for_bpm_files(directory: Path) -> List[Path]:
    """Recursively scan directory for .bpm files."""
    bpm_files = []
    for file_path in directory.rglob("*.bpm"):
        bpm_files.append(file_path)
    return sorted(bpm_files)


def generate_process_mappings(root_dir: Path, output_file: Path) -> Dict:
    """Generate process mappings JSON from all .bpm files in directory."""
    print(f"Scanning {root_dir} for .bpm files...")
    
    bpm_files = scan_directory_for_bpm_files(root_dir)
    print(f"Found {len(bpm_files)} .bpm file(s)")
    
    mappings = {}
    
    for bpm_file in bpm_files:
        print(f"\nProcessing: {bpm_file.name}")
        metadata = extract_metadata_from_bpm(bpm_file)
        
        if metadata:
            process_id = metadata["processId"]
            mappings[process_id] = metadata
            print(f"  ✓ Process ID: {process_id}")
            print(f"  ✓ Entity: {metadata['entityName']}")
            print(f"  ✓ Endpoint: {metadata['postEndpoint']}")
    
    # Write to output file
    print(f"\nWriting mappings to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(mappings, f, indent=2)
    
    print(f"✓ Generated process mappings for {len(mappings)} process(es)")
    
    return mappings


def main():
    """Main entry point."""
    # Default paths
    repo_root = Path(__file__).parent.parent
    examples_dir = repo_root / "examples"
    output_file = repo_root / "src" / "microservices" / "process-mappings.json"
    
    # Parse command-line arguments
    if len(sys.argv) > 1:
        examples_dir = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    # Validate input directory
    if not examples_dir.exists():
        print(f"Error: Directory {examples_dir} does not exist")
        sys.exit(1)
    
    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate mappings
    try:
        mappings = generate_process_mappings(examples_dir, output_file)
        
        print("\n" + "=" * 60)
        print("Process Mappings Summary")
        print("=" * 60)
        for process_id, metadata in mappings.items():
            print(f"\n{process_id}:")
            print(f"  Entity: {metadata['entityName']}")
            print(f"  Endpoint: {metadata['postEndpoint']}")
            print(f"  YAML: {metadata['yamlFile']}")
        
        print("\n✓ Process metadata extraction complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
