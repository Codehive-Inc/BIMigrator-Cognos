"""Main entry point for the migration tool."""
import argparse
import io
import json
import logging
from bimigrator.common.log_utils import configure_logging, log_info, log_debug, log_warning, log_error, log_file_generated
import os
import sys
import uuid
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
from bimigrator.parsers.version_parser import VersionParser
from bimigrator.parsers.report_metadata_parser import ReportMetadataParser
from bimigrator.generators.report_metadata_generator import ReportMetadataGenerator
from bimigrator.parsers.report_settings_parser import ReportSettingsParser
from bimigrator.generators.report_settings_generator import ReportSettingsGenerator
from bimigrator.parsers.diagram_layout_parser import DiagramLayoutParser
from bimigrator.generators.diagram_layout_generator import DiagramLayoutGenerator
from bimigrator.parsers.report_parser import ReportParser
from bimigrator.generators.report_generator import ReportGenerator
from bimigrator.parsers.report_config_parser import ReportConfigParser
from bimigrator.generators.report_config_generator import ReportConfigGenerator
from bimigrator.parsers.page_section_parser import PageSectionParser
from bimigrator.parsers.page_config_parser import PageConfigParser
from bimigrator.parsers.page_filters_parser import PageFiltersParser
from bimigrator.generators.page_section_generator import PageSectionGenerator
from bimigrator.generators.page_config_generator import PageConfigGenerator
from bimigrator.generators.page_filters_generator import PageFiltersGenerator
from bimigrator.licensing.license_manager import LicenseManager
from bimigrator.licensing.exceptions import (
    LicenseError, LicenseExpiredError, LicenseLimitError, LicenseConnectionError
)


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)


def get_default_config() -> dict[str, Any]:
    """Retrieves the default config stored inside the config for all cases"""
    config_path = Path(__file__).resolve().parent / 'config' / 'twb-to-pbi.yaml'
    return load_config(str(config_path))


def generate_version_file(filename, config, output_dir):
    version_parser = VersionParser(filename, config)
    version_info = version_parser.extract_version()
    version_generator = VersionGenerator(config, output_dir)
    version_path = version_generator.generate_version(version_info, output_dir)
    return


# Remove these functions as they're now provided by our log_utils module


def migrate_to_tmdl(filename: str | io.BytesIO, output_dir: str = 'output', config: dict[str, Any] = None, skip_license_check: bool = False):
    """Migrate a Tableau workbook to Power BI TMDL format.
    
    Args:
        filename: Path to the Tableau workbook file or BytesIO object
        output_dir: Output directory for the migration
        config: Optional configuration dictionary
        skip_license_check: Whether to skip license validation
        
    Returns:
        Dictionary mapping file types to their generated paths
    """
    # Get workbook name for logging
    if isinstance(filename, (Path, str)):
        twb_name = Path(filename).stem
    else:
        twb_name = Path(getattr(filename, 'name', uuid.uuid4().hex)).stem
    
    # Configure logging with workbook name
    configure_logging(twb_name)
    
    log_info(f"Starting migration for workbook: {twb_name}")
    log_info(f"Output directory: {output_dir}")
    
    # Validate license before proceeding (unless skipped for testing)
    if not skip_license_check:
        try:
            # Get license ID from environment variable or use default
            license_id = os.environ.get('BIMIGRATOR_LICENSE_ID')
            license_id = int(license_id) if license_id else None
            
            # Create license manager and validate license
            license_manager = LicenseManager(license_id)
            license_manager.validate_license()
            
            # Log license status
            license_info = license_manager.get_license_info()
            print(f"\nLicense Status: {license_info['status_message']}")
            print(f"Migrations Remaining: {license_info['migrations_remaining']} of {license_info['max_migrations']}")
            print(f"License Expires: {license_info['expires_at_formatted']} ({license_info['days_remaining']} days remaining)")
            
        except LicenseExpiredError as e:
            print(f"\nERROR: {str(e)}")
            print("Please renew your license to continue using BIMigrator.")
            sys.exit(1)
        except LicenseLimitError as e:
            print(f"\nERROR: {str(e)}")
            print("Please upgrade your license to perform more migrations.")
            sys.exit(1)
        except LicenseConnectionError as e:
            print(f"\nERROR: Unable to connect to license database: {str(e)}")
            print("Please check your database connection settings and try again.")
            print("Required environment variables:")
            print("  BIMIGRATOR_DB_HOST - PostgreSQL host (default: localhost)")
            print("  BIMIGRATOR_DB_PORT - PostgreSQL port (default: 5432)")
            print("  BIMIGRATOR_DB_NAME - PostgreSQL database name (default: bimigrator_db)")
            print("  BIMIGRATOR_DB_USER - PostgreSQL username (default: app_user)")
            print("  BIMIGRATOR_DB_PASSWORD - PostgreSQL password (required)")
            sys.exit(1)
        except LicenseError as e:
            print(f"\nERROR: License validation failed: {str(e)}")
            sys.exit(1)
    
    if not config:
        config = get_default_config()

    # Create output directories
    output_path = Path(output_dir)
    if isinstance(filename, (Path, str)):
        twb_name = Path(filename).stem
    else:
        twb_name = Path(getattr(filename, 'name', uuid.uuid4().hex)).stem

    # Create output directory structure
    structure_generator = ProjectStructureGenerator(config, str(output_path / twb_name))
    structure_generator.create_directory_structure()
    output_dir = structure_generator.base_dir

    # Step 1: Generate version.txt
    print('\nStep 1: Generating version.txt...')
    try:
        version_parser = VersionParser(filename, config, output_dir)
        version_info = version_parser.extract_version()

        version_generator = VersionGenerator(config, output_dir)
        version_path = version_generator.generate_version(version_info, output_dir)
        log_file_generated(str(version_path))
        print(f'Generated version.txt: {version_path}')
    except Exception as e:
        print(f'Failed to generate version.txt: {str(e)}')
        return

    # Step 2: Generate culture TMDL
    print('\nStep 2: Generating culture TMDL...')
    try:
        culture_parser = CultureParser(filename, config, output_dir)
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
            config, twb_name, output_dir,
        )
        # Pass the correct output directory for culture TMDL
        culture_path = culture_generator.generate_culture_tmdl(
            culture_info, output_dir
        )
        log_file_generated(str(culture_path))
        print(f'Generated culture TMDL: {culture_path}')
    except Exception as e:
        print(f'Failed to generate culture TMDL: {str(e)}')
        raise e

    # Step 3: Generate .pbixproj.json
    print('\nStep 3: Generating .pbixproj.json...')
    try:
        from bimigrator.parsers.pbixproj_parser import PbixprojParser
        from bimigrator.generators.pbixproj_generator import PbixprojGenerator
        pbixproj_parser = PbixprojParser(filename, config, output_dir)
        project_info = pbixproj_parser.extract_pbixproj_info()

        pbixproj_generator = PbixprojGenerator(
            config, twb_name, output_dir
        )
        pbixproj_path = pbixproj_generator.generate_pbixproj(project_info, output_dir=structure_generator.base_dir)
        log_file_generated(str(pbixproj_path))
        print(f'Generated .pbixproj.json: {pbixproj_path}')
    except Exception as e:
        print(f'Failed to generate .pbixproj.json: {str(e)}')
        raise e

    # Step 4: Generate database TMDL
    print('\nStep 4: Generating database TMDL...')
    try:
        db_parser = DatabaseParser(filename, config, output_dir)
        db_info = db_parser.extract_database_info()

        database_generator = DatabaseTemplateGenerator(
            config, twb_name, output_dir
        )
        database_path = database_generator.generate_database_tmdl(db_info, output_dir=structure_generator.base_dir)
        log_file_generated(str(database_path))
        print(f'Generated database TMDL: {database_path}')
        print(f'  Database name: {db_info.name}')
    except Exception as e:
        print(f'Failed to generate database TMDL: {str(e)}')
        raise e

    # Step 5: Generate table TMDL files and model TMDL
    print('\nStep 5: Generating table TMDL files...')
    try:
        # Create a single table parser instance to be used by both table and model generation
        table_parser = TableParser(filename, config, str(structure_generator.extracted_dir))
        tables = table_parser.extract_all_tables()

        # Extract relationships first
        relationship_parser = RelationshipParser(filename, config, output_dir)
        relationships = relationship_parser.extract_relationships()

        # Generate table TMDL files
        table_generator = TableTemplateGenerator(
            config, twb_name, output_dir
        )
        # Pass relationships to table generator
        table_paths = table_generator.generate_all_tables(
            tables, 
            relationships=relationships,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated {len(table_paths)} table TMDL files:')
        for path in table_paths:
            print(f'  - {path}')

        # Generate model TMDL using the same tables
        print('\nGenerating model TMDL...')
        model_parser = ModelParser(filename, config, output_dir, table_parser)
        model = model_parser.extract_model_info(tables)

        model_generator = ModelTemplateGenerator(
            config, twb_name, output_dir
        )
        model_path = model_generator.generate_model_tmdl(model, tables, output_dir=structure_generator.base_dir)
        print(f'Generated model TMDL: {model_path}')
        print(f'  Model name: {model.model_name}')
        print(f'  Culture: {model.culture}')
        print(f'  Number of tables: {len(model.tables)}')
        if model.desktop_version:
            print(f'  Desktop version: {model.desktop_version}')
    except Exception as e:
        print(f'Failed to generate table and model TMDL files: {str(e)}')
        raise e

    # Step 6: Generate relationships TMDL
    print('\nStep 6: Generating relationship TMDL files...')
    try:
        print('Debug: Creating relationship parser...')
        relationship_parser = RelationshipParser(filename, config, output_dir)
        print('Debug: Extracting relationships...')
        relationships = relationship_parser.extract_relationships()
        print(f'Debug: Found {len(relationships)} relationships')

        print('Debug: Creating relationship generator...')
        relationship_generator = RelationshipTemplateGenerator(
            config, twb_name, output_dir
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
        raise e

    # Step 7: Generate report metadata
    print('\nStep 7: Generating report metadata...')
    try:
        report_metadata_parser = ReportMetadataParser(filename, config, output_dir)
        report_metadata = report_metadata_parser.extract_metadata()

        report_metadata_generator = ReportMetadataGenerator(
            config,
            twb_name,
            output_dir
        )
        metadata_path = report_metadata_generator.generate_report_metadata(
            report_metadata,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated report metadata: {metadata_path}')
    except Exception as e:
        print(f'Failed to generate report metadata: {str(e)}')
        raise e

    # Step 8: Generate report settings
    print('\nStep 8: Generating report settings...')
    try:
        report_settings_parser = ReportSettingsParser(filename, config, output_dir)
        report_settings = report_settings_parser.extract_report_settings()

        report_settings_generator = ReportSettingsGenerator(
            config,
            twb_name,
            output_dir
        )
        settings_path = report_settings_generator.generate_report_settings(
            report_settings,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated report settings: {settings_path}')
    except Exception as e:
        print(f'Failed to generate report settings: {str(e)}')
        raise e

    # Step 9: Generate diagram layout
    print('\nStep 9: Generating diagram layout...')
    try:
        diagram_layout_parser = DiagramLayoutParser(filename, config, output_dir)
        diagram_layout = diagram_layout_parser.extract_diagram_layout()

        diagram_layout_generator = DiagramLayoutGenerator(
            config,
            twb_name,
            output_dir
        )
        layout_path = diagram_layout_generator.generate_diagram_layout(
            diagram_layout,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated diagram layout: {layout_path}')
    except Exception as e:
        print(f'Failed to generate diagram layout: {str(e)}')
        raise e
        
    # Step 10: Generate report.json
    print('\nStep 10: Generating report.json...')
    try:
        report_parser = ReportParser(filename, config, output_dir)
        report = report_parser.extract_report()

        report_generator = ReportGenerator(
            config,
            twb_name,
            output_dir
        )
        report_path = report_generator.generate_report(
            report,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated report.json: {report_path}')
    except Exception as e:
        print(f'Failed to generate report.json: {str(e)}')
        raise e
        
    # Step 11: Generate report config.json
    print('\nStep 11: Generating report config.json...')
    try:
        report_config_parser = ReportConfigParser(filename, config, output_dir)
        report_config = report_config_parser.extract_report_config()

        report_config_generator = ReportConfigGenerator(
            config,
            twb_name,
            output_dir
        )
        config_path = report_config_generator.generate_report_config(
            report_config,
            output_dir=structure_generator.base_dir
        )
        print(f'Generated report config.json: {config_path}')
    except Exception as e:
        print(f'Failed to generate report config.json: {str(e)}')
        raise e
        
    # Step 12: Generate page section, config, and filters files
    print('\nStep 12: Generating page section, config, and filters files...')
    try:
        # Extract page sections
        page_section_parser = PageSectionParser(filename, config, output_dir)
        page_sections = page_section_parser.extract_all_sections()
        
        # Create generators
        page_section_generator = PageSectionGenerator(config, twb_name, output_dir)
        page_config_generator = PageConfigGenerator(config, twb_name, output_dir)
        page_filters_generator = PageFiltersGenerator(config, twb_name, output_dir)
        
        # Generate files for each section
        for i, section in enumerate(page_sections):
            # Create section directory path
            # Use 'Page 1' format for the directory name
            page_number = i + 1  # Start from 1 instead of 0
            section_dir_name = f"{i:03d}_Page {page_number}"
            section_dir = structure_generator.base_dir / 'Report' / 'sections' / section_dir_name
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Set the pbit_dir for each generator to point to the section directory
            page_section_generator.pbit_dir = section_dir
            page_config_generator.pbit_dir = section_dir
            page_filters_generator.pbit_dir = section_dir
            
            # Update context with section-specific data
            section_context = {
                'name': section.name,
                'display_name': section.display_name,
                'ordinal': i,
                'width': section.layout.width,
                'height': section.layout.height,
                'display_option': 1
            }
            
            # Generate section.json directly in the section directory
            section_path = section_dir / 'section.json'
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(page_section_generator.render_template('page.section.json', section_context))
            print(f'Generated section.json: {section_path}')
            
            # Extract and generate config.json
            page_config_parser = PageConfigParser(filename, config, output_dir)
            page_config = page_config_parser.extract_page_config(section.display_name)
            
            # Generate config.json directly in the section directory
            config_path = section_dir / 'config.json'
            config_context = {
                'visuals': [],
                'layout': {
                    'width': section.layout.width,
                    'height': section.layout.height,
                    'display_option': '1'
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(page_config_generator.render_template('page.config.json', config_context))
            print(f'Generated config.json: {config_path}')
            
            # Extract and generate filters.json
            page_filters_parser = PageFiltersParser(filename, config, output_dir)
            page_filters = page_filters_parser.extract_page_filters(section.display_name)
            
            # Generate filters.json directly in the section directory
            filters_path = section_dir / 'filters.json'
            filters_context = {'filters': page_filters or []}
            with open(filters_path, 'w', encoding='utf-8') as f:
                f.write(page_filters_generator.render_template('page.filters.json', filters_context))
            print(f'Generated filters.json: {filters_path}')
            print(f'Generated filters.json: {filters_path}')
    except Exception as e:
        print(f'Failed to generate page files: {str(e)}')
        print(f'Error details: {e}')
        # Continue with migration even if page files generation fails
        print('Continuing with migration...')

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
    parser.add_argument(
        '--skip-license-check',
        action='store_true',
        help='Skip license validation (for testing only)'
    )
    parser.add_argument(
        '--check-license',
        action='store_true',
        help='Check license status and exit'
    )

    args = parser.parse_args()

    # Configure logging using our custom logging utility
    from bimigrator.common.log_utils import configure_logging, log_info, log_debug, log_warning, log_error, log_file_generated

    configure_logging()

    # Check license status if requested
    if args.check_license:
        try:
            license_id = os.environ.get('BIMIGRATOR_LICENSE_ID')
            license_id = int(license_id) if license_id else None
            
            license_manager = LicenseManager(license_id)
            license_info = license_manager.get_license_info()
            
            print("\nBIMigrator License Status:")
            print(f"Status: {license_info['status_message']}")
            print(f"Migrations Used: {license_info['migrations_used']}")
            print(f"Migrations Remaining: {license_info['migrations_remaining']}")
            print(f"Migration Limit: {license_info['max_migrations']}")
            print(f"License Expires: {license_info['expires_at_formatted']}")
            print(f"Days Remaining: {license_info['days_remaining']}")
            sys.exit(0)
        except Exception as e:
            print(f"\nError checking license: {str(e)}")
            sys.exit(1)

    try:
        # Load configuration
        config = get_default_config()
        if args.config:
            custom_config = load_config(args.config)
            config.update(custom_config)
        migrate_to_tmdl(
            args.filename,
            output_dir=args.output,
            config=config,
            skip_license_check=args.skip_license_check
        )
        print("\nMigration completed successfully!")
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise e


if __name__ == '__main__':
    main()
