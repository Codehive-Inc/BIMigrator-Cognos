"""
Module-specific migration orchestrator for Cognos to Power BI migration
"""

import os
import sys
import json
import logging
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime

from cognos_migrator.config import ConfigManager, MigrationConfig
from cognos_migrator.client import CognosClient
from cognos_migrator.report_parser import CognosReportSpecificationParser
from cognos_migrator.generators.modules import ModuleModelFileGenerator, ModuleDocumentationGenerator
from cognos_migrator.extractors.module_extractors import ModuleMetadataExtractor
from cognos_migrator.models import (
    CognosReport, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage,
    VisualType, DataRole, AggregationType
)


class ModuleMigrator:
    """Module-specific migration orchestrator for Cognos to Power BI migration"""
    
    def __init__(self, config: MigrationConfig, logger=None):
        """
        Initialize the module migrator
        
        Args:
            config: Migration configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        self.cognos_client = CognosClient(cognos_config)
        self.report_parser = CognosReportSpecificationParser()
        
        # Use module-specific extractors and generators
        self.metadata_extractor = ModuleMetadataExtractor(self.cognos_client)
        self.model_file_generator = ModuleModelFileGenerator()
        self.doc_generator = ModuleDocumentationGenerator()
        
    def migrate_module(self, module_id: str, folder_id: str, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Migrate a Cognos module to Power BI
        
        Args:
            module_id: ID of the Cognos module to migrate
            folder_id: ID of the folder containing reports to migrate
            output_path: Optional path to store migration output
            
        Returns:
            Dict[str, Any]: Results of the migration
        """
        try:
            self.logger.info(f"Starting module migration for module {module_id}")
            
            # Set output path
            if not output_path:
                output_path = Path(self.config.output_directory) / f"module_{module_id}"
            
            # Create module directory structure
            module_path = Path(output_path)
            module_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            docs_dir = module_path / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            reports_dir = module_path / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            extracted_dir = module_path / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            pbit_dir = module_path / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Extract module metadata
            self.logger.info(f"Step 1: Extracting module metadata for {module_id}")
            module_info, module_metadata = self.metadata_extractor.extract_module_metadata(module_id)
            
            if not module_info:
                self.logger.error(f"Failed to retrieve module information for {module_id}")
                return {"success": False, "error": "Failed to retrieve module information"}
            
            # Save module information in extracted directory
            with open(extracted_dir / "module_info.json", "w") as f:
                json.dump(module_info, f, indent=2)
            
            # Save module metadata in extracted directory
            with open(extracted_dir / "module_metadata.json", "w") as f:
                json.dump(module_metadata, f, indent=2)
            
            # Step 2: Process reports in the folder
            self.logger.info(f"Step 2: Processing reports from folder {folder_id}")
            
            # Get reports in folder
            reports = self.cognos_client.get_folder_reports(folder_id)
            if not reports:
                self.logger.error(f"No reports found in folder {folder_id}")
                return {"success": False, "error": "No reports found in folder"}
            
            # Process each report
            results = {}
            for report in reports:
                report_id = report.get("id")
                report_name = report.get("name", "Unknown")
                
                self.logger.info(f"Processing report: {report_name} ({report_id})")
                
                # Create report directory
                report_dir = reports_dir / f"report_{report_id}"
                report_dir.mkdir(exist_ok=True)
                
                # Extract report
                report_spec = self.cognos_client.get_report_specification(report_id)
                if not report_spec:
                    self.logger.error(f"Failed to extract report specification for {report_id}")
                    results[report_id] = False
                    continue
                
                # Save report specification
                with open(report_dir / "report_spec.xml", "w") as f:
                    f.write(report_spec)
                
                # Parse report
                cognos_report = self.report_parser.parse(report_spec, report_id, report_name)
                if not cognos_report:
                    self.logger.error(f"Failed to parse report {report_id}")
                    results[report_id] = False
                    continue
                
                # Process report with module-specific logic
                success = self._process_report_with_module_context(
                    cognos_report, 
                    report_dir, 
                    module_info, 
                    module_metadata
                )
                
                results[report_id] = success
            
            # Step 3: Generate module-level documentation
            self.logger.info("Step 3: Generating module documentation")
            self.doc_generator.generate_module_documentation(
                module_path,
                module_info,
                module_metadata
            )
            
            # Generate module-level summary
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            summary = {
                "module_id": module_id,
                "folder_id": folder_id,
                "total_reports": total,
                "successful_reports": successful,
                "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
            }
            
            # Save summary in documentation directory
            with open(docs_dir / "module_migration_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Module migration completed: {successful}/{total} reports successful")
            
            return {
                "success": True,
                "results": results,
                "summary": summary
            }
            
        except Exception as e:
            self.logger.error(f"Error during module migration: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_report_with_module_context(
        self, 
        cognos_report: CognosReport, 
        output_dir: Path,
        module_info: Dict[str, Any],
        module_metadata: Dict[str, Any]
    ) -> bool:
        """
        Process a report with module-specific context
        
        Args:
            cognos_report: Parsed Cognos report
            output_dir: Output directory for the report
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing report {cognos_report.name} with module context")
            
            # Create necessary directories
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Save report details with module context
            report_details = {
                "id": cognos_report.id,
                "name": cognos_report.name,
                "module_id": module_info.get("id"),
                "module_name": module_info.get("name"),
                "processed_date": datetime.now().isoformat()
            }
            
            with open(extracted_dir / "report_details.json", "w") as f:
                json.dump(report_details, f, indent=2)
            
            # Step 1: Parse report specification
            parsed_structure = self.report_parser.parse_report_specification(
                cognos_report.specification, 
                cognos_report.metadata
            )
            
            if not parsed_structure:
                self.logger.error(f"Failed to parse report specification for {cognos_report.id}")
                return False
            
            # Save parsed structure for debugging
            with open(extracted_dir / "parsed_structure.json", "w") as f:
                json.dump(parsed_structure.to_dict() if hasattr(parsed_structure, "to_dict") else {"error": "Cannot serialize"}, f, indent=2)
            
            # Step 2: Convert to Power BI project with module context
            powerbi_project = self._convert_to_powerbi_with_module_context(
                cognos_report, 
                parsed_structure, 
                module_info, 
                module_metadata
            )
            
            if not powerbi_project:
                self.logger.error(f"Failed to convert report {cognos_report.id} to Power BI project")
                return False
            
            # Step 3: Generate Power BI files using module-specific generators
            # Create model directory
            model_dir = pbit_dir / "Model"
            model_dir.mkdir(exist_ok=True)
            
            # Generate model files
            self.model_file_generator.generate_model_files(
                powerbi_project.data_model, 
                str(model_dir),
                module_context={
                    "module_id": module_info.get("id"),
                    "module_name": module_info.get("name"),
                    "module_metadata": module_metadata
                }
            )
            
            # Create report directory
            report_dir = pbit_dir / "Report"
            report_dir.mkdir(exist_ok=True)
            
            # Generate report files
            # For now, we'll create a basic report.json file
            report_json = {
                "config": {
                    "version": "1.0",
                    "settings": {
                        "moduleSource": module_info.get("name"),
                        "moduleId": module_info.get("id")
                    }
                },
                "sections": [
                    {
                        "name": "ReportSection",
                        "displayName": f"Module: {module_info.get('name')}",
                        "filters": [],
                        "visualContainers": []
                    }
                ]
            }
            
            with open(report_dir / "report.json", "w") as f:
                json.dump(report_json, f, indent=2)
            
            # Generate report metadata
            report_metadata = {
                "version": "1.0",
                "custom": {
                    "moduleSource": module_info.get("name"),
                    "moduleId": module_info.get("id"),
                    "migratedFrom": "Cognos",
                    "migrationDate": datetime.now().isoformat()
                }
            }
            
            with open(report_dir / "report.metadata.json", "w") as f:
                json.dump(report_metadata, f, indent=2)
            
            # Generate documentation for this report
            docs_dir = output_dir / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Generate a simple report documentation
            with open(docs_dir / "report_documentation.md", "w") as f:
                f.write(f"# Report: {cognos_report.name}\n\n")
                f.write(f"## Module Context\n\n")
                f.write(f"- Module: {module_info.get('name')}\n")
                f.write(f"- Module ID: {module_info.get('id')}\n\n")
                f.write(f"## Migration Details\n\n")
                f.write(f"- Migrated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.logger.info(f"Successfully processed report {cognos_report.name} with module context")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process report with module context: {e}")
            return False
            
    def _convert_to_powerbi_with_module_context(
        self, 
        cognos_report: CognosReport, 
        parsed_structure: Any,
        module_info: Dict[str, Any],
        module_metadata: Dict[str, Any]
    ) -> Optional[PowerBIProject]:
        """
        Convert Cognos report to Power BI project structure with module context
        
        Args:
            cognos_report: Cognos report object
            parsed_structure: Parsed report structure
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            Optional[PowerBIProject]: Power BI project or None if conversion fails
        """
        try:
            # Prepare safe table name - replace spaces with underscores and remove special characters
            import re
            safe_table_name = re.sub(r'[^\w\s]', '', cognos_report.name).replace(' ', '_')
            self.logger.info(f"Using report name '{cognos_report.name}' (sanitized as '{safe_table_name}') for table name")
            
            # Convert parsed structure to migration data
            converted_data = self._convert_parsed_structure_with_module_context(
                parsed_structure, 
                safe_table_name,
                module_info,
                module_metadata
            )
            
            # Create data model with module context
            data_model = self._create_data_model_with_module_context(
                converted_data, 
                cognos_report.name,
                module_info,
                module_metadata
            )
            
            # Create report structure with module context
            report = self._create_report_structure_with_module_context(
                cognos_report, 
                converted_data, 
                data_model,
                module_info,
                module_metadata
            )
            
            # Create Power BI project with module context
            project = PowerBIProject(
                name=f"{module_info.get('name')} - {cognos_report.name}",
                version="1.0",
                created=datetime.now(),
                last_modified=datetime.now(),
                data_model=data_model,
                report=report,
                metadata={
                    "module_id": module_info.get("id"),
                    "module_name": module_info.get("name"),
                    "report_id": cognos_report.id,
                    "report_name": cognos_report.name
                }
            )
            
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to convert report to Power BI with module context: {e}")
            return None
            
    def _convert_parsed_structure_with_module_context(
        self, 
        parsed_structure: Any, 
        safe_table_name: str,
        module_info: Dict[str, Any],
        module_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert parsed Cognos structure to migration data format with module context
        
        Args:
            parsed_structure: Parsed report structure
            safe_table_name: Sanitized table name
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            Dict[str, Any]: Converted data structure
        """
        try:
            # Extract basic information
            converted_data = {
                'tables': [],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': [],
                'module_context': {
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name')
                }
            }
            
            # Convert pages if available
            if hasattr(parsed_structure, 'pages') and parsed_structure.pages:
                for page in parsed_structure.pages:
                    page_data = {
                        'name': page.name,
                        'visuals': []
                    }
                    
                    # Convert visuals if available
                    if hasattr(page, 'visuals') and page.visuals:
                        for visual in page.visuals:
                            visual_data = {
                                'name': visual.name,
                                'type': visual.cognos_type,
                                'powerbi_type': visual.power_bi_type.value if hasattr(visual, 'power_bi_type') and visual.power_bi_type else 'textbox',
                                'position': visual.position if hasattr(visual, 'position') else {},
                                'fields': []
                            }
                            
                            # Convert fields if available
                            if hasattr(visual, 'fields') and visual.fields:
                                for field in visual.fields:
                                    field_data = {
                                        'name': field.name,
                                        'source_table': field.source_table if hasattr(field, 'source_table') else safe_table_name,
                                        'data_role': field.data_role if hasattr(field, 'data_role') else 'Dimension',
                                        'aggregation': field.aggregation if hasattr(field, 'aggregation') else 'None'
                                    }
                                    visual_data['fields'].append(field_data)
                            
                            page_data['visuals'].append(visual_data)
                    
                    converted_data['pages'].append(page_data)
            
            # Convert data sources to tables
            if hasattr(parsed_structure, 'data_sources') and parsed_structure.data_sources:
                for ds in parsed_structure.data_sources:
                    table_data = {
                        'name': ds.name if hasattr(ds, 'name') else safe_table_name,
                        'columns': [],
                        'source_type': ds.source_type if hasattr(ds, 'source_type') else 'Unknown',
                        'module_source': module_info.get('name')
                    }
                    
                    # Add columns if available
                    if hasattr(ds, 'columns') and ds.columns:
                        for col in ds.columns:
                            column_data = {
                                'name': col.name if hasattr(col, 'name') else 'Unknown',
                                'data_type': col.data_type if hasattr(col, 'data_type') else 'String',
                                'source_column': col.source_column if hasattr(col, 'source_column') else col.name if hasattr(col, 'name') else 'Unknown'
                            }
                            table_data['columns'].append(column_data)
                    
                    converted_data['tables'].append(table_data)
            
            # If no specific structure, create basic defaults with module context
            if not converted_data['tables']:
                self.logger.info(f"Using safe table name '{safe_table_name}' for default table with module context")
                converted_data['tables'].append({
                    'name': safe_table_name,
                    'columns': [
                        {'name': 'ID', 'data_type': 'Int64', 'source_column': 'ID'},
                        {'name': 'Value', 'data_type': 'String', 'source_column': 'Value'}
                    ],
                    'source_type': 'Module',
                    'module_source': module_info.get('name')
                })
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"Failed to convert parsed structure with module context: {e}")
            # Return basic structure to avoid errors
            return {
                'tables': [{
                    'name': safe_table_name,
                    'columns': [
                        {'name': 'ID', 'data_type': 'Int64', 'source_column': 'ID'},
                        {'name': 'Value', 'data_type': 'String', 'source_column': 'Value'}
                    ],
                    'source_type': 'Module',
                    'module_source': module_info.get('name')
                }],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': [],
                'module_context': {
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name')
                }
            }
            
    def _create_data_model_with_module_context(
        self, 
        converted_data: Dict[str, Any], 
        model_name: str,
        module_info: Dict[str, Any],
        module_metadata: Dict[str, Any]
    ) -> DataModel:
        """
        Create Power BI data model from converted data with module context
        
        Args:
            converted_data: Converted data structure
            model_name: Name for the model
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            DataModel: Power BI data model
        """
        try:
            # Create tables
            tables = []
            for table_data in converted_data.get('tables', []):
                columns = []
                for col_data in table_data.get('columns', []):
                    column = Column(
                        name=col_data.get('name', 'Unknown'),
                        data_type=col_data.get('data_type', 'String'),
                        source_column=col_data.get('source_column', col_data.get('name', 'Unknown'))
                    )
                    columns.append(column)
                
                # Create table with module context
                table = Table(
                    name=table_data.get('name', 'Unknown'),
                    columns=columns,
                    source_type=table_data.get('source_type', 'Unknown'),
                    module_source=module_info.get('name', 'Unknown Module'),
                    module_id=module_info.get('id', 'Unknown')
                )
                tables.append(table)
            
            # Create relationships
            relationships = []
            for rel_data in converted_data.get('relationships', []):
                relationship = Relationship(
                    from_table=rel_data.get('from_table', ''),
                    from_column=rel_data.get('from_column', ''),
                    to_table=rel_data.get('to_table', ''),
                    to_column=rel_data.get('to_column', ''),
                    type=rel_data.get('type', 'OneToMany')
                )
                relationships.append(relationship)
            
            # Create measures
            measures = []
            for measure_data in converted_data.get('measures', []):
                measure = Measure(
                    name=measure_data.get('name', 'Unknown'),
                    expression=measure_data.get('expression', 'BLANK()'),
                    table=measure_data.get('table', tables[0].name if tables else 'Unknown')
                )
                measures.append(measure)
            
            # Create data model with module context
            data_model = DataModel(
                name=f"{module_info.get('name')} - {model_name}",
                tables=tables,
                relationships=relationships,
                measures=measures,
                metadata={
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name'),
                    'module_type': module_metadata.get('type', 'Unknown')
                }
            )
            
            return data_model
            
        except Exception as e:
            self.logger.error(f"Failed to create data model with module context: {e}")
            # Create a minimal data model to avoid errors
            table = Table(
                name="DefaultTable",
                columns=[
                    Column(name="ID", data_type="Int64", source_column="ID"),
                    Column(name="Value", data_type="String", source_column="Value")
                ],
                source_type="Module",
                module_source=module_info.get('name', 'Unknown Module'),
                module_id=module_info.get('id', 'Unknown')
            )
            
            return DataModel(
                name=f"{module_info.get('name')} - {model_name}",
                tables=[table],
                relationships=[],
                measures=[],
                metadata={
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name'),
                    'module_type': module_metadata.get('type', 'Unknown')
                }
            )
            
    def _create_report_structure_with_module_context(
        self, 
        cognos_report: CognosReport, 
        converted_data: Dict[str, Any], 
        data_model: DataModel,
        module_info: Dict[str, Any],
        module_metadata: Dict[str, Any]
    ) -> Report:
        """
        Create Power BI report structure with module context
        
        Args:
            cognos_report: Cognos report object
            converted_data: Converted data structure
            data_model: Power BI data model
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            Report: Power BI report structure
        """
        try:
            # Create report pages
            pages = []
            
            # Use converted pages if available
            if converted_data.get('pages'):
                for page_data in converted_data.get('pages', []):
                    page = ReportPage(
                        name=page_data.get('name', 'Default'),
                        visuals=page_data.get('visuals', [])
                    )
                    pages.append(page)
            else:
                # Create default page with module context
                default_page = ReportPage(
                    name="ReportPage",
                    visuals=[{
                        'name': 'Title',
                        'type': 'textbox',
                        'powerbi_type': 'textbox',
                        'position': {'x': 0, 'y': 0, 'width': 800, 'height': 100},
                        'properties': {
                            'text': f"Module: {module_info.get('name')}\nReport: {cognos_report.name}"
                        }
                    }]
                )
                pages.append(default_page)
            
            # Create report with module context
            report = Report(
                name=f"{module_info.get('name')} - {cognos_report.name}",
                pages=pages,
                metadata={
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name'),
                    'report_id': cognos_report.id,
                    'report_name': cognos_report.name
                }
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to create report structure with module context: {e}")
            # Create a minimal report to avoid errors
            default_page = ReportPage(
                name="ReportPage",
                visuals=[{
                    'name': 'Title',
                    'type': 'textbox',
                    'powerbi_type': 'textbox',
                    'position': {'x': 0, 'y': 0, 'width': 800, 'height': 100},
                    'properties': {
                        'text': f"Module: {module_info.get('name')}\nReport: {cognos_report.name}"
                    }
                }]
            )
            
            return Report(
                name=f"{module_info.get('name')} - {cognos_report.name}",
                pages=[default_page],
                metadata={
                    'module_id': module_info.get('id'),
                    'module_name': module_info.get('name'),
                    'report_id': cognos_report.id,
                    'report_name': cognos_report.name
                }
            )


# Add a command-line entry point
def migrate_module_cli():
    """Command-line entry point for module migration"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    if len(sys.argv) < 3:
        logger.error("Usage: python -m cognos_migrator.module_migrator <module_id> <folder_id> [output_path]")
        return
    
    module_id = sys.argv[1]
    folder_id = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_migration_config()
    
    # Initialize migrator
    migrator = ModuleMigrator(config)
    
    # Migrate module
    result = migrator.migrate_module(module_id, folder_id, output_path)
    
    if result.get("success"):
        logger.info("Module migration completed successfully")
    else:
        logger.error(f"Module migration failed: {result.get('error')}")


if __name__ == "__main__":
    migrate_module_cli()
