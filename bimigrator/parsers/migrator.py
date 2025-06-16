"""
Main migration orchestrator for Cognos to Power BI migration
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import CognosConfig, MigrationConfig
from .client import CognosClient
from .parsers import CognosReportConverter
from .generators import PowerBIProjectGenerator, DocumentationGenerator
from .models import (
    CognosReport, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
)


class CognosToPowerBIMigrator:
    """Main orchestrator for Cognos to Power BI migration"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.cognos_client = CognosClient(config)
        self.report_converter = CognosReportConverter()
        self.project_generator = PowerBIProjectGenerator(config)
        self.doc_generator = DocumentationGenerator(config)
    
    def migrate_report(self, report_id: str, output_path: str, is_module_migration: bool = False) -> bool:
        """Migrate a single Cognos report to Power BI
        
        Args:
            report_id: ID of the report to migrate
            output_path: Path to store migration output
            is_module_migration: Flag indicating if this is part of a module migration
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting migration of report: {report_id}")
            
            # Step 1: Fetch Cognos report
            cognos_report = self.cognos_client.get_report(report_id)
            if not cognos_report:
                self.logger.error(f"Failed to fetch Cognos report: {report_id}")
                return False
            
            # Step 2: Convert to Power BI structures
            # Pass the is_module_migration flag to the conversion process
            powerbi_project = self._convert_cognos_to_powerbi(cognos_report, is_module_migration)
            if not powerbi_project:
                self.logger.error(f"Failed to convert report: {report_id}")
                return False
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, output_path)
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, output_path)
            
            self.logger.info(f"Successfully migrated report {report_id} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed for report {report_id}: {e}")
            return False
    
    def migrate_multiple_reports(self, report_ids: List[str], output_base_path: str, is_module_migration: bool = False) -> Dict[str, bool]:
        """Migrate multiple Cognos reports
        
        Args:
            report_ids: List of report IDs to migrate
            output_base_path: Base path for migration output
            is_module_migration: Flag indicating if this is part of a module migration
            
        Returns:
            Dict[str, bool]: Results of the migration process
        """
        results = {}
        
        for report_id in report_ids:
            try:
                # Create individual output directory for each report
                report_output_path = Path(output_base_path) / f"report_{report_id}"
                
                # Pass the is_module_migration flag to migrate_report
                success = self.migrate_report(report_id, str(report_output_path), is_module_migration=is_module_migration)
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
    
    def migrate_folder(self, folder_id: str, output_path: str, recursive: bool = True, is_module_migration: bool = False) -> Dict[str, bool]:
        """Migrate all reports in a Cognos folder
        
        Args:
            folder_id: ID of the folder containing reports to migrate
            output_path: Path to store migration output
            recursive: Whether to include reports in subfolders
            is_module_migration: Flag indicating if this is part of a module migration
            
        Returns:
            Dict[str, bool]: Results of the migration process
        """
        try:
            self.logger.info(f"Starting folder migration: {folder_id}")
            
            # Get all reports in folder
            reports = self.cognos_client.list_reports_in_folder(folder_id, recursive)
            if not reports:
                self.logger.warning(f"No reports found in folder: {folder_id}")
                return {}
            
            report_ids = [report.id for report in reports]
            # Pass the is_module_migration flag to migrate_multiple_reports
            return self.migrate_multiple_reports(report_ids, output_path, is_module_migration=is_module_migration)
            
        except Exception as e:
            self.logger.error(f"Failed to migrate folder {folder_id}: {e}")
            return {}
    
    def _convert_cognos_to_powerbi(self, cognos_report: CognosReport, is_module_migration: bool = False) -> Optional[PowerBIProject]:
        """Convert Cognos report to Power BI project structure
        
        Args:
            cognos_report: The Cognos report to convert
            is_module_migration: Flag indicating if this is part of a module migration
            
        Returns:
            Optional[PowerBIProject]: The converted Power BI project, or None if conversion failed
        """
        try:
            # Convert report specification
            converted_data = self.report_converter.convert_report(cognos_report)
            
            # Create data model
            data_model = self._create_data_model(converted_data, cognos_report.name)
            
            # Create report structure
            report = self._create_report_structure(cognos_report, converted_data)
            
            # Create Power BI project
            project = PowerBIProject(
                name=cognos_report.name,
                version="1.0.0",
                created=datetime.now(),
                last_modified=datetime.now(),
                data_model=data_model,
                report=report,
                metadata={
                    "is_module_migration": is_module_migration,
                    "migration_type": "module" if is_module_migration else "standalone"
                }
            )
            
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to convert Cognos report to Power BI: {e}")
            return None
    
    def _create_data_model(self, converted_data: Dict[str, Any], model_name: str) -> DataModel:
        """Create Power BI data model from converted data"""
        # Create tables
        tables = converted_data.get('tables', [])
        
        # Create relationships
        relationships = converted_data.get('relationships', [])
        
        # Create measures
        measures = converted_data.get('measures', [])
        
        data_model = DataModel(
            name=model_name,
            compatibility_level=1600,  # Power BI compatibility level
            culture="en-US",
            tables=tables,
            relationships=relationships,
            measures=measures,
            annotations={
                "PBI_QueryOrder": "[\"Query1\"]",
                "PBIDesktopVersion": "2.120.1085.0 (23.08)",
                "PBI_ProTooling": "[\"DevMode\"]"
            }
        )
        
        return data_model
    
    def _create_report_structure(self, cognos_report: CognosReport, converted_data: Dict[str, Any]) -> Report:
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
            
            # Check template directory
            if not Path(self.config.template_directory).exists():
                self.logger.error(f"Template directory not found: {self.config.template_directory}")
                return False
            
            # Check required templates
            required_templates = ['database.tmdl', 'Table.tmdl', 'pbixproj.json']
            template_dir = Path(self.config.template_directory)
            
            for template in required_templates:
                if not (template_dir / template).exists():
                    self.logger.error(f"Required template not found: {template}")
                    return False
            
            self.logger.info("All migration prerequisites validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate prerequisites: {e}")
            return False
    
    def get_migration_status(self, output_path: str) -> Dict[str, Any]:
        """Get status of migration in output directory"""
        try:
            output_dir = Path(output_path)
            
            if not output_dir.exists():
                return {"status": "not_started", "message": "Output directory does not exist"}
            
            # Check for project file
            project_file = output_dir / '.pbixproj.json'
            if not project_file.exists():
                return {"status": "incomplete", "message": "Project file not found"}
            
            # Check for model files
            model_dir = output_dir / 'Model'
            if not model_dir.exists():
                return {"status": "incomplete", "message": "Model directory not found"}
            
            # Count generated files
            file_count = len(list(output_dir.rglob('*')))
            
            return {
                "status": "completed",
                "message": "Migration appears complete",
                "file_count": file_count,
                "last_modified": datetime.fromtimestamp(output_dir.stat().st_mtime)
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error checking status: {e}"}


class MigrationBatch:
    """Handles batch migration operations"""
    
    def __init__(self, migrator: CognosToPowerBIMigrator):
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
