"""
Module-specific documentation generator for Cognos to Power BI migration
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class ModuleDocumentationGenerator:
    """
    Generates module-specific documentation for the migration
    """
    
    def __init__(self):
        """Initialize the module documentation generator"""
        self.logger = logging.getLogger(__name__)
        
    def generate_module_documentation(self, module_path: Path, module_info: Dict[str, Any], 
                                    module_metadata: Dict[str, Any]) -> bool:
        """
        Generate module-specific documentation
        
        Args:
            module_path: Path to the module directory
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            docs_dir = module_path / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Generate module overview
            self._generate_module_overview(docs_dir, module_info, module_metadata)
            
            # Generate data model documentation
            self._generate_data_model_documentation(docs_dir, module_path)
            
            # Generate migration report
            self._generate_migration_report(docs_dir, module_info, module_metadata)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate module documentation: {e}")
            return False
            
    def _generate_module_overview(self, docs_dir: Path, module_info: Dict[str, Any], 
                                module_metadata: Dict[str, Any]) -> None:
        """Generate module overview documentation"""
        try:
            overview_path = docs_dir / "module_overview.md"
            
            # Extract module information
            module_name = module_info.get('name', 'Unknown Module')
            module_description = module_info.get('description', 'No description available')
            module_id = module_info.get('id', 'Unknown ID')
            
            # Create overview content
            content = f"""# Module: {module_name}

## Overview
- **Module ID**: {module_id}
- **Description**: {module_description}

## Migration Information
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Migration Tool Version**: {module_metadata.get('tool_version', 'Unknown')}

## Module Structure
"""
            
            # Add module structure if available
            if 'structure' in module_metadata:
                content += "### Components\n"
                for component in module_metadata.get('structure', {}).get('components', []):
                    content += f"- {component.get('name', 'Unknown')}\n"
            
            # Write to file
            with open(overview_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate module overview: {e}")
            
    def _generate_data_model_documentation(self, docs_dir: Path, module_path: Path) -> None:
        """Generate data model documentation"""
        try:
            model_doc_path = docs_dir / "data_model.md"
            
            # Look for model information in the module
            model_info = {}
            model_info_path = module_path / "extracted" / "model_info.json"
            
            if model_info_path.exists():
                with open(model_info_path, "r") as f:
                    model_info = json.load(f)
            
            # Create model documentation content
            content = """# Data Model Documentation

## Tables
"""
            
            # Add tables if available
            tables = model_info.get('tables', [])
            if tables:
                for table in tables:
                    table_name = table.get('name', 'Unknown')
                    content += f"### {table_name}\n"
                    
                    # Add columns
                    content += "| Column | Data Type | Description |\n"
                    content += "|--------|-----------|-------------|\n"
                    
                    for column in table.get('columns', []):
                        col_name = column.get('name', 'Unknown')
                        col_type = column.get('datatype', 'Unknown')
                        col_desc = column.get('description', '')
                        content += f"| {col_name} | {col_type} | {col_desc} |\n"
                    
                    content += "\n"
            else:
                content += "*No tables found in the data model*\n"
            
            # Write to file
            with open(model_doc_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate data model documentation: {e}")
            
    def _generate_migration_report(self, docs_dir: Path, module_info: Dict[str, Any],
                                 module_metadata: Dict[str, Any]) -> None:
        """Generate migration report for the module"""
        try:
            report_path = docs_dir / "migration_report.md"
            
            # Extract module information
            module_name = module_info.get('name', 'Unknown Module')
            module_id = module_info.get('id', 'Unknown ID')
            
            # Create report content
            content = f"""# Migration Report: {module_name}

## Module Information
- **Module Name**: {module_name}
- **Module ID**: {module_id}
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Migration Summary
"""
            
            # Add migration summary if available
            migration_summary_path = docs_dir / "module_migration_summary.json"
            if migration_summary_path.exists():
                with open(migration_summary_path, "r") as f:
                    summary = json.load(f)
                    
                content += f"- **Total Reports**: {summary.get('total_reports', 'Unknown')}\n"
                content += f"- **Successfully Migrated**: {summary.get('successful_reports', 'Unknown')}\n"
                content += f"- **Success Rate**: {summary.get('success_rate', 'Unknown')}\n\n"
            else:
                content += "*Migration summary not available*\n\n"
                
            content += """## Migration Details

### Cognos to Power BI Mapping
The following Cognos elements were mapped to Power BI:

| Cognos Element | Power BI Element | Notes |
|---------------|-----------------|-------|
| Module | Dataset | Module metadata included as annotations |
| Report | Report Page | Each report becomes a page in Power BI |
| Query | Table | Tables include module source information |
| Calculation | Measure | Calculations converted to DAX |

### Known Limitations
- Complex Cognos expressions may require manual adjustment
- Some advanced formatting options may not be preserved
- Custom JavaScript elements are not supported in Power BI
"""
            
            # Write to file
            with open(report_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {e}")
            
    def generate_migration_report(self, powerbi_project: Any, extracted_dir: Path) -> bool:
        """
        Generate migration report for a specific Power BI project
        
        Args:
            powerbi_project: Power BI project
            extracted_dir: Directory containing extracted data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create documentation directory
            docs_dir = Path(extracted_dir).parent / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Path for the report
            report_path = docs_dir / "report_migration_details.md"
            
            # Extract project metadata
            metadata = powerbi_project.metadata if hasattr(powerbi_project, 'metadata') else {}
            module_id = metadata.get('module_id', 'Unknown')
            module_name = metadata.get('module_name', 'Unknown')
            report_name = metadata.get('report_name', 'Unknown')
            
            # Create report content
            content = f"""# Migration Report: {report_name}

## Module Context
- **Module Name**: {module_name}
- **Module ID**: {module_id}
- **Report Name**: {report_name}
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Migration Details
"""
            
            # Add data model details if available
            if hasattr(powerbi_project, 'data_model'):
                data_model = powerbi_project.data_model
                
                content += "### Data Model\n"
                content += f"- **Model Name**: {data_model.name}\n"
                content += f"- **Tables**: {len(data_model.tables)}\n"
                content += f"- **Relationships**: {len(data_model.relationships)}\n"
                content += f"- **Measures**: {len(data_model.measures)}\n\n"
                
                # Add table details
                content += "#### Tables\n"
                for table in data_model.tables:
                    content += f"- **{table.name}**: {len(table.columns)} columns\n"
            
            # Write to file
            with open(report_path, "w") as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {e}")
            return False
