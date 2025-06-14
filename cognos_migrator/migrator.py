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
# Import PowerBIProjectGenerator directly from generators.py to use the LLM-integrated version
from .generators import PowerBIProjectGenerator, DocumentationGenerator
from .models import (
    CognosReport, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
)
from .cpf_extractor import CPFExtractor


class CognosMigrator:
    """Main orchestrator for Cognos to Power BI migration"""
    
    def __init__(self, config: MigrationConfig, base_url: str = None, session_key: str = None, cpf_file_path: str = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        self.cognos_client = CognosClient(cognos_config, base_url, session_key)
        self.report_parser = CognosReportSpecificationParser()
        self.project_generator = PowerBIProjectGenerator(config)
        self.doc_generator = DocumentationGenerator(config)
        
        # Initialize CPF extractor if a CPF file path is provided
        self.cpf_extractor = None
        if cpf_file_path:
            self.cpf_extractor = CPFExtractor(cpf_file_path)
            if not self.cpf_extractor.metadata:
                self.logger.warning(f"Failed to load CPF file: {cpf_file_path}")
                self.cpf_extractor = None
            else:
                self.logger.info(f"Successfully loaded CPF file: {cpf_file_path}")
    
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
            
            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor:
                self._enhance_with_cpf_metadata(powerbi_project)
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, str(extracted_dir))
            
            # If CPF metadata is available, save it to the extracted folder
            if self.cpf_extractor:
                cpf_metadata_path = extracted_dir / "cpf_metadata.json"
                self.cpf_extractor.parser.save_metadata_to_json(str(cpf_metadata_path))
                self.logger.info(f"Saved CPF metadata to: {cpf_metadata_path}")
            
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
        """Save extracted data to files for investigation"""
        try:
            import json
            import xml.etree.ElementTree as ET
            from datetime import datetime
            
            # Save raw report specification XML
            spec_path = extracted_dir / "report_specification.xml"
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(cognos_report.specification)
            
            # Save report metadata as JSON
            metadata_path = extracted_dir / "report_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(cognos_report.metadata, f, indent=2)
            
            # Save report details as JSON
            details_path = extracted_dir / "report_details.json"
            with open(details_path, "w", encoding="utf-8") as f:
                details = {
                    "id": cognos_report.id,
                    "name": cognos_report.name,
                    "extractionTime": str(datetime.now())
                }
                
                # Add optional attributes if they exist
                if hasattr(cognos_report, 'path'):
                    details["path"] = cognos_report.path
                if hasattr(cognos_report, 'type'):
                    details["type"] = cognos_report.type
                    
                json.dump(details, f, indent=2)
            
            # Save serialized CognosReport object
            report_obj_path = extracted_dir / "cognos_report.json"
            with open(report_obj_path, "w", encoding="utf-8") as f:
                report_dict = {
                    "id": cognos_report.id,
                    "name": cognos_report.name,
                    "data_sources": [ds.__dict__ if hasattr(ds, '__dict__') else str(ds) for ds in cognos_report.data_sources]
                }
                
                # Add optional attributes if they exist
                if hasattr(cognos_report, 'path'):
                    report_dict["path"] = cognos_report.path
                if hasattr(cognos_report, 'type'):
                    report_dict["type"] = cognos_report.type
                    
                json.dump(report_dict, f, indent=2)
            
            # Extract and save additional intermediate files for detailed investigation
            try:
                # Parse the XML for additional extractions
                root = ET.fromstring(cognos_report.specification)
                
                # Register the namespace - Cognos XML uses namespaces
                ns = {}
                if root.tag.startswith('{'):
                    ns_uri = root.tag.split('}')[0].strip('{')
                    ns['ns'] = ns_uri
                    self.logger.info(f"Detected XML namespace: {ns_uri}")
                
                # Extract and save queries
                queries = self._extract_queries_from_xml(root, ns)
                queries_path = extracted_dir / "report_queries.json"
                with open(queries_path, "w", encoding="utf-8") as f:
                    json.dump(queries, f, indent=2)
                
                # Extract and save data items/columns
                data_items = self._extract_data_items_from_xml(root, ns)
                data_items_path = extracted_dir / "report_data_items.json"
                with open(data_items_path, "w", encoding="utf-8") as f:
                    json.dump(data_items, f, indent=2)
                
                # Extract and save expressions
                expressions = self._extract_expressions_from_xml(root, ns)
                expressions_path = extracted_dir / "report_expressions.json"
                with open(expressions_path, "w", encoding="utf-8") as f:
                    json.dump(expressions, f, indent=2)
                
                # Extract and save parameters
                parameters = self._extract_parameters_from_xml(root, ns)
                parameters_path = extracted_dir / "report_parameters.json"
                with open(parameters_path, "w", encoding="utf-8") as f:
                    json.dump(parameters, f, indent=2)
                
                # Extract and save filters
                filters = self._extract_filters_from_xml(root, ns)
                filters_path = extracted_dir / "report_filters.json"
                with open(filters_path, "w", encoding="utf-8") as f:
                    json.dump(filters, f, indent=2)
                
                # Extract and save layout information
                layout = self._extract_layout_from_xml(root, ns)
                layout_path = extracted_dir / "report_layout.json"
                with open(layout_path, "w", encoding="utf-8") as f:
                    json.dump(layout, f, indent=2)
                
                self.logger.info(f"Saved additional extracted data files to {extracted_dir}")
                
            except Exception as e:
                self.logger.warning(f"Could not extract additional data from XML: {e}")
            
            self.logger.info(f"Saved extracted Cognos report data to {extracted_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save extracted data: {e}")
    
    def _extract_queries_from_xml(self, root, ns=None):
        """Extract queries from report specification XML"""
        queries = []
        try:
            # Find the queries section directly under the root
            queries_section = root.find("queries")
                
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return queries
                
            # Find all query elements directly under the queries section
            query_elements = queries_section.findall("query")
            
            for i, query_elem in enumerate(query_elements):
                query = {
                    "id": query_elem.get("id", f"query_{i}"),
                    "name": query_elem.get("name", f"Query {i}"),
                }
                
                # Extract source information
                source_elem = query_elem.find("source")
                if source_elem is not None:
                    model_elem = source_elem.find("model")
                    if model_elem is not None:
                        query["source"] = "model"
                    else:
                        query["source"] = self._get_element_text(source_elem)
                
                # Extract data items (columns)
                data_items = []
                selection_elem = query_elem.find("selection")
                if selection_elem is not None:
                    for item in selection_elem.findall("dataItem"):
                        data_item = {
                            "name": item.get("name", ""),
                            "aggregate": item.get("aggregate", "none"),
                            "rollupAggregate": item.get("rollupAggregate", "none"),
                        }
                        
                        # Extract expression
                        expr_elem = item.find("expression")
                        if expr_elem is not None:
                            data_item["expression"] = self._get_element_text(expr_elem)
                        
                        # Extract XML attributes for data type and usage
                        xml_attrs = item.find("XMLAttributes")
                        if xml_attrs is not None:
                            data_type_attr = xml_attrs.find("XMLAttribute[@name='RS_dataType']")
                            if data_type_attr is not None:
                                data_item["dataType"] = data_type_attr.get("value", "")
                                
                            usage_attr = xml_attrs.find("XMLAttribute[@name='RS_dataUsage']")
                            if usage_attr is not None:
                                data_item["dataUsage"] = usage_attr.get("value", "")
                        
                        data_items.append(data_item)
                
                query["dataItems"] = data_items
                
                # Extract filters
                filters = []
                detail_filters = query_elem.find("detailFilters")
                if detail_filters is not None:
                    for filter_elem in detail_filters.findall("detailFilter"):
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            filters.append({
                                "type": "detail",
                                "expression": self._get_element_text(filter_expr)
                            })
                
                summary_filters = query_elem.find("summaryFilters")
                if summary_filters is not None:
                    for filter_elem in summary_filters.findall("summaryFilter"):
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            filters.append({
                                "type": "summary",
                                "expression": self._get_element_text(filter_expr)
                            })
                
                query["filters"] = filters
                queries.append(query)
                
            return queries
            
        except Exception as e:
            self.logger.warning(f"Error extracting queries from XML: {e}")
            return queries
    
    def _extract_data_items_from_xml(self, root, ns=None):
        """Extract data items from report specification XML"""
        data_items = []
        try:
            # Find the queries section directly under the root
            queries_section = root.find("queries")
                
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return data_items
                
            # Process each query
            for query_idx, query_elem in enumerate(queries_section.findall("query")):
                query_name = query_elem.get("name", f"Query {query_idx}")
                
                # Find the selection element that contains data items
                selection_elem = query_elem.find("selection")
                if selection_elem is None:
                    continue
                    
                # Process each data item in the selection
                for i, item_elem in enumerate(selection_elem.findall("dataItem")):
                    data_item = {
                        "name": item_elem.get("name", f"Data Item {i}"),
                        "queryName": query_name,
                        "aggregate": item_elem.get("aggregate", "none"),
                        "rollupAggregate": item_elem.get("rollupAggregate", "none"),
                    }
                    
                    # Extract expression
                    expr_elem = item_elem.find("expression")
                    if expr_elem is not None:
                        data_item["expression"] = self._get_element_text(expr_elem)
                    
                    # Extract XML attributes for data type and usage
                    xml_attrs = item_elem.find("XMLAttributes")
                    if xml_attrs is not None:
                        # Extract data type
                        data_type_attr = xml_attrs.find("XMLAttribute[@name='RS_dataType']")
                        if data_type_attr is not None:
                            data_type_value = data_type_attr.get("value", "")
                            # Convert numeric data type codes to readable format
                            data_type_map = {
                                "1": "integer",
                                "2": "decimal",
                                "3": "string",
                                "4": "datetime",
                                "5": "boolean"
                            }
                            data_item["dataType"] = data_type_map.get(data_type_value, data_type_value)
                        
                        # Extract data usage
                        usage_attr = xml_attrs.find("XMLAttribute[@name='RS_dataUsage']")
                        if usage_attr is not None:
                            usage_value = usage_attr.get("value", "")
                            # Convert numeric usage codes to readable format
                            usage_map = {
                                "0": "attribute",
                                "1": "identifier",
                                "2": "fact"
                            }
                            data_item["dataUsage"] = usage_map.get(usage_value, usage_value)
                    
                    # Extract format information if available
                    format_elem = item_elem.find("format")
                    if format_elem is not None:
                        data_item["format"] = {
                            "type": format_elem.get("type", ""),
                            "pattern": format_elem.get("pattern", ""),
                        }
                    
                    data_items.append(data_item)
        except Exception as e:
            self.logger.warning(f"Error extracting data items: {e}")
        
        return data_items
    
    def _extract_expressions_from_xml(self, root, ns=None):
        """Extract expressions from report specification XML"""
        expressions = []
        try:
            # Create a map of elements to their parent contexts
            # This is needed because ElementTree doesn't have a getparent() method
            parent_map = {}
            for parent in root.iter():
                for child in parent:
                    parent_map[child] = parent
            
            # Find the queries section directly under the root
            queries_section = root.find("queries")
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return expressions
                
            # Process each query
            for query_elem in queries_section.findall("query"):
                query_name = query_elem.get("name", "")
                
                # Process data item expressions
                selection_elem = query_elem.find("selection")
                if selection_elem is not None:
                    for data_item in selection_elem.findall("dataItem"):
                        data_item_name = data_item.get("name", "")
                        expr_elem = data_item.find("expression")
                        
                        if expr_elem is not None:
                            expressions.append({
                                "parentType": "dataItem",
                                "parentName": data_item_name,
                                "queryName": query_name,
                                "text": self._get_element_text(expr_elem),
                                "context": f"Query: {query_name}, Data Item: {data_item_name}"
                            })
                
                # Process detail filter expressions
                detail_filters = query_elem.find("detailFilters")
                if detail_filters is not None:
                    for filter_elem in detail_filters.findall("detailFilter"):
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            expressions.append({
                                "parentType": "detailFilter",
                                "queryName": query_name,
                                "text": self._get_element_text(filter_expr),
                                "context": f"Query: {query_name}, Detail Filter"
                            })
            
                # Process summary filter expressions
                summary_filters = query_elem.find("summaryFilters")
                if summary_filters is not None:
                    for filter_elem in summary_filters.findall("summaryFilter"):
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            expressions.append({
                                "parentType": "summaryFilter",
                                "queryName": query_name,
                                "text": self._get_element_text(filter_expr),
                                "context": f"Query: {query_name}, Summary Filter"
                            })
                
            # We've already processed all expressions in the queries section above,
            # so we don't need this redundant section anymore.
            # The expressions from data items, detail filters, and summary filters are already captured.
        except Exception as e:
            self.logger.warning(f"Error extracting expressions: {e}")
        
        return expressions
    
    def _extract_parameters_from_xml(self, root, ns=None):
        """Extract parameters from report specification XML"""
        parameters = []
        try:
            # Find the parameters section directly under the root
            params_section = root.find("parameters")
            if params_section is None:
                # Try to find parameters in other locations
                params_section = root.find("parameterList")
                if params_section is None:
                    self.logger.warning("No parameters section found in report specification")
                    return parameters
            
            # Process each parameter
            for i, param_elem in enumerate(params_section.findall("parameter")):
                param = {
                    "id": param_elem.get("id", f"param_{i}"),
                    "name": param_elem.get("name", f"Parameter {i}"),
                    "type": param_elem.get("type", ""),
                    "required": param_elem.get("required", "false"),
                    "multiValue": param_elem.get("multiValue", "false"),
                }
                
                # Extract default value
                default_elem = param_elem.find("defaultValue")
                if default_elem is not None:
                    param["defaultValue"] = self._get_element_text(default_elem)
                
                # Extract allowed values
                values_elem = param_elem.find("allowedValues")
                if values_elem is not None:
                    allowed_values = []
                    for value_elem in values_elem.findall("value"):
                        allowed_values.append(self._get_element_text(value_elem))
                    param["allowedValues"] = allowed_values
                
                parameters.append(param)
        except Exception as e:
            self.logger.warning(f"Error extracting parameters: {e}")
        
        return parameters

    def _extract_filters_from_xml(self, root, ns=None):
        """Extract filters from report specification XML"""
        filters = []
        try:
            # Find the queries section directly under the root
            queries_section = root.find("queries")
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return filters
                
            # Process each query
            for query_idx, query_elem in enumerate(queries_section.findall("query")):
                query_name = query_elem.get("name", f"Query {query_idx}")
                query_id = query_elem.get("id", f"query_{query_idx}")
                
                # Process detail filters
                detail_filters = query_elem.find("detailFilters")
                if detail_filters is not None:
                    for i, filter_elem in enumerate(detail_filters.findall("detailFilter")):
                        filter_item = {
                            "id": filter_elem.get("id", f"detail_filter_{query_id}_{i}"),
                            "name": filter_elem.get("name", f"Detail Filter {i}"),
                            "type": "detail",
                            "queryName": query_name,
                            "queryId": query_id
                        }
                        
                        # Extract filter expression
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            filter_item["expression"] = self._get_element_text(filter_expr)
                        
                        filters.append(filter_item)
                
                # Process summary filters
                summary_filters = query_elem.find("summaryFilters")
                if summary_filters is not None:
                    for i, filter_elem in enumerate(summary_filters.findall("summaryFilter")):
                        filter_item = {
                            "id": filter_elem.get("id", f"summary_filter_{query_id}_{i}"),
                            "name": filter_elem.get("name", f"Summary Filter {i}"),
                            "type": "summary",
                            "queryName": query_name,
                            "queryId": query_id
                        }
                        
                        # Extract filter expression
                        filter_expr = filter_elem.find("filterExpression")
                        if filter_expr is not None:
                            filter_item["expression"] = self._get_element_text(filter_expr)
                        
                        filters.append(filter_item)
                
        except Exception as e:
            self.logger.warning(f"Error extracting filters: {e}")
        
        return filters
    
    def _extract_layout_from_xml(self, root, ns=None):
        """Extract layout information from report specification XML"""
        layout = {
            "pages": [],
            "containers": [],
            "visualizations": []
        }
        try:
            # Find layout section directly under the root
            layout_section = root.find("layout")
            if layout_section is None:
                # Try to find layout in other locations
                layout_section = root.find("layouts/layout")
                if layout_section is None:
                    self.logger.warning("No layout section found in report specification")
                    return layout
            
            # Extract page information
            pages = []
            page_elements = layout_section.findall(".//page")
            for page_elem in page_elements:
                page = {
                    "id": page_elem.get("id", ""),
                    "name": page_elem.get("name", ""),
                    "style": page_elem.get("style", "")
                }
                pages.append(page)
            layout["pages"] = pages
            
            # Extract container information (blocks, tables, etc.)
            containers = []
            block_elements = layout_section.findall(".//block")
            table_elements = layout_section.findall(".//table")
                
            for container_elem in block_elements + table_elements:
                container = {
                    "id": container_elem.get("id", ""),
                    "type": container_elem.tag.split('}')[-1] if '}' in container_elem.tag else container_elem.tag,
                    "style": container_elem.get("style", "")
                }
                containers.append(container)
            layout["containers"] = containers
            
            # Extract visualization information (charts, crosstabs, lists, etc.)
            visualizations = []
            chart_elements = layout_section.findall(".//chart")
            crosstab_elements = layout_section.findall(".//crosstab")
            list_elements = layout_section.findall(".//list")
            
            for viz_elem in chart_elements + crosstab_elements + list_elements:
                viz = {
                    "id": viz_elem.get("id", ""),
                    "type": viz_elem.tag.split('}')[-1] if '}' in viz_elem.tag else viz_elem.tag,
                    "style": viz_elem.get("style", "")
                }
                visualizations.append(viz)
            layout["visualizations"] = visualizations
            
        except Exception as e:
            self.logger.warning(f"Error extracting layout: {e}")
        
        return layout
    
    def _get_element_text(self, element):
        """Safely get text from an XML element"""
        if element is None:
            return ""
        return element.text or ""
    
    def _enhance_with_cpf_metadata(self, powerbi_project: PowerBIProject) -> None:
        """Enhance Power BI project with metadata from CPF file"""
        try:
            if not self.cpf_extractor or not powerbi_project or not powerbi_project.data_model:
                return
            
            self.logger.info("Enhancing Power BI project with CPF metadata")
            
            # Enhance tables with CPF metadata
            for table in powerbi_project.data_model.tables:
                table_name = table.name
                
                # Get table schema from CPF metadata
                table_schema = self.cpf_extractor.get_table_schema(table_name)
                if not table_schema or not table_schema.get('columns'):
                    continue
                
                self.logger.info(f"Enhancing table: {table_name} with CPF metadata")
                
                # Update column metadata
                for col in table.columns:
                    # Find matching column in CPF metadata
                    for cpf_col in table_schema.get('columns', []):
                        if cpf_col.get('name') == col.name:
                            # Update column data type if available
                            if cpf_col.get('dataType'):
                                col.data_type = self._map_cpf_data_type(cpf_col.get('dataType'))
                            
                            # Update column description if available
                            if cpf_col.get('expression'):
                                col.description = f"Expression: {cpf_col.get('expression')}"
                            
                            break
                
                # Add relationships if available
                for rel in table_schema.get('relationships', []):
                    target_table = self._find_table_by_name(powerbi_project.data_model, 
                                                         self.cpf_extractor.get_query_subject_by_id(rel.get('targetQuerySubjectId', '')).get('name', ''))
                    
                    if target_table:
                        # Get column names
                        source_cols = [self.cpf_extractor.get_column_name_by_id(col_id) for col_id in rel.get('sourceColumns', [])]
                        target_cols = [self.cpf_extractor.get_column_name_by_id(col_id) for col_id in rel.get('targetColumns', [])]
                        
                        # Create relationship if columns are found
                        if source_cols and target_cols:
                            new_rel = Relationship(
                                from_table=table.name,
                                from_column=source_cols[0],  # Use first column for now
                                to_table=target_table.name,
                                to_column=target_cols[0],    # Use first column for now
                                cardinality=self._map_cpf_cardinality(rel.get('cardinality', ''))
                            )
                            
                            # Add relationship if it doesn't already exist
                            if not self._relationship_exists(powerbi_project.data_model, new_rel):
                                powerbi_project.data_model.relationships.append(new_rel)
                                self.logger.info(f"Added relationship: {table.name}.{source_cols[0]} -> {target_table.name}.{target_cols[0]}")
            
            # Add M-query context to the project for later use
            powerbi_project.metadata['cpf_metadata'] = True
            
            self.logger.info("Successfully enhanced Power BI project with CPF metadata")
            
        except Exception as e:
            self.logger.error(f"Error enhancing with CPF metadata: {e}")
    
    def _map_cpf_data_type(self, cpf_type: str) -> str:
        """Map CPF data type to Power BI data type"""
        type_mapping = {
            'xs:string': 'Text',
            'xs:integer': 'Int64',
            'xs:decimal': 'Decimal',
            'xs:double': 'Double',
            'xs:float': 'Double',
            'xs:boolean': 'Boolean',
            'xs:date': 'Date',
            'xs:time': 'Time',
            'xs:dateTime': 'DateTime',
            'xs:duration': 'Duration'
        }
        
        return type_mapping.get(cpf_type, 'Text')  # Default to Text if unknown
    
    def _map_cpf_cardinality(self, cardinality: str) -> str:
        """Map CPF cardinality to Power BI cardinality"""
        cardinality_mapping = {
            'oneToOne': 'OneToOne',
            'oneToMany': 'OneToMany',
            'manyToOne': 'ManyToOne',
            'manyToMany': 'ManyToMany'
        }
        
        return cardinality_mapping.get(cardinality, 'ManyToOne')  # Default to ManyToOne if unknown
    
    def _find_table_by_name(self, data_model, table_name: str):
        """Find a table in the data model by name"""
        for table in data_model.tables:
            if table.name == table_name:
                return table
        return None
    
    def _relationship_exists(self, data_model, new_rel: Relationship) -> bool:
        """Check if a relationship already exists in the data model"""
        for rel in data_model.relationships:
            if (rel.from_table == new_rel.from_table and 
                rel.from_column == new_rel.from_column and 
                rel.to_table == new_rel.to_table and 
                rel.to_column == new_rel.to_column):
                return True
        return False
    
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
