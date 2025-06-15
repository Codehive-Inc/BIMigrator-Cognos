"""
Module processor for Cognos to Power BI migration
Handles post-processing of module-based migrations
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class ModuleProcessor:
    """
    Handles post-processing of module-based migrations
    Enhances generated Power BI files with module-specific information
    """
    
    def __init__(self, module_path: str):
        """
        Initialize the module processor
        
        Args:
            module_path: Path to the module output directory
        """
        self.module_path = Path(module_path)
        self.logger = logging.getLogger(__name__)
        self.module_info = None
        self.module_metadata = None
        
    def load_module_info(self) -> bool:
        """
        Load module information from the module_info.json file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            module_info_path = self.module_path / "module_info.json"
            if not module_info_path.exists():
                self.logger.error(f"Module info file not found: {module_info_path}")
                return False
                
            with open(module_info_path, "r") as f:
                self.module_info = json.load(f)
                
            module_metadata_path = self.module_path / "module_metadata.json"
            if module_metadata_path.exists():
                with open(module_metadata_path, "r") as f:
                    self.module_metadata = json.load(f)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load module info: {e}")
            return False
            
    def process_report_files(self) -> bool:
        """
        Process all report files in the module's reports directory
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            reports_path = self.module_path / "reports"
            if not reports_path.exists() or not reports_path.is_dir():
                self.logger.error(f"Reports directory not found: {reports_path}")
                return False
                
            # Find all report directories
            report_dirs = [d for d in reports_path.iterdir() if d.is_dir() and d.name.startswith("report_")]
            
            for report_dir in report_dirs:
                self.process_single_report(report_dir)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process report files: {e}")
            return False
            
    def process_single_report(self, report_dir: Path) -> bool:
        """
        Process a single report directory
        
        Args:
            report_dir: Path to the report directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            report_id = report_dir.name.replace("report_", "")
            self.logger.info(f"Processing report: {report_id}")
            
            # Process Power BI project files
            pbit_dir = report_dir / "pbit"
            if not pbit_dir.exists():
                self.logger.warning(f"PBIT directory not found for report: {report_id}")
                return False
                
            # Process model files
            model_dir = pbit_dir / "Model"
            if model_dir.exists():
                self.enhance_model_files(model_dir, report_id)
                
            # Process report files
            report_files_dir = pbit_dir / "Report"
            if report_files_dir.exists():
                self.enhance_report_files(report_files_dir, report_id)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process report {report_dir.name}: {e}")
            return False
            
    def enhance_model_files(self, model_dir: Path, report_id: str) -> None:
        """
        Enhance Power BI model files with module information
        
        Args:
            model_dir: Path to the model directory
            report_id: ID of the report
        """
        try:
            # Enhance model.tmdl
            model_file = model_dir / "model.tmdl"
            if model_file.exists():
                self._enhance_model_file(model_file)
                
            # Enhance database.tmdl if exists
            database_file = model_dir / "database.tmdl"
            if database_file.exists():
                self._enhance_database_file(database_file)
                
            # Process tables
            tables_dir = model_dir / "tables"
            if tables_dir.exists():
                for table_file in tables_dir.glob("*.tmdl"):
                    self._enhance_table_file(table_file)
                    
        except Exception as e:
            self.logger.error(f"Failed to enhance model files for report {report_id}: {e}")
            
    def enhance_report_files(self, report_dir: Path, report_id: str) -> None:
        """
        Enhance Power BI report files with module information
        
        Args:
            report_dir: Path to the report directory
            report_id: ID of the report
        """
        try:
            # Enhance report.json
            report_file = report_dir / "report.json"
            if report_file.exists():
                self._enhance_report_file(report_file)
                
            # Enhance report metadata
            metadata_file = report_dir / "report.metadata.json"
            if metadata_file.exists():
                self._enhance_report_metadata(metadata_file)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance report files for report {report_id}: {e}")
            
    def _enhance_model_file(self, model_file: Path) -> None:
        """
        Enhance the model.tmdl file with module information
        
        Args:
            model_file: Path to the model.tmdl file
        """
        try:
            with open(model_file, "r") as f:
                model_data = json.load(f)
                
            # Add module information to model annotations
            if self.module_info and "annotations" in model_data:
                module_name = self.module_info.get("name", "Unknown Module")
                model_data["annotations"]["ModuleSource"] = module_name
                model_data["annotations"]["ModuleId"] = self.module_info.get("id", "")
                
                # Add module description if available
                if self.module_metadata and "description" in self.module_metadata:
                    model_data["annotations"]["ModuleDescription"] = self.module_metadata["description"]
                    
            # Write back enhanced model
            with open(model_file, "w") as f:
                json.dump(model_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance model file {model_file}: {e}")
            
    def _enhance_database_file(self, database_file: Path) -> None:
        """
        Enhance the database.tmdl file with module information
        
        Args:
            database_file: Path to the database.tmdl file
        """
        try:
            with open(database_file, "r") as f:
                database_data = json.load(f)
                
            # Add module information to database
            if self.module_info and "annotations" in database_data:
                module_name = self.module_info.get("name", "Unknown Module")
                database_data["annotations"]["ModuleSource"] = module_name
                
            # Write back enhanced database
            with open(database_file, "w") as f:
                json.dump(database_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance database file {database_file}: {e}")
            
    def _enhance_table_file(self, table_file: Path) -> None:
        """
        Enhance a table.tmdl file with module information
        
        Args:
            table_file: Path to the table.tmdl file
        """
        try:
            with open(table_file, "r") as f:
                table_data = json.load(f)
                
            # Add module information to table annotations
            if self.module_info and "annotations" in table_data:
                module_name = self.module_info.get("name", "Unknown Module")
                table_data["annotations"]["ModuleSource"] = module_name
                
            # Write back enhanced table
            with open(table_file, "w") as f:
                json.dump(table_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance table file {table_file}: {e}")
            
    def _enhance_report_file(self, report_file: Path) -> None:
        """
        Enhance the report.json file with module information
        
        Args:
            report_file: Path to the report.json file
        """
        try:
            with open(report_file, "r") as f:
                report_data = json.load(f)
                
            # Add module information to report
            if self.module_info and "config" in report_data:
                if "settings" not in report_data["config"]:
                    report_data["config"]["settings"] = {}
                    
                module_name = self.module_info.get("name", "Unknown Module")
                report_data["config"]["settings"]["moduleSource"] = module_name
                report_data["config"]["settings"]["moduleId"] = self.module_info.get("id", "")
                
            # Write back enhanced report
            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance report file {report_file}: {e}")
            
    def _enhance_report_metadata(self, metadata_file: Path) -> None:
        """
        Enhance the report.metadata.json file with module information
        
        Args:
            metadata_file: Path to the report.metadata.json file
        """
        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                
            # Add module information to metadata
            if self.module_info:
                if "custom" not in metadata:
                    metadata["custom"] = {}
                    
                module_name = self.module_info.get("name", "Unknown Module")
                metadata["custom"]["moduleSource"] = module_name
                metadata["custom"]["moduleId"] = self.module_info.get("id", "")
                
                # Add module description if available
                if self.module_metadata and "description" in self.module_metadata:
                    metadata["custom"]["moduleDescription"] = self.module_metadata["description"]
                    
            # Write back enhanced metadata
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to enhance metadata file {metadata_file}: {e}")
            
    def generate_module_documentation(self) -> bool:
        """
        Generate comprehensive documentation for the module migration
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create documentation directory
            docs_dir = self.module_path / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Generate module overview document
            self._generate_module_overview(docs_dir)
            
            # Generate report mapping document
            self._generate_report_mapping(docs_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate module documentation: {e}")
            return False
            
    def _generate_module_overview(self, docs_dir: Path) -> None:
        """
        Generate module overview documentation
        
        Args:
            docs_dir: Path to the documentation directory
        """
        try:
            if not self.module_info:
                self.logger.warning("Module info not loaded, cannot generate overview")
                return
                
            # Create overview markdown file
            overview_path = docs_dir / "module_overview.md"
            
            module_name = self.module_info.get("name", "Unknown Module")
            module_id = self.module_info.get("id", "Unknown")
            
            content = f"""# Module Migration Overview: {module_name}

## Module Information
- **Module ID**: {module_id}
- **Module Name**: {module_name}
"""
            
            # Add description if available
            if self.module_metadata and "description" in self.module_metadata:
                content += f"- **Description**: {self.module_metadata['description']}\n"
                
            # Add creation date if available
            if self.module_info and "created" in self.module_info:
                content += f"- **Created**: {self.module_info['created']}\n"
                
            # Add migration timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content += f"- **Migration Date**: {timestamp}\n\n"
            
            # Write overview file
            with open(overview_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate module overview: {e}")
            
    def _generate_report_mapping(self, docs_dir: Path) -> None:
        """
        Generate report mapping documentation
        
        Args:
            docs_dir: Path to the documentation directory
        """
        try:
            # Create mapping markdown file
            mapping_path = docs_dir / "report_mapping.md"
            
            content = """# Report Mapping

This document maps Cognos reports to their Power BI equivalents.

| Cognos Report ID | Cognos Report Name | Power BI Report Path | Status |
|------------------|-------------------|---------------------|--------|
"""
            
            # Find all report directories
            reports_path = self.module_path / "reports"
            if not reports_path.exists():
                self.logger.warning("Reports directory not found, cannot generate mapping")
                return
                
            report_dirs = [d for d in reports_path.iterdir() if d.is_dir() and d.name.startswith("report_")]
            
            # Process each report
            for report_dir in report_dirs:
                report_id = report_dir.name.replace("report_", "")
                
                # Try to get report details from extracted data
                report_details_path = report_dir / "extracted" / "report_details.json"
                report_name = "Unknown"
                
                if report_details_path.exists():
                    try:
                        with open(report_details_path, "r") as f:
                            details = json.load(f)
                            report_name = details.get("name", "Unknown")
                    except:
                        pass
                        
                # Check if PBIT was generated successfully
                pbit_dir = report_dir / "pbit"
                status = "✓ Success" if pbit_dir.exists() else "✗ Failed"
                
                # Add to mapping table
                content += f"| {report_id} | {report_name} | {report_dir.name} | {status} |\n"
                
            # Write mapping file
            with open(mapping_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate report mapping: {e}")
