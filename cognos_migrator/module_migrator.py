"""
Module-specific migration orchestrator for Cognos to Power BI migration
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from cognos_migrator.config import ConfigManager, MigrationConfig
from cognos_migrator.client import CognosClient
from cognos_migrator.report_parser import CognosReportSpecificationParser
from cognos_migrator.generators.module_generators import ModuleModelFileGenerator, ModuleDocumentationGenerator
from cognos_migrator.models import (
    CognosReport, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
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
        
        # Use module-specific generators
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
            module_info = self.cognos_client.get_module(module_id)
            if not module_info:
                self.logger.error(f"Failed to retrieve module information for {module_id}")
                return {"success": False, "error": "Failed to retrieve module information"}
            
            # Extract module metadata
            module_metadata = self.cognos_client.get_module_metadata(module_id)
            
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
            # Create extracted directory
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            # Save report details
            report_details = {
                "id": cognos_report.id,
                "name": cognos_report.name,
                "module_id": module_info.get("id"),
                "module_name": module_info.get("name")
            }
            
            with open(extracted_dir / "report_details.json", "w") as f:
                json.dump(report_details, f, indent=2)
            
            # Process report using module-specific generators
            # This would be implemented with the module-specific logic
            # For now, we'll just return True
            
            self.logger.info(f"Processed report {cognos_report.name} with module context")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process report with module context: {e}")
            return False


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
