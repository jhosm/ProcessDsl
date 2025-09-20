"""Command-line interface for BPM DSL."""

import click
import sys
from pathlib import Path
from typing import Optional

from .parser import BPMParser
from .bpmn_generator import BPMNGenerator
from .validator import ProcessValidator


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """BPM DSL - Text-based Business Process Modeling Language."""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output BPMN file path (default: input_file.bpmn)')
@click.option('--validate/--no-validate', default=True, 
              help='Validate the process before generating BPMN')
@click.option('--pretty/--no-pretty', default=True,
              help='Pretty-print the generated XML')
def convert(input_file: Path, output: Optional[Path], validate: bool, pretty: bool):
    """Convert a BPM DSL file to BPMN XML."""
    try:
        # Parse the input file
        click.echo(f"Parsing {input_file}...")
        parser = BPMParser()
        process = parser.parse_file(input_file)
        
        click.echo(f"✓ Successfully parsed process '{process.name}' (ID: {process.id})")
        
        # Validate if requested
        if validate:
            click.echo("Validating process...")
            validator = ProcessValidator()
            validation_result = validator.validate(process)
            
            if not validation_result.is_valid:
                click.echo("❌ Validation failed:")
                for error in validation_result.errors:
                    click.echo(f"  • {error}")
                sys.exit(1)
            
            click.echo("✓ Process validation passed")
        
        # Generate output file path if not specified
        if output is None:
            output = input_file.with_suffix('.bpmn')
        
        # Generate BPMN XML
        click.echo(f"Generating BPMN XML...")
        generator = BPMNGenerator()
        generator.save_to_file(process, str(output))
        
        click.echo(f"✓ Successfully generated BPMN file: {output}")
        
        # Show process summary
        click.echo(f"\nProcess Summary:")
        click.echo(f"  Name: {process.name}")
        click.echo(f"  ID: {process.id}")
        click.echo(f"  Version: {process.version or 'N/A'}")
        click.echo(f"  Elements: {len(process.elements)}")
        click.echo(f"  Flows: {len(process.flows)}")
        
    except FileNotFoundError as e:
        click.echo(f"❌ File not found: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Parse error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
def validate(input_file: Path):
    """Validate a BPM DSL file."""
    try:
        # Parse the input file
        click.echo(f"Parsing {input_file}...")
        parser = BPMParser()
        process = parser.parse_file(input_file)
        
        click.echo(f"✓ Successfully parsed process '{process.name}'")
        
        # Validate the process
        click.echo("Validating process...")
        validator = ProcessValidator()
        result = validator.validate(process)
        
        if result.is_valid:
            click.echo("✅ Process validation passed!")
            
            # Show process info
            click.echo(f"\nProcess Information:")
            click.echo(f"  Name: {process.name}")
            click.echo(f"  ID: {process.id}")
            click.echo(f"  Version: {process.version or 'N/A'}")
            click.echo(f"  Elements: {len(process.elements)}")
            click.echo(f"  Flows: {len(process.flows)}")
            
        else:
            click.echo("❌ Process validation failed:")
            for error in result.errors:
                click.echo(f"  • {error}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
def info(input_file: Path):
    """Show information about a BPM DSL file."""
    try:
        # Parse the input file
        parser = BPMParser()
        process = parser.parse_file(input_file)
        
        # Display detailed information
        click.echo(f"Process Information:")
        click.echo(f"  Name: {process.name}")
        click.echo(f"  ID: {process.id}")
        click.echo(f"  Version: {process.version or 'N/A'}")
        click.echo(f"  Total Elements: {len(process.elements)}")
        click.echo(f"  Total Flows: {len(process.flows)}")
        
        # Element breakdown
        element_types = {}
        for element in process.elements:
            element_type = type(element).__name__
            element_types[element_type] = element_types.get(element_type, 0) + 1
        
        click.echo(f"\nElement Breakdown:")
        for element_type, count in element_types.items():
            click.echo(f"  {element_type}: {count}")
        
        # List all elements
        click.echo(f"\nElements:")
        for element in process.elements:
            click.echo(f"  • {type(element).__name__}: {element.name} (ID: {element.id})")
        
        # List all flows
        if process.flows:
            click.echo(f"\nFlows:")
            for flow in process.flows:
                condition_str = f" [condition: {flow.condition}]" if flow.condition else ""
                click.echo(f"  • {flow.source_id} → {flow.target_id}{condition_str}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
