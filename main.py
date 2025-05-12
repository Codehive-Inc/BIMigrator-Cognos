"""Main entry point for the migration tool."""
import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.parsers.database_parser import DatabaseParser
from src.parsers.model_parser import ModelParser
from src.parsers.table_parser import TableParser
from src.generators.structure_generator import ProjectStructureGenerator
from src.generators.database_template_generator import DatabaseTemplateGenerator
from src.generators.model_template_generator import ModelTemplateGenerator
from src.generators.table_template_generator import TableTemplateGenerator

def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def migrate_to_tmdl(input_path: str, config_path: str, output_dir: str) -> None:
    """Migrate Tableau workbook to Power BI TMDL format.
    
    Args:
        input_path: Path to TWB file to convert
        config_path: Path to YAML configuration file
        output_dir: Optional output directory
    
    Returns:
        Dictionary mapping file types to lists of generated file paths
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create output directories
    output_path = Path(output_dir)
    twb_name = Path(input_path).stem
    
    # Create output directory structure
    structure_generator = ProjectStructureGenerator(config, str(output_path / twb_name))
    created_dirs = structure_generator.create_directory_structure()
    
    # Step 1: Generate database TMDL
    print('\nStep 1: Generating database TMDL...')
    try:
        db_parser = DatabaseParser(input_path, config)
        db_info = db_parser.extract_database_info()
        
        database_generator = DatabaseTemplateGenerator(
            config_path=config_path,
            input_path=input_path
        )
        database_path = database_generator.generate_database_tmdl(db_info, output_dir=structure_generator.base_dir)
        print(f'Generated database TMDL: {database_path}')
        print(f'  Database name: {db_info.name}')
    except Exception as e:
        print(f'Failed to generate database TMDL: {str(e)}')
        return
    
    # Step 2: Generate table TMDL files
    print('\nStep 2: Generating table TMDL files...')
    try:
        table_parser = TableParser(input_path, config)
        tables = table_parser.extract_all_tables()
        
        table_generator = TableTemplateGenerator(
            config_path=config_path,
            input_path=input_path
        )
        table_paths = table_generator.generate_all_tables(tables, output_dir=structure_generator.base_dir)
        print(f'Generated {len(table_paths)} table TMDL files:')
        for path in table_paths:
            print(f'  - {path}')
    except Exception as e:
        print(f'Failed to generate table TMDL files: {str(e)}')
        return
    
    # Step 3: Generate model TMDL
    print('\nStep 3: Generating model TMDL...')
    try:
        model_parser = ModelParser(input_path, config)
        model = model_parser.extract_model_info()
        
        model_generator = ModelTemplateGenerator(
            config_path=config_path,
            input_path=input_path
        )
        model_path = model_generator.generate_model_tmdl(model, output_dir=structure_generator.base_dir)
        print(f'Generated model TMDL: {model_path}')
        print(f'  Model name: {model.model_name}')
    except Exception as e:
        print(f'Failed to generate model TMDL: {str(e)}')
        return
    
    print('\nMigration completed successfully!')

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