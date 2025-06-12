"""
Main migration orchestrator for Cognos to Power BI migration
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import CognosConfig, MigrationConfig, ConfigManager
from .client import CognosClient
from .report_parser import CognosReportSpecificationParser
from .generators import PowerBIProjectGenerator, DocumentationGenerator
from .models import (
    CognosReport, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
)


class CognosMigrator:
    """Main orchestrator for Cognos to Power BI migration"""
    
    def __init__(self, config: MigrationConfig, base_url: str = None, session_key: str = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        self.cognos_client = CognosClient(cognos_config, base_url, session_key)
        self.report_parser = CognosReportSpecificationParser()
        self.project_generator = PowerBIProjectGenerator(config)
        self.doc_generator = DocumentationGenerator(config)
    
    def migrate_report(self, report_id: str, output_path: str) -> bool:
        """Migrate a single Cognos report to Power BI"""
        try:
            self.logger.info(f"Starting migration of report: {report_id}")
            
            # Create output directory structure
            from pathlib import Path
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create extracted directory for raw extracted data
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            # Create pbit directory for pbitools files
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Fetch Cognos report
            cognos_report = self.cognos_client.get_report(report_id)
            if not cognos_report:
                self.logger.error(f"Failed to fetch Cognos report: {report_id}")
                return False
            
            # Save raw Cognos report data to extracted folder
            self._save_extracted_data(cognos_report, extracted_dir)
            
            # Step 2: Convert to Power BI structures
            powerbi_project = self._convert_cognos_to_powerbi(cognos_report)
            if not powerbi_project:
                self.logger.error(f"Failed to convert report: {report_id}")
                return False
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, str(extracted_dir))
            
            self.logger.info(f"Successfully migrated report {report_id} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed for report {report_id}: {e}")
            return False
    
    def migrate_multiple_reports(self, report_ids: List[str], output_base_path: str) -> Dict[str, bool]:
        """Migrate multiple Cognos reports"""
        results = {}
        
        for report_id in report_ids:
            try:
                # Create individual output directory for each report
                report_output_path = Path(output_base_path) / f"report_{report_id}"
                
                success = self.migrate_report(report_id, str(report_output_path))
                results[report_id] = success
                
                if success:
                    self.logger.info(f"✓ Successfully migrated report: {report_id}")
                else:
                    self.logger.error(f"✗ Failed to migrate report: {report_id}")
                    
            except Exception as e:
                self.logger.error(f"Error migrating report {report_id}: {e}")
                results[report_id] = False
        
        # Generate summary report
        self._generate_migration_summary(results, output_base_path)
        
        return results
    
    def migrate_folder(self, folder_id: str, output_path: str, recursive: bool = True) -> Dict[str, bool]:
        """Migrate all reports in a Cognos folder"""
        try:
            self.logger.info(f"Starting folder migration: {folder_id}")
            
            # Get all reports in folder
            reports = self.cognos_client.list_reports_in_folder(folder_id, recursive)
            if not reports:
                self.logger.warning(f"No reports found in folder: {folder_id}")
                return {}
            
            report_ids = [report.id for report in reports]
            return self.migrate_multiple_reports(report_ids, output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to migrate folder {folder_id}: {e}")
            return {}
    
    def _convert_cognos_to_powerbi(self, cognos_report: CognosReport) -> Optional[PowerBIProject]:
        """Convert Cognos report to Power BI project structure"""
        try:
            # Parse report specification
            parsed_structure = self.report_parser.parse_report_specification(
                cognos_report.specification, 
                cognos_report.metadata
            )
            
            # Convert parsed structure to migration data
            converted_data = self._convert_parsed_structure(parsed_structure)
            
            # Create data model
            data_model = self._create_data_model(converted_data, cognos_report.name)
            
            # Create report structure
            report = self._create_report_structure(cognos_report, converted_data, data_model)
            
            # Create Power BI project
            project = PowerBIProject(
                name=cognos_report.name,
                version="1.0",  # Match the version format in example files
                created=datetime.now(),
                last_modified=datetime.now(),
                data_model=data_model,
                report=report
            )
            
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to convert Cognos report to Power BI: {e}")
            return None
    
    def _convert_parsed_structure(self, parsed_structure) -> Dict[str, Any]:
        """Convert parsed Cognos structure to migration data format"""
        try:
            # Extract basic information
            converted_data = {
                'tables': [],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': []
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
                                'powerbi_type': visual.power_bi_type.value if visual.power_bi_type else 'textbox',
                                'position': visual.position,
                                'fields': []
                            }
                            
                            # Convert fields if available
                            if hasattr(visual, 'fields') and visual.fields:
                                for field in visual.fields:
                                    field_data = {
                                        'name': field.name,
                                        'source_table': field.source_table,
                                        'data_role': field.data_role,
                                        'aggregation': field.aggregation
                                    }
                                    visual_data['fields'].append(field_data)
                            
                            page_data['visuals'].append(visual_data)
                    
                    converted_data['pages'].append(page_data)
            
            # Convert data sources to tables
            if hasattr(parsed_structure, 'data_sources') and parsed_structure.data_sources:
                for ds in parsed_structure.data_sources:
                    table_data = {
                        'name': ds.name,
                        'columns': [],
                        'source_type': ds.source_type if hasattr(ds, 'source_type') else 'Unknown'
                    }
                    converted_data['tables'].append(table_data)
            
            # If no specific structure, create basic defaults
            if not converted_data['tables']:
                converted_data['tables'].append({
                    'name': 'Data',
                    'columns': [
                        {'name': 'ID', 'type': 'Int64'},
                        {'name': 'Name', 'type': 'Text'},
                        {'name': 'Value', 'type': 'Decimal'}
                    ],
                    'source_type': 'Cognos'
                })
            
            return converted_data
            
        except Exception as e:
            self.logger.warning(f"Error converting parsed structure: {e}")
            # Return minimal structure as fallback
            return {
                'tables': [{
                    'name': 'Data',
                    'columns': [
                        {'name': 'ID', 'type': 'Int64'},
                        {'name': 'Value', 'type': 'Decimal'}
                    ],
                    'source_type': 'Cognos'
                }],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': []
            }
    
    def _create_data_model(self, converted_data: Dict[str, Any], model_name: str) -> DataModel:
        """Create Power BI data model from converted data"""
        from .models import Table, Column, Relationship, Measure, DataType
        
        # Create tables from converted data
        tables = []
        for table_data in converted_data.get('tables', []):
            # Create columns
            columns = []
            for col_data in table_data.get('columns', []):
                column = Column(
                    name=col_data.get('name', 'Column'),
                    data_type=DataType.STRING if col_data.get('type') == 'Text' else DataType.INTEGER,
                    source_column=col_data.get('name', 'Column'),
                    format_string=col_data.get('format_string')
                )
                columns.append(column)
            
            # Create table
            table = Table(
                name=table_data.get('name', 'Table'),
                columns=columns,
                source_query=f"let Source = {table_data.get('source_type', 'Cognos')} in Source"
            )
            tables.append(table)
        
        # Create relationships (basic implementation)
        relationships = []
        for rel_data in converted_data.get('relationships', []):
            relationship = Relationship(
                from_table=rel_data.get('from_table', ''),
                from_column=rel_data.get('from_column', ''),
                to_table=rel_data.get('to_table', ''),
                to_column=rel_data.get('to_column', ''),
                cardinality=rel_data.get('cardinality', 'OneToMany')
            )
            relationships.append(relationship)
        
        # Create measures
        measures = []
        for measure_data in converted_data.get('measures', []):
            measure = Measure(
                name=measure_data.get('name', 'Measure'),
                expression=measure_data.get('expression', 'SUM(Table[Column])'),
                format_string=measure_data.get('format_string'),
                description=measure_data.get('description')
            )
            measures.append(measure)
        
        data_model = DataModel(
            name=model_name,
            compatibility_level=1567,  # Match example file compatibility level
            culture="en-US",
            tables=tables,
            relationships=relationships,
            measures=measures,
            annotations={
                "PBI_QueryOrder": "[\"Query1\"]",
                "PBIDesktopVersion": "2.142.928.0 (25.04)+de52df9f0bb74ad93a80d89c52d63fe6d07e0e1b",  # Use newer version from Sales Dashboard example
                "__PBI_TimeIntelligenceEnabled": "0"  # Match example file setting
            }
        )
        
        return data_model
    
    def _create_report_structure(self, cognos_report: CognosReport, converted_data: Dict[str, Any], data_model: DataModel) -> Report:
        """Create Power BI report structure"""
        # Create basic report page
        page = ReportPage(
            name="Page1",
            display_name="Report Page",
            width=1280,
            height=720,
            visuals=[],  # Would be populated with actual visuals
            filters=converted_data.get('filters', []),
            config={}
        )
        
        report = Report(
            name=cognos_report.name,
            pages=[page],
            data_model=data_model,
            config={
                "theme": "CorporateTheme",
                "settings": {}
            },
            settings={}
        )
        
        return report
    
    def _generate_migration_summary(self, results: Dict[str, bool], output_path: str):
        """Generate migration summary report"""
        try:
            summary_path = Path(output_path) / "migration_summary.md"
            
            total_reports = len(results)
            successful_reports = sum(1 for success in results.values() if success)
            failed_reports = total_reports - successful_reports
            
            summary_content = f"""# Migration Summary Report

## Overview
- **Total Reports**: {total_reports}
- **Successful Migrations**: {successful_reports}
- **Failed Migrations**: {failed_reports}
- **Success Rate**: {(successful_reports/total_reports*100):.1f}%

## Migration Results

### Successful Migrations
"""
            
            for report_id, success in results.items():
                if success:
                    summary_content += f"- ✓ {report_id}\n"
            
            summary_content += "\n### Failed Migrations\n"
            
            for report_id, success in results.items():
                if not success:
                    summary_content += f"- ✗ {report_id}\n"
            
            summary_content += f"""
## Migration Details
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Output Directory**: {output_path}

## Next Steps
1. Review failed migrations and check logs for error details
2. Validate successful migrations by opening in Power BI Desktop
3. Test data connections and refresh capabilities
4. Review and adjust visual layouts as needed
"""
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            self.logger.info(f"Generated migration summary: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration summary: {e}")
    
    def validate_migration_prerequisites(self) -> bool:
        """Validate that all prerequisites for migration are met"""
        try:
            # Check Cognos connection
            if not self.cognos_client.test_connection():
                self.logger.error("Cannot connect to Cognos Analytics")
                return False
            
            # Check template directory - use the path from config
            template_dir_from_config = self.config.template_directory
            self.logger.info(f"Template directory from config: {template_dir_from_config}")
            
            # Try different ways to resolve the template directory
            project_root = Path(__file__).parent.parent
            template_paths = [
                Path(template_dir_from_config),  # Absolute path
                project_root / template_dir_from_config,  # Relative to project root
            ]
            
            # Find the first path that exists
            template_dir = None
            for path in template_paths:
                self.logger.info(f"Checking template path: {path}, exists: {path.exists()}")
                if path.exists():
                    template_dir = path
                    break
            
            if not template_dir:
                self.logger.error(f"Template directory not found: {template_dir_from_config}")
                return False
            
            # Update config with the resolved absolute path
            self.config.template_directory = str(template_dir)
            self.logger.info(f"Using template directory: {self.config.template_directory}")
            
            
            # Check required templates
            required_templates = ['database.tmdl', 'Table.tmdl', 'pbixproj.json']
            
            for template in required_templates:
                if not (template_dir / template).exists():
                    self.logger.error(f"Required template not found: {template}")
                    return False
            
            self.logger.info("All migration prerequisites validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate prerequisites: {e}")
            return False
    
    def _save_extracted_data(self, cognos_report, extracted_dir):
        """Save raw Cognos report data to the extracted folder"""
        try:
            import json
            from pathlib import Path
            
            # Save report specification
            if hasattr(cognos_report, 'specification') and cognos_report.specification:
                spec_file = Path(extracted_dir) / 'report_specification.xml'
                with open(spec_file, 'w', encoding='utf-8') as f:
                    f.write(cognos_report.specification)
            
            # Save report metadata
            if hasattr(cognos_report, 'metadata') and cognos_report.metadata:
                metadata_file = Path(extracted_dir) / 'report_metadata.json'
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(cognos_report.metadata, f, indent=2)
            
            # Save report details
            report_details = {
                'id': cognos_report.id,
                'name': cognos_report.name,
                'path': cognos_report.path if hasattr(cognos_report, 'path') else None,
                'type': cognos_report.type if hasattr(cognos_report, 'type') else None,
                'created': str(cognos_report.created) if hasattr(cognos_report, 'created') else None,
                'modified': str(cognos_report.modified) if hasattr(cognos_report, 'modified') else None
            }
            
            details_file = Path(extracted_dir) / 'report_details.json'
            with open(details_file, 'w', encoding='utf-8') as f:
                json.dump(report_details, f, indent=2)
                
            self.logger.info(f"Saved extracted Cognos report data to {extracted_dir}")
        except Exception as e:
            self.logger.error(f"Failed to save extracted data: {e}")
    
    def get_migration_status(self, output_path: str) -> Dict[str, Any]:
        """Get status of migration in output directory"""
        status = {
            'status': 'unknown',
            'message': '',
            'file_count': 0,
            'last_modified': None
        }
        
        try:
            path = Path(output_path)
            if not path.exists():
                status['status'] = 'not_started'
                status['message'] = 'Output directory does not exist'
                return status
            
            # Count files
            file_count = sum(1 for _ in path.glob('**/*') if _.is_file())
            status['file_count'] = file_count
            
            # Get last modified time
            if file_count > 0:
                last_modified = max(_.stat().st_mtime for _ in path.glob('**/*') if _.is_file())
                status['last_modified'] = datetime.fromtimestamp(last_modified)
            
            # Determine status
            if file_count == 0:
                status['status'] = 'empty'
                status['message'] = 'Output directory is empty'
            elif path.joinpath('pbit/.pbixproj.json').exists() or path.joinpath('.pbixproj.json').exists():
                status['status'] = 'completed'
                status['message'] = 'Migration appears complete'
            else:
                status['status'] = 'in_progress'
                status['message'] = 'Migration in progress'
            
            return status
            
        except Exception as e:
            return {"status": "error", "message": f"Error checking status: {e}"}


class MigrationBatch:
    """Handles batch migration operations"""
    
    def __init__(self, migrator: CognosMigrator):
        self.migrator = migrator
        self.logger = logging.getLogger(__name__)
    
    def create_migration_plan(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a migration plan from source configuration"""
        plan = {
            "migration_id": f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created": datetime.now().isoformat(),
            "source": source_config,
            "reports": [],
            "estimated_duration": "Unknown"
        }
        
        # Add reports based on source configuration
        if "report_ids" in source_config:
            plan["reports"] = [{"id": rid, "type": "individual"} for rid in source_config["report_ids"]]
        
        if "folder_ids" in source_config:
            for folder_id in source_config["folder_ids"]:
                reports = self.migrator.cognos_client.list_reports_in_folder(folder_id)
                for report in reports:
                    plan["reports"].append({"id": report.id, "type": "folder", "folder": folder_id})
        
        # Estimate duration (rough calculation)
        report_count = len(plan["reports"])
        estimated_minutes = report_count * 2  # Assume 2 minutes per report
        plan["estimated_duration"] = f"{estimated_minutes} minutes"
        
        return plan
    
    def execute_migration_plan(self, plan: Dict[str, Any], output_base_path: str) -> Dict[str, Any]:
        """Execute a migration plan"""
        self.logger.info(f"Executing migration plan: {plan['migration_id']}")
        
        results = {
            "plan_id": plan["migration_id"],
            "started": datetime.now().isoformat(),
            "completed": None,
            "total_reports": len(plan["reports"]),
            "successful": 0,
            "failed": 0,
            "results": {}
        }
        
        try:
            for report_info in plan["reports"]:
                report_id = report_info["id"]
                report_output_path = Path(output_base_path) / f"report_{report_id}"
                
                success = self.migrator.migrate_report(report_id, str(report_output_path))
                results["results"][report_id] = success
                
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            
            results["completed"] = datetime.now().isoformat()
            
            # Save execution results
            results_file = Path(output_base_path) / f"{plan['migration_id']}_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Migration plan completed: {results['successful']}/{results['total_reports']} successful")
            
        except Exception as e:
            self.logger.error(f"Migration plan execution failed: {e}")
            results["error"] = str(e)
        
        return results


# Legacy alias for backward compatibility
CognosToPowerBIMigrator = CognosMigrator
