"""Main module for Power BI TMDL migration."""
import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.generators.structure_generator import create_project_structure
from src.generators.template_generator import generate_project_files
from src.parsers.database_parser import DatabaseParser

def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def migrate_to_tmdl(
    config_path: str,
    input_path: str,
    output_dir: Optional[str] = None
) -> Dict[str, List[str]]:
    """Migrate Tableau workbook to Power BI TMDL format.
    
    Args:
        config_path: Path to YAML configuration file
        input_path: Path to TWB file to convert
        output_dir: Optional output directory
    
    Returns:
        Dictionary mapping file types to lists of generated file paths
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Set output directory and add input file name subdirectory
    if not output_dir:
        output_dir = config['Templates'].get('output_dir', 'output')
    input_name = Path(input_path).stem
    project_dir = str(Path(output_dir) / input_name)
    
    # Create project structure
    created_dirs = create_project_structure(
        config_path=config_path,
        output_dir=project_dir
    )
    print("\nCreated directories:")
    for directory in sorted(created_dirs):
        print(f"  - {directory}")
    
    # Parse TWB file and extract database info
    parser = DatabaseParser(input_path, config)
    database = parser.extract_database_info()
    print(f"Extracted database name: {database.name}")
    
    # Get intermediate directory from config
    intermediate_dir = config.get('Output', {}).get('intermediate_dir', 'extracted')
    
    # Save extracted data
    extracted_dir = Path(project_dir) / intermediate_dir
    database_json = extracted_dir / 'database.json'
    with open(database_json, 'w') as f:
        json.dump(database.__dict__, f, indent=2)
    
    # Prepare config data for template generation
    config_data = {
        'PowerBiDatabase': database
    }
    
    # Generate files
    generated_files = generate_project_files(
        config_path=config_path,
        config_data=config_data,
        output_dir=project_dir
    )
    print("\nGenerated files:")
    for file_type, files in sorted(generated_files.items()):
        print(f"\n{file_type}:")
        for file in sorted(files):
            print(f"  - {file}")
    
    return {
        'directories': sorted(str(d) for d in created_dirs),
        'files': generated_files
    }

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description='Migrate Tableau workbook to Power BI TMDL format'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input data file (YAML/JSON)'
    )
    parser.add_argument(
        '--output',
        help='Output directory'
    )
    
    args = parser.parse_args()
    
    try:
        result = migrate_to_tmdl(
            config_path=args.config,
            input_path=args.input,
            output_dir=args.output
        )
        print("\nMigration completed successfully!")
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise

if __name__ == '__main__':
    main()