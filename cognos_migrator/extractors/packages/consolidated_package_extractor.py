"""
Consolidated package extractor for Cognos Framework Manager packages.

This module provides functionality to coordinate the extraction of data from
Cognos Framework Manager (FM) package files using specialized extractors.
"""

import logging
import re
import json
import os
import shutil
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import Dict, List, Optional, Any

from cognos_migrator.models import DataType, DataModel, Table, Column, Relationship, Measure

from .base_package_extractor import BasePackageExtractor
from .package_structure_extractor import PackageStructureExtractor
from .package_query_subject_extractor import PackageQuerySubjectExtractor
from .package_relationship_extractor import PackageRelationshipExtractor
from .package_calculation_extractor import PackageCalculationExtractor
from .package_filter_extractor import PackageFilterExtractor


class ConsolidatedPackageExtractor:
    """Coordinates the extraction of data from Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the consolidated package extractor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize specialized extractors
        self.structure_extractor = PackageStructureExtractor(logger)
        self.query_subject_extractor = PackageQuerySubjectExtractor(logger)
        self.relationship_extractor = PackageRelationshipExtractor(logger)
        self.calculation_extractor = PackageCalculationExtractor(logger)
        self.filter_extractor = PackageFilterExtractor(logger)

    def _save_json(self, data: Dict[str, Any], file_path: str):
        """Saves dictionary data to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved data to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save data to {file_path}: {e}")

    def extract_package(self, package_file_path: str, output_dir: str, required_tables: Optional[set] = None) -> Dict[str, Any]:
        """Extracts and consolidates information from a package XML file."""
        try:
            self.logger.info(f"Extracting package from {package_file_path}")
            
            # Create output directory if specified
            if output_dir:
                # Use the output_dir directly without adding "extracted" subfolder
                # This avoids creating a nested extracted folder
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = None
            
            # Parse the XML file once
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Update namespaces on all extractors from the root element
            self.structure_extractor.update_namespaces_from_root(root)
            self.query_subject_extractor.update_namespaces_from_root(root)
            self.relationship_extractor.update_namespaces_from_root(root)
            self.calculation_extractor.update_namespaces_from_root(root)
            self.logger.info(f"Updated namespaces on all extractors from {package_file_path}")
            
            # Save a formatted version of the XML file if output directory is specified
            if output_path:
                self._save_formatted_xml(package_file_path, output_path)
            
            # Extract package structure
            if output_path:
                structure = self.structure_extractor.extract_and_save(package_file_path, output_path)
            else:
                structure = self.structure_extractor.extract_package_structure(root)
            
            # Extract query subjects
            if output_path:
                query_subjects_result = self.query_subject_extractor.extract_and_save(package_file_path, output_path)
                query_subjects = query_subjects_result.get("query_subjects", [])
            else:
                query_subjects = self.query_subject_extractor.extract_query_subjects(root)
            
            # Extract relationships
            if output_path:
                relationships_result = self.relationship_extractor.extract_and_save(package_file_path, output_path)
                relationships = relationships_result.get("relationships", [])
            else:
                relationships = self.relationship_extractor.extract_relationships(root)
            
            # Extract calculations
            if output_path:
                calculations_result = self.calculation_extractor.extract_and_save(package_file_path, output_path)
                calculations = calculations_result.get("calculations", {})
            else:
                calculations = self.calculation_extractor.extract_calculations(root)
                
            # Extract filters
            if output_path:
                filters_result = self.filter_extractor.extract_and_save(package_file_path, output_path)
                filters = filters_result.get("filters", {})
            else:
                filters = self.filter_extractor.extract_filters(root)
            
            # Combine into package info
            package_info = {
                'name': structure.get('name', 'Unknown Package'),
                'query_subjects': query_subjects,
                'relationships': relationships,
                'calculations': calculations,
                'filters': filters,
                'structure': structure
            }
            
            # Save consolidated package info if output directory is specified
            if output_path:
                self.structure_extractor.save_to_json(package_info, output_path, "package_info.json")
            
            self.logger.info(f"Successfully extracted package: {package_info['name']}")

            # Apply filtering if required_tables is provided
            if required_tables:
                self.logger.info(f"Filtering package to {len(required_tables)} required tables.")
                
                # Filter query subjects (tables)
                package_info['query_subjects'] = [
                    qs for qs in package_info.get('query_subjects', [])
                    if qs.get('name') in required_tables
                ]
                
                # Filter relationships
                package_info['relationships'] = [
                    rel for rel in package_info.get('relationships', [])
                    if rel.get('from_table') in required_tables and rel.get('to_table') in required_tables
                ]
                self.logger.info(f"Filtered to {len(package_info['query_subjects'])} tables and {len(package_info['relationships'])} relationships.")

            self._save_json(package_info, os.path.join(output_dir, f"{package_info['name']}_consolidated.json"))
            
            return package_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract package from {package_file_path}: {e}")
            raise
    
    def _save_formatted_xml(self, package_file_path: str, output_path: Path) -> None:
        """Save a formatted version of the XML file
        
        Args:
            package_file_path: Path to the original XML file
            output_path: Directory to save the formatted XML file
        """
        try:
            # Get the original filename
            original_filename = os.path.basename(package_file_path)
            formatted_filename = f"{os.path.splitext(original_filename)[0]}_formatted.xml"
            formatted_file_path = output_path / formatted_filename
            
            self.logger.info(f"Creating formatted XML file: {formatted_file_path}")
            
            # Parse the XML file
            with open(package_file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Parse and format the XML using minidom
            dom = minidom.parseString(xml_content)
            formatted_xml = dom.toprettyxml(indent="  ")
            
            # Remove extra blank lines that minidom sometimes adds
            lines = [line for line in formatted_xml.split('\n') if line.strip()]
            formatted_xml = '\n'.join(lines)
            
            # Write the formatted XML to file
            with open(formatted_file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_xml)
            
            # Also save a copy with the original filename for easier reference
            original_formatted_path = output_path / original_filename
            shutil.copy(str(formatted_file_path), str(original_formatted_path))
            
            self.logger.info(f"Formatted XML saved to {formatted_file_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save formatted XML: {e}")
            # Continue with extraction even if formatting fails
    
    def convert_to_data_model(self, package_info: Dict[str, Any]) -> DataModel:
        """Convert extracted package information to a data model
        
        Args:
            package_info: Dictionary containing extracted package information
            
        Returns:
            DataModel instance
        """
        try:
            # Load settings from settings.json
            settings = {}
            try:
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
            except FileNotFoundError:
                self.logger.warning("settings.json not found. Using default settings.")
            
            date_table_mode = settings.get('date_table_mode', 'visible')
            self.logger.info(f"Using date table mode: {date_table_mode}")

            self.logger.info(f"Converting package {package_info['name']} to data model")
            
            # Create tables list for data model
            tables = []
            
            # Create data model with empty tables list and settings
            data_model = DataModel(name=package_info['name'], tables=tables, date_table_mode=date_table_mode)

            # Create a single, central date table for the entire model
            self._create_central_date_table(data_model)
            
            # Track query subjects by type for later processing
            db_query_subjects = []
            model_query_subjects = []
            other_query_subjects = []
            
            # First pass: Categorize query subjects by type
            for qs in package_info['query_subjects']:
                if 'sql_definition' in qs and qs['sql_definition']:
                    # Check if this is a dbQuery or modelQuery by examining the definition
                    if 'type' in qs['sql_definition'] and qs['sql_definition']['type'] == 'dbQuery':
                        self.logger.info(f"Found dbQuery subject: {qs['name']}")
                        db_query_subjects.append(qs)
                    elif 'type' in qs['sql_definition'] and qs['sql_definition']['type'] == 'modelQuery':
                        self.logger.info(f"Found modelQuery subject: {qs['name']}")
                        model_query_subjects.append(qs)
                    else:
                        # If type not clearly identified, check the SQL content
                        sql = qs['sql_definition'].get('sql', '')
                        if 'select * from' in sql.lower():
                            self.logger.info(f"Identified as likely dbQuery by SQL pattern: {qs['name']}")
                            db_query_subjects.append(qs)
                        else:
                            self.logger.info(f"Processing as other query subject: {qs['name']}")
                            other_query_subjects.append(qs)
                else:
                    # If no SQL definition, process as other
                    other_query_subjects.append(qs)
            
            # Process database query subjects first
            for qs in db_query_subjects:
                self._create_table_from_query_subject(qs, data_model)
                
            # Process other query subjects
            for qs in other_query_subjects:
                self._create_table_from_query_subject(qs, data_model)
                
            # Process model query subjects last, potentially combining with existing tables
            for qs in model_query_subjects:
                # Try to find if this model query references an existing table
                referenced_table = self._find_referenced_table(qs, data_model)
                
                if referenced_table:
                    # Enhance the existing table with the model query information
                    self._enhance_table_with_model_query(qs, referenced_table, data_model)
                    self.logger.info(f"Enhanced table {referenced_table.name} with model query from {qs['name']}")
                else:
                    # Create a new table if no matching reference found
                    self._create_table_from_query_subject(qs, data_model)

            # Sort tables alphabetically to ensure deterministic processing for primary variation
            data_model.tables.sort(key=lambda t: t.name)
            
            # Convert relationships
            for rel in package_info['relationships']:
                # Get left and right query subjects
                left_qs = rel.get('left', {}).get('query_subject')
                right_qs = rel.get('right', {}).get('query_subject')
                
                if not left_qs or not right_qs:
                    continue
                
                # Extract simple table names from fully qualified names
                # This doesn't change the Relationship class, just helps us identify tables
                left_table = left_qs.split('.')[-1].strip('[]')
                right_table = right_qs.split('.')[-1].strip('[]')
                
                # Get determinants (join columns)
                determinants = rel.get('determinants', [])
                
                left_col = None
                right_col = None
                
                # If determinants exist, use them
                if determinants:
                    det = determinants[0]  # Use the first determinant
                    left_col = det.get('left_column')
                    right_col = det.get('right_column')
                
                # If no determinants or columns, try to infer from table names
                if not left_col or not right_col:
                    self.logger.warning(f"No explicit join columns found for relationship between {left_table} and {right_table}. Attempting to infer.")
                    
                    # Find tables in the data model by their simple names
                    left_table_obj = None
                    right_table_obj = None
                    
                    for table in data_model.tables:
                        if table.name == left_table:
                            left_table_obj = table
                        if table.name == right_table:
                            right_table_obj = table
                    
                    # If tables exist, try to find matching columns
                    if left_table_obj and right_table_obj:
                        left_cols = [c.name for c in left_table_obj.columns]
                        right_cols = [c.name for c in right_table_obj.columns]
                        
                        # Find common column names
                        common_cols = set(left_cols).intersection(set(right_cols))
                        
                        # Try to find ID columns
                        id_patterns = [f"{left_table}ID", f"{left_table}_ID", "ID"]
                        for pattern in id_patterns:
                            matching_cols = [col for col in common_cols if pattern.lower() in col.lower()]
                            if matching_cols:
                                left_col = matching_cols[0]
                                right_col = matching_cols[0]
                                break
                        
                        # If still no match, use any common column as a last resort
                        if not left_col and common_cols:
                            left_col = right_col = list(common_cols)[0]
                            self.logger.info(f"Using common column {left_col} for relationship between {left_table} and {right_table}")
                
                # Skip if we still couldn't determine columns
                if not left_col or not right_col:
                    self.logger.warning(f"Skipping relationship between {left_table} and {right_table}: couldn't determine join columns")
                    continue
                
                # Extract just the column name without table name prefix
                # Pattern could be: TableName.ColumnName or just ColumnName
                if left_col and '.' in left_col:
                    parts = left_col.split('.')
                    left_col = parts[-1]  # Take the last part after the last dot
                
                if right_col and '.' in right_col:
                    parts = right_col.split('.')
                    right_col = parts[-1]  # Take the last part after the last dot
                
                # Create relationship with a name - using the simple table names instead of fully qualified names
                relationship = Relationship(
                    from_table=left_table,  # Use simple table name
                    from_column=left_col,    # Use just the column name without table prefix
                    to_table=right_table,    # Use simple table name
                    to_column=right_col      # Use just the column name without table prefix
                    # Let the Relationship class generate a UUID instead of using a descriptive name
                )
                
                # Add relationship to data model's relationships list
                data_model.relationships.append(relationship)
            
            self.logger.info(f"Successfully converted package to data model with {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
            
            return data_model
            
        except Exception as e:
            self.logger.error(f"Failed to convert package to data model: {e}")
            raise

    def _create_table_from_query_subject(self, qs: Dict[str, Any], data_model: DataModel) -> Table:
        """Create a Table object from a query subject and add it to the data model
        
        Args:
            qs: Query subject dictionary
            data_model: DataModel to add the table to
            
        Returns:
            The created Table object
        """
        # Create columns list for table
        columns = []
        
        # Add columns
        for item in qs.get('items', []):
            # Get the data type from the item
            cognos_type = item.get('datatype', 'string')
            
            # Map Cognos data type to Power BI data type
            if cognos_type.lower() in ['int32', 'int64']:
                data_type = DataType.INTEGER
            elif cognos_type.lower() in ['float', 'double']:
                data_type = DataType.DOUBLE
            elif cognos_type.lower() == 'boolean':
                data_type = DataType.BOOLEAN
            elif cognos_type.lower() in ['date', 'time', 'timestamp', 'datetime']:
                data_type = DataType.DATE
                self.logger.info(f"Mapped column {item['name']} with datatype {cognos_type} to DATE")
            else:
                data_type = DataType.STRING
                
            column = Column(
                name=item['name'],
                data_type=data_type,
                source_column=item.get('source_column', item['name'])  # Use source_column if available, otherwise use name
            )
            columns.append(column)
        
        # Extract SQL from sql_definition if available
        source_query = None
        metadata = {}
        
        if 'sql_definition' in qs and qs['sql_definition'] and 'sql' in qs['sql_definition']:
            source_query = qs['sql_definition']['sql']
            self.logger.info(f"Extracted SQL for table {qs['name']}: {source_query}")
            
            # Determine if this is a source table or model table
            query_type = qs['sql_definition'].get('type')
            if query_type:
                metadata['query_type'] = query_type
                
                # For dbQuery (source tables), mark as source table
                if query_type == 'dbQuery':
                    metadata['is_source_table'] = True
                    self.logger.info(f"Table {qs['name']} identified as source table (dbQuery)")
                    
                    # Extract the table name from the SQL for verification
                    match = re.search(r'from\s+\[?[\w\.]+\]?\.([\w]+)', source_query, re.IGNORECASE)
                    if match:
                        source_table_name = match.group(1)
                        if source_table_name != qs['name']:
                            self.logger.info(f"Source table name in SQL ({source_table_name}) differs from query subject name ({qs['name']})")
                
                # For modelQuery (model tables), extract the source table they reference
                elif query_type == 'modelQuery':
                    metadata['is_source_table'] = False
                    self.logger.info(f"Table {qs['name']} identified as model table (modelQuery)")
                    
                    # Extract the original table name from the SQL
                    match = re.search(r'from\s+\[?[\w\.]+\]?\.([\w]+)', source_query, re.IGNORECASE)
                    if match:
                        original_table_name = match.group(1)
                        self.logger.info(f"Model query {qs['name']} references source table: {original_table_name}")
                        metadata['original_source_table'] = original_table_name
        
        # Create table with columns and source query
        table = Table(name=qs['name'], columns=columns, source_query=source_query, metadata=metadata)
        
        # Add table to data model's tables list
        data_model.tables.append(table)
        
        # Create date tables for datetime columns
        self._create_date_tables_for_datetime_columns(table, data_model)
        
        return table
        
    def _deduplicate_columns(self, table: Table) -> None:
        """Deduplicate columns in a table by name
    
        Args:
            table: Table to deduplicate columns in
        """
        # Log all column names before deduplication
        self.logger.info(f"Before deduplication - Table {table.name} has {len(table.columns)} columns")
        column_names = [col.name for col in table.columns]
        self.logger.info(f"Column names: {column_names}")
        
        # Create a dictionary to track unique columns by name (case-insensitive)
        unique_columns = {}
        duplicates = []
        
        # Identify unique columns (keeping the first occurrence)
        for col in table.columns:
            col_name_lower = col.name.lower()
            if col_name_lower not in unique_columns:
                unique_columns[col_name_lower] = col
            else:
                duplicates.append(col.name)
        
        duplicate_count = len(duplicates)
        
        if duplicate_count > 0:
            self.logger.info(f"Deduplicating columns in table {table.name}: found {duplicate_count} duplicate columns")
            self.logger.info(f"Duplicate column names: {duplicates}")
            # Replace the columns list with the deduplicated list
            table.columns = list(unique_columns.values())
            
            # Log the column names after deduplication
            after_column_names = [col.name for col in table.columns]
            self.logger.info(f"After deduplication - Table {table.name} has {len(table.columns)} columns")
            self.logger.info(f"Column names after deduplication: {after_column_names}")
        else:
            self.logger.info(f"No duplicate columns found in table {table.name}")
    
    def _create_date_tables_for_datetime_columns(self, table: Table, data_model: DataModel) -> None:
        """Create relationships between datetime columns and the central date table.
        
        Args:
            table: The table containing datetime columns
            data_model: The data model which contains the central date table
        """
        # Find datetime columns in the table, sorted case-insensitively
        datetime_columns = sorted([col for col in table.columns if col.data_type == DataType.DATE], key=lambda x: x.name.lower())
        
        if not datetime_columns:
            return
            
        self.logger.info(f"Found {len(datetime_columns)} datetime columns in table {table.name}")
        
        # The central date table should already be created.
        if not hasattr(data_model, 'date_tables') or not data_model.date_tables:
            self.logger.warning(f"Central date table not found. Skipping date relationship creation for table {table.name}.")
            return
        
        central_date_table = data_model.date_tables[0]
        date_table_name = central_date_table['name']

        # The first datetime column (alphabetically) will have the active relationship.
        primary_column = datetime_columns[0]
        
        # Create relationships for all datetime columns
        for i, column in enumerate(datetime_columns):
            is_active = (i == 0) # Only the first relationship is active
            relationship_id = str(uuid.uuid4())
            
            relationship = Relationship(
                id=relationship_id,
                from_table=table.name,
                from_column=f"{table.name}.{column.name}",
                to_table=date_table_name,
                to_column="Date",
                cross_filtering_behavior="automatic",
                join_on_date_behavior="datePartOnly",
                is_active=is_active
            )
            
            data_model.relationships.append(relationship)
            self.logger.info(f"Created relationship for {table.name}[{column.name}] to {date_table_name}[Date] (Active: {is_active})")

            # Store relationship info in the column's metadata for the active relationship's variation.
            # Only one column in the entire model can have this default variation, and only in 'hidden' mode.
            if is_active and data_model.date_table_mode == 'hidden' and not data_model.has_primary_date_variation:
                if not hasattr(column, 'metadata'):
                    column.metadata = {}
                column.metadata['relationship_info'] = {
                    'id': relationship_id,
                    'hierarchy': f"{date_table_name}.'Date Hierarchy'"
                }
                # Set the flag so no other column gets the variation
                data_model.has_primary_date_variation = True
                self.logger.info(f"Designated {table.name}[{column.name}] as the primary date variation for the model.")
            elif not is_active:
                # For inactive relationships, create a DAX measure
                measure_name = f"{table.name} - Count by {column.name}"
                expression = (
                    f"CALCULATE(\n"
                    f"    COUNTROWS('{table.name}'),\n"
                    f"    USERELATIONSHIP('{date_table_name}'[Date], '{table.name}'[{column.name}])\n"
                    f")"
                )
                measure = Measure(name=measure_name, expression=expression)
                
                if not hasattr(table, 'measures'):
                    table.measures = []
                
                if not any(m.name == measure_name for m in table.measures):
                    table.measures.append(measure)
                    self.logger.info(f"Created DAX measure '{measure_name}' for inactive relationship on {table.name}[{column.name}]")

    def _create_central_date_table(self, data_model: DataModel) -> None:
        """Creates a single, central date table for the data model."""
        self.logger.info("Creating a single central date table for the model.")

        # Determine which template to use based on the mode
        template_filename = f"DateTableTemplate_{data_model.date_table_mode.capitalize()}.tmdl"
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'templates', template_filename)
        
        if not os.path.exists(template_path):
            self.logger.warning(f"{template_filename} not found at {template_path}. Skipping central date table creation.")
            return
        
        # Read the template content
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read DateTableTemplate.tmdl: {e}")
            return
        
        # Initialize date_tables attribute if it doesn't exist
        if not hasattr(data_model, 'date_tables'):
            data_model.date_tables = []
        
        # Create the central date table
        date_table_name = "CentralDateTable"
        
        data_model.date_tables.append({
            'id': str(uuid.uuid4()),
            'name': date_table_name,
            'template_content': template_content.replace('DateTableTemplate_19728d8e-9427-4914-8bc5-607973681b1e', date_table_name)
        })
        
        self.logger.info(f"Successfully created central date table: {date_table_name}")

    def _find_referenced_table(self, model_qs: Dict[str, Any], data_model: DataModel) -> Optional[Table]:
        """Find the table referenced by a model query subject
        
        Args:
            model_qs: Model query subject dictionary
            data_model: Data model containing tables
            
        Returns:
            Table referenced by the model query, or None if not found
        """
        model_name = model_qs['name'].lower()
        self.logger.info(f"Finding referenced table for model query {model_qs['name']}")
        
        # First, try direct name matching with special handling for Territory/tblTerritory case
        for table in data_model.tables:
            table_name = table.name.lower()
            
            # Direct match
            if table_name == model_name:
                self.logger.info(f"Found direct name match: {table.name}")
                return table
                
            # Special case for Territory/tblTerritory
            if model_name == 'territory' and table_name == 'tblterritory':
                self.logger.info(f"Found Territory/tblTerritory match: {table.name}")
                return table
                
            # Check for tbl prefix
            if table_name == f"tbl{model_name}" or (table_name.startswith('tbl') and table_name[3:] == model_name):
                self.logger.info(f"Found match with tbl prefix: {table.name}")
                return table
        
        # If direct name matching didn't work, try SQL-based matching
        if 'sql_definition' in model_qs and model_qs['sql_definition'] and 'sql' in model_qs['sql_definition']:
            sql = model_qs['sql_definition']['sql']
            self.logger.info(f"Trying SQL-based matching with SQL: {sql[:100]}...")
            
            # Try to extract table name from SQL using regex
            # Look for FROM clause
            from_match = re.search(r'\bFROM\s+\[?[\w\.]+\]?\.([\w]+)', sql, re.IGNORECASE)
            if from_match:
                table_name = from_match.group(1)
                self.logger.info(f"Extracted table name from FROM clause: {table_name}")
                
                # Look for a matching table in the data model
                for table in data_model.tables:
                    if table.name.lower() == table_name.lower() or \
                       (table.metadata and 'original_name' in table.metadata and \
                        table.metadata['original_name'].lower() == table_name.lower()):
                        self.logger.info(f"Found matching table from SQL: {table.name}")
                        return table
            
            # If FROM clause didn't work, try JOIN clauses
            join_matches = re.findall(r'\bJOIN\s+\[?[\w\.]+\]?\.([\w]+)', sql, re.IGNORECASE)
            if join_matches:
                for join_table in join_matches:
                    table_name = join_table.split('.')[-1]  # Get the last part after any schema/db qualifier
                    self.logger.info(f"Extracted table name from JOIN clause: {table_name}")
                    
                    # Look for a matching table in the data model
                    for table in data_model.tables:
                        if table.name.lower() == table_name.lower() or \
                           (table.metadata and 'original_name' in table.metadata and \
                            table.metadata['original_name'].lower() == table_name.lower()):
                            self.logger.info(f"Found matching table from JOIN: {table.name}")
                            return table
        
        # If all else fails, try fuzzy matching based on name similarity
        for table in data_model.tables:
            table_name = table.name.lower()
            
            # Check if one name contains the other
            if model_name in table_name or table_name in model_name:
                self.logger.info(f"Found fuzzy name match: {table.name}")
                return table
                
        self.logger.warning(f"Could not find referenced table for model query {model_qs['name']}")
        return None

    def _enhance_table_with_model_query(self, model_qs: Dict[str, Any], table: Table, data_model: DataModel) -> None:
        """Enhance an existing table with information from a model query
        
        Args:
            model_qs: Model query subject dictionary
            table: Table to enhance
        """
        # If the model query has a more detailed SQL, use it instead of the simple dbQuery
        if 'sql_definition' in model_qs and model_qs['sql_definition'] and 'sql' in model_qs['sql_definition']:
            model_sql = model_qs['sql_definition']['sql']
            
            # Only replace if the current SQL is a simple SELECT * query or doesn't exist
            if not table.source_query or 'select * from' in table.source_query.lower():
                self.logger.info(f"Replacing simple SQL with more detailed model query for table {table.name}")
                self.logger.info(f"  Original SQL: {table.source_query}")
                self.logger.info(f"  New SQL from {model_qs['name']}: {model_sql[:100]}...")
                table.source_query = model_sql
                
                # Add a note that this table was enhanced with a model query
                table.metadata = table.metadata or {}
                table.metadata['enhanced_with_model_query'] = model_qs['name']
        
        # First, deduplicate existing columns in the table by name
        self._deduplicate_columns(table)
            
        # Add any additional columns from the model query that don't exist in the table
        model_columns = {item['name'].lower(): item for item in model_qs.get('items', [])}
        table_columns = {col.name.lower(): col for col in table.columns}
        
        for col_name, item in model_columns.items():
            if col_name not in table_columns:
                # Get the data type from the item
                cognos_type = item.get('datatype', 'string')
                
                # Map Cognos data type to Power BI data type
                if cognos_type.lower() in ['int32', 'int64']:
                    data_type = DataType.INTEGER
                elif cognos_type.lower() in ['float', 'double']:
                    data_type = DataType.DOUBLE
                elif cognos_type.lower() == 'boolean':
                    data_type = DataType.BOOLEAN
                elif cognos_type.lower() in ['date', 'time', 'timestamp']:
                    data_type = DataType.DATE
                else:
                    data_type = DataType.STRING
                    
                # Create and add the new column
                new_column = Column(
                    name=item['name'],
                    data_type=data_type,
                    source_column=item.get('source_column', item['name'])
                )
                table.columns.append(new_column)
                self.logger.info(f"Added column {new_column.name} from model query to table {table.name}")
                
        # Update the table name to the model query name if it's more business-friendly
        # (e.g., "Territory" instead of "tblTerritory")
        if table.name.lower().startswith('tbl') and not model_qs['name'].lower().startswith('tbl'):
            self.logger.info(f"Updating table name from {table.name} to {model_qs['name']} (more business-friendly)")
            
            # Store the original name in metadata for relationship updates
            original_name = table.name
            table.metadata = table.metadata or {}
            table.metadata['original_name'] = original_name
            
            # Update the name
            new_name = model_qs['name']
            table.name = new_name

            # Update all existing relationships that point to the old table name
            for rel in data_model.relationships:
                if rel.from_table == original_name:
                    rel.from_table = new_name
                    self.logger.info(f"Updated relationship from_table from {original_name} to {new_name}")
                if rel.to_table == original_name:
                    rel.to_table = new_name
                    self.logger.info(f"Updated relationship to_table from {original_name} to {new_name}")
            
            # Also update the DAX expressions of any measures on this table
            if hasattr(table, 'measures'):
                for measure in table.measures:
                    # Use a regex to replace the old table name, case-insensitively
                    # This is safer than a simple string replace
                    old_expression = measure.expression
                    measure.expression = re.sub(f"'{re.escape(original_name)}'", f"'{new_name}'", old_expression, flags=re.IGNORECASE)
                    if old_expression != measure.expression:
                        self.logger.info(f"Updated measure '{measure.name}' DAX from using '{original_name}' to '{new_name}'")
