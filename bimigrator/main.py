"""Main entry point for the migration tool."""
import argparse
import json
from pathlib import Path
from typing import Dict, Any

import yaml

from bimigrator.generators.culture_generator import CultureGenerator
from bimigrator.generators.database_template_generator import DatabaseTemplateGenerator
from bimigrator.generators.model_template_generator import ModelTemplateGenerator
from bimigrator.generators.relationship_template_generator import RelationshipTemplateGenerator
from bimigrator.generators.structure_generator import ProjectStructureGenerator
from bimigrator.generators.table_template_generator import TableTemplateGenerator
from bimigrator.generators.version_generator import VersionGenerator
from bimigrator.parsers.culture_parser import CultureParser
from bimigrator.parsers.database_parser import DatabaseParser
from bimigrator.parsers.model_parser import ModelParser
from bimigrator.parsers.relationship_parser import RelationshipParser
from bimigrator.parsers.table_parser import TableParser
from bimigrator.parsers.twb_parser import parse_workbook
from bimigrator.parsers.version_parser import VersionParser


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)


def get_default_config() -> dict[str, Any]:
    """Retrieves the default config stored inside the config for all cases"""
    config_path = Path().resolve() / 'config' / 'twb-to-pbi.yaml'
    return load_config(str(config_path))


def generate_version_file(filename, config, output_dir):
    version_parser = VersionParser(filename, config)
    version_info = version_parser.extract_version()
    version_generator = VersionGenerator(config, output_dir)
    version_path = version_generator.generate_version(version_info, output_dir)
    return


def migrate_to_tmdl(filename, config: dict[str, Any], output_dir: str) -> None:
    """Migrate Tableau workbook to Power BI TMDL format.

    Args:
        filename: Name of the twb_file
        # parsed_data: Content of the TWB file parsed to dict.
        config: Dict containing configuration data
        output_dir: Optional output directory

    Returns:
        Dictionary mapping file types to their generated paths
    """

    # Create output directories
    output_path = Path(output_dir)
    twb_name = Path(filename).stem
    # Create output directory structure

    structure_generator = ProjectStructureGenerator(config, str(output_path / twb_name))
    structure_generator.create_directory_structure()
    output_dir = structure_generator.base_dir

    # Step 0: Generate version.txt
    print('\nStep 0: Generating version.txt...')
    try:
        version_parser = VersionParser(filename, config)
        version_info = version_parser.extract_version()

        version_generator = VersionGenerator(config, output_dir)
        version_path = version_generator.generate_version(version_info, output_dir)
        print(f'Generated version.txt: {version_path}')
    except Exception as e:
        print(f'Failed to generate version.txt: {str(e)}')
        raise e
        return

    # Step 1: Generate culture TMDL
    print('\nStep 1: Generating culture TMDL...')
    try:
        culture_parser = CultureParser(filename, config)
        culture_info = culture_parser.extract_culture_info()

        # Debug culture info
        print(f'Debug: Culture info - culture: {culture_info.culture}')
        if culture_info.linguistic_metadata:
            print(
                f'Debug: Linguistic metadata - entities: {len(culture_info.linguistic_metadata.entities) if culture_info.linguistic_metadata.entities else 0} entities')
            if culture_info.linguistic_metadata.entities:
                for key, entity in culture_info.linguistic_metadata.entities.items():
                    print(
                        f'Debug: Entity {key} - binding: {entity.binding.conceptual_entity if entity.binding else None}')

        # Generate culture TMDL file
        culture_generator = CultureGenerator(
            config, filename, output_dir
        )
        # Pass the correct output directory for culture TMDL
        culture_path = culture_generator.generate_culture_tmdl(
            culture_info, output_dir
        )
        print(f'Generated culture TMDL: {culture_path}')
    except Exception as e:
        print(f'Failed to generate culture TMDL: {str(e)}')

    # Step 2: Generate .pbixproj.json
    print('\nStep 2: Generating .pbixproj.json...')
    try:
        from bimigrator.parsers.pbixproj_parser import PbixprojParser
        from bimigrator.generators.pbixproj_generator import PbixprojGenerator

        pbixproj_parser = PbixprojParser(filename, config)
        project_info = pbixproj_parser.extract_pbixproj_info()

        pbixproj_generator = PbixprojGenerator(
            config,filename,output_dir
        )
        pbixproj_path = pbixproj_generator.generate_pbixproj(project_info, output_dir=structure_generator.base_dir)
        print(f'Generated .pbixproj.json: {pbixproj_path}')
    except Exception as e:
        print(f'Failed to generate .pbixproj.json: {str(e)}')
        return

    # Step 2: Generate database TMDL
    print('\nStep 1: Generating database TMDL...')
    try:
        db_parser = DatabaseParser(filename, config)
        db_info = db_parser.extract_database_info()

        database_generator = DatabaseTemplateGenerator(
            config, filename, output_dir
        )
        database_path = database_generator.generate_database_tmdl(db_info, output_dir=structure_generator.base_dir)
        print(f'Generated database TMDL: {database_path}')
        print(f'  Database name: {db_info.name}')
    except Exception as e:
        print(f'Failed to generate database TMDL: {str(e)}')
        return

    # Step 3: Generate table TMDL files
    print('\nStep 2: Generating table TMDL files...')
    try:
        table_parser = TableParser(filename, config)
        tables = table_parser.extract_all_tables()

        table_generator = TableTemplateGenerator(
            config, filename, output_dir
        )
        table_paths = table_generator.generate_all_tables(tables, output_dir=structure_generator.base_dir)
        print(f'Generated {len(table_paths)} table TMDL files:')
        for path in table_paths:
            print(f'  - {path}')
    except Exception as e:
        print(f'Failed to generate table TMDL files: {str(e)}')
        return

    # Step 3: Generate relationships TMDL
    print('\nStep 3: Generating relationship TMDL files...')
    try:
        print('Debug: Creating relationship parser...')
        relationship_parser = RelationshipParser(filename, config)
        print('Debug: Extracting relationships...')
        relationships = relationship_parser.extract_relationships()
        print(f'Debug: Found {len(relationships)} relationships')

        print('Debug: Creating relationship generator...')
        relationship_generator = RelationshipTemplateGenerator(
            config, filename, output_dir
        )
        print('Debug: Generating relationship TMDL files...')
        relationship_paths = relationship_generator.generate_relationships(
            relationships,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated {len(relationship_paths)} relationship TMDL files:')
        for path in relationship_paths:
            print(f'  - {path}')
    except Exception as e:
        print(f'Failed to generate relationship TMDL files: {str(e)}')
        import traceback
        traceback.print_exc()

    # Step 4: Generate model TMDL
    print('\nStep 4: Generating model TMDL...')
    try:
        model_parser = ModelParser(filename, config)
        model, tables = model_parser.extract_model_info()

        model_generator = ModelTemplateGenerator(
            config, filename, output_dir
        )
        model_path = model_generator.generate_model_tmdl(model, tables, output_dir=structure_generator.base_dir)
        print(f'Generated model TMDL: {model_path}')
        print(f'  Model name: {model.model_name}')
        print(f'  Culture: {model.culture}')
        print(f'  Number of tables: {len(model.tables)}')
        if model.desktop_version:
            print(f'  Desktop version: {model.desktop_version}')
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
        'filename',
        help='Path to input TWB file'
    )
    parser.add_argument(
        '--config',
        required=False,
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--output',
        help='Output directory',
        default='output'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = get_default_config()
        if args.config:
            custom_config = load_config(args.config)
            config.update(custom_config)
        # parsed_data = parse_workbook(args.filename, config)
        migrate_to_tmdl(
            args.filename,
            config=config,
            # parsed_data=parsed_data,
            output_dir=args.output
        )
        print("\nMigration completed successfully!")
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise e


if __name__ == '__main__':
    main()
