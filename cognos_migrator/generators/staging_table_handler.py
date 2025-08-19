"""
Staging table handler for Power BI model generation.

This module handles the creation and management of staging tables
based on settings in the settings.json file.
"""
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

from ..models import DataModel, Table, Relationship, Column, DataType


class StagingTableHandler:
    """
    Handler for creating and managing staging tables based on settings.
    
    This class is responsible for:
    1. Reading staging table settings from settings.json
    2. Creating staging tables based on the specified model_handling approach
    3. Modifying relationships to use staging tables when appropriate
    4. Integrating staging tables into the data model
    """
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None, extracted_dir: Optional[Path] = None, mquery_converter: Optional[Any] = None):
        """
        Initialize the staging table handler.
        
        Args:
            settings: Optional settings dictionary. If not provided, will attempt to load from settings.json
            extracted_dir: Optional path to extracted directory containing SQL relationships
            mquery_converter: Optional MQueryConverter from package migration for generating proper M-queries
        """
        self.logger = logging.getLogger(__name__)
        self.extracted_dir = extracted_dir
        self.mquery_converter = mquery_converter
        
        # Load settings if not provided
        if settings is None:
            settings_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / 'settings.json'
            if settings_path.exists():
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    self.logger.info(f"Loaded settings from {settings_path}")
                except Exception as e:
                    self.logger.warning(f"Error loading settings from {settings_path}: {e}")
                    settings = {}
            else:
                self.logger.warning(f"Settings file not found at {settings_path}")
                settings = {}
        
        # Extract staging table settings
        self.staging_settings = settings.get('staging_tables', {})
        self.enabled = self.staging_settings.get('enabled', False)
        self.naming_prefix = self.staging_settings.get('naming_prefix', 'stg_')
        self.model_handling = self.staging_settings.get('model_handling', 'none')
        
        # Log settings
        self.logger.info(f"Staging table settings: enabled={self.enabled}, "
                         f"naming_prefix={self.naming_prefix}, "
                         f"model_handling={self.model_handling}")
        
        # Load SQL relationships if extracted directory is provided
        self.sql_relationships = []
        if self.extracted_dir and self.enabled:
            self._load_sql_relationships()
    
    def _load_sql_relationships(self) -> None:
        """Load SQL relationships from sql_filtered_relationships.json if available"""
        try:
            sql_rel_file = self.extracted_dir / "sql_filtered_relationships.json"
            if sql_rel_file.exists():
                with open(sql_rel_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sql_relationships = data.get('sql_relationships', [])
                self.logger.info(f"Loaded {len(self.sql_relationships)} SQL relationships from {sql_rel_file}")
            else:
                self.logger.warning(f"SQL relationships file not found at {sql_rel_file}")
        except Exception as e:
            self.logger.error(f"Error loading SQL relationships: {e}")
            self.sql_relationships = []
    
    def process_data_model(self, data_model: DataModel) -> DataModel:
        """
        Process a data model to add staging tables based on settings.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with staging tables added if enabled
        """
        # If staging tables are not enabled or model_handling is 'none', return the original model
        if not self.enabled or self.model_handling == 'none':
            self.logger.info("Staging tables are disabled or set to 'none', returning original model")
            return data_model
        
        self.logger.info(f"Processing data model for staging tables with model_handling={self.model_handling}")
        
        # Create staging tables based on model_handling approach
        if self.model_handling == 'merged_tables':
            return self._process_merged_tables(data_model)
        elif self.model_handling == 'star_schema':
            return self._process_star_schema(data_model)
        else:
            self.logger.warning(f"Unknown model_handling value: {self.model_handling}, returning original model")
            return data_model
    
    def _process_merged_tables(self, data_model: DataModel) -> DataModel:
        """
        Process data model using the 'merged_tables' approach.
        
        In this approach, staging tables are created and merged with the original tables,
        preserving the original table structure while adding the necessary columns for complex joins.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with merged staging tables
        """
        self.logger.info("Processing data model with 'merged_tables' approach")
        
        # Identify tables involved in complex relationships
        complex_tables = self._identify_complex_relationship_tables(data_model.relationships)
        self.logger.info(f"Identified {len(complex_tables)} tables involved in complex relationships")
        
        # Create merged tables for complex tables
        new_tables = []
        for table in data_model.tables:
            if table.name in complex_tables:
                # Create a merged table with staging prefix
                merged_table = self._create_merged_table(table, data_model)
                new_tables.append(merged_table)
                self.logger.info(f"Created merged table {merged_table.name} for {table.name}")
            else:
                # Keep original table
                new_tables.append(table)
        
        # Update relationships to use merged tables
        new_relationships = self._update_relationships_for_merged_tables(
            data_model.relationships, complex_tables)
        
        # Create new data model with updated tables and relationships
        new_data_model = DataModel(
            name=data_model.name,
            tables=new_tables,
            relationships=new_relationships,
            compatibility_level=data_model.compatibility_level
        )
        
        # Copy any additional attributes from the original data model
        for attr, value in vars(data_model).items():
            if attr not in ['name', 'tables', 'relationships', 'compatibility_level']:
                setattr(new_data_model, attr, value)
        
        self.logger.info(f"Processed data model with 'merged_tables' approach: "
                         f"{len(new_tables)} tables, {len(new_relationships)} relationships")
        return new_data_model
    
    def _process_star_schema(self, data_model: DataModel) -> DataModel:
        """
        Process data model using the 'star_schema' approach.
        
        In this approach, staging tables are created as separate entities in a star schema design,
        with columns based on join keys in relationships. Each staging table will have its own
        M-query that combines data from related tables.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with star schema staging tables
        """
        self.logger.info("Processing data model with 'star_schema' approach")
        
        # Use SQL relationships if available, otherwise fall back to basic relationships
        if self.sql_relationships:
            self.logger.info(f"Using {len(self.sql_relationships)} SQL relationships for staging tables")
            complex_relationships = self._identify_complex_sql_relationships(self.sql_relationships)
        else:
            self.logger.info("Using basic data model relationships for staging tables")
            complex_relationships = self._identify_complex_relationships(data_model.relationships)
        
        self.logger.info(f"Identified {len(complex_relationships)} complex relationships that need staging tables")
        
        if not complex_relationships:
            self.logger.info("No complex relationships found, returning original model")
            return data_model
        
        # Group relationships by tables they connect
        if self.sql_relationships:
            relationship_groups = self._group_sql_relationships_by_tables(complex_relationships)
        else:
            relationship_groups = self._group_relationships_by_tables(complex_relationships)
        
        self.logger.info(f"Grouped complex relationships into {len(relationship_groups)} groups")
        
        # Create dimension tables from relationship groups
        new_tables = list(data_model.tables)  # Start with all original tables
        dimension_tables = []
        dimension_table_map = {}  # Maps original table pairs to dimension tables
        
        for group_key, relationships in relationship_groups.items():
            # Extract table names from the group key
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            
            # Find the original tables
            from_table = next((t for t in data_model.tables if t.name == from_table_name), None)
            to_table = next((t for t in data_model.tables if t.name == to_table_name), None)
            
            if not from_table or not to_table:
                continue
                
            # Create a dimension table for this relationship group
            dimension_table_name = f"Dim_{from_table_name}_{to_table_name}"
            
            # Get all columns needed for the relationships in this group
            if self.sql_relationships:
                columns = self._extract_columns_for_staging_table_from_sql(relationships, from_table, to_table)
            else:
                columns = self._extract_columns_for_staging_table(relationships, from_table, to_table)
            
            # Create the dimension table with composite key
            dimension_table = self._create_dimension_table_with_composite_key(dimension_table_name, columns, relationships, from_table, to_table)
            new_tables.append(dimension_table)
            dimension_tables.append(dimension_table)
            dimension_table_map[group_key] = dimension_table_name
            
            self.logger.info(f"Created dimension table {dimension_table_name} with {len(columns)} columns plus composite key")
        
        # Create new relationships using dimension tables with single composite key
        new_relationships = []
        
        for group_key, relationships in relationship_groups.items():
            if group_key not in dimension_table_map:
                continue
                
            dimension_table_name = dimension_table_map[group_key]
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            
            # Create relationships between dimension table and original tables using composite key
            if self.sql_relationships:
                # For SQL relationships, create relationships using composite key
                self._create_dimension_relationships_from_sql(relationships, dimension_table_name, 
                                                          from_table_name, to_table_name, new_relationships)
            else:
                # Use the original logic for basic relationships with composite key
                composite_key_name = self._get_composite_key_name(relationships)
                for rel in relationships:
                    # Create relationship from dimension table to from_table
                    from_rel = Relationship(
                        id=f"Dim_{rel.id}_From",
                        from_table=dimension_table_name,
                        from_column=composite_key_name,
                        to_table=from_table_name,
                        to_column=composite_key_name,
                        from_cardinality="one",
                        to_cardinality="many",
                        cross_filtering_behavior="OneDirection",
                        is_active=True
                    )
                    new_relationships.append(from_rel)
                    
                    # Create relationship from dimension table to to_table
                    to_rel = Relationship(
                        id=f"Dim_{rel.id}_To",
                        from_table=dimension_table_name,
                        from_column=composite_key_name,
                        to_table=to_table_name,
                        to_column=composite_key_name,
                        from_cardinality="one",
                        to_cardinality="many",
                        cross_filtering_behavior="OneDirection",
                        is_active=True
                    )
                    new_relationships.append(to_rel)
                    
                    self.logger.info(f"Created dimension relationships for {rel.id} using {dimension_table_name}")
        
        # Remove old relationships that are now handled by dimension tables
        final_relationships = self._filter_replaced_relationships(new_relationships, relationship_groups)
        
        # Create new data model with updated tables and relationships
        new_data_model = DataModel(
            name=data_model.name,
            tables=new_tables,
            relationships=final_relationships,
            compatibility_level=data_model.compatibility_level
        )
        
        # Add composite keys to fact tables
        new_data_model = self._add_composite_keys_to_fact_tables(new_data_model, relationship_groups)
        
        # Save dimension and updated fact tables as JSON files
        if self.extracted_dir:
            self._save_updated_tables_as_json(new_data_model, dimension_tables, relationship_groups)
        
        # Copy any additional attributes from the original data model
        for attr, value in vars(data_model).items():
            if attr not in ['name', 'tables', 'relationships', 'compatibility_level']:
                setattr(new_data_model, attr, value)
        
        self.logger.info(f"Processed data model with 'star_schema' approach: "
                         f"{len(new_data_model.tables)} tables, {len(new_relationships)} relationships")
        return new_data_model
    
    def _save_updated_tables_as_json(self, data_model: DataModel, dimension_tables: List[Table], relationship_groups: Dict[str, List]) -> None:
        """
        Save dimension tables and updated fact tables as JSON files for TMDL generation.
        
        Args:
            data_model: The updated data model
            dimension_tables: List of dimension tables to save
            relationship_groups: Relationship groups used to identify fact tables
        """
        import json
        from datetime import datetime
        
        self.logger.info("Saving dimension and updated fact tables as JSON files")
        
        # Get list of fact table names that were updated with composite keys
        fact_table_names = set()
        for group_key, relationships in relationship_groups.items():
            table_names = group_key.split(':')
            if len(table_names) == 2:
                fact_table_names.update(table_names)
        
        # Save dimension tables
        for dim_table in dimension_tables:
            self._save_table_as_json(dim_table, self.extracted_dir)
            self.logger.info(f"Saved dimension table JSON: {dim_table.name}")
        
        # Don't save fact tables - let package migration handle them
        # The staging table handler only saves dimension tables
        # Fact tables will be processed by the package migration with composite keys added to the data model
    
    def _save_table_as_json(self, table: Table, extracted_dir: Path) -> None:
        """
        Save a single table as JSON file.
        
        Args:
            table: Table object to save
            extracted_dir: Directory to save the JSON file
        """
        import json
        
        # Build table JSON structure
        table_json = {
            "source_name": table.name,
            "name": table.name,
            "lineage_tag": None,
            "description": None,
            "is_hidden": False,
            "columns": []
        }
        
        # Add columns
        for col in table.columns:
            column_json = {
                "source_name": col.name,
                "datatype": col.data_type.value if hasattr(col, 'data_type') and hasattr(col.data_type, 'value') and col.data_type else "string",
                "format_string": None,
                "lineage_tag": None,
                "source_column": col.source_column if hasattr(col, 'source_column') else col.name,
                "description": None,
                "is_hidden": getattr(col, 'is_hidden', False),
                "summarize_by": getattr(col, 'summarize_by', 'none'),
                "data_category": None,
                "is_calculated": False,
                "is_data_type_inferred": True,
                "annotations": {
                    "SummarizationSetBy": "Automatic"
                }
            }
            table_json["columns"].append(column_json)
        
        # Add hierarchies (empty for now)
        table_json["hierarchies"] = []
        
        # Generate M-query - use separate functions for dimension vs fact tables
        if table.name.startswith('Dim_'):
            # For dimension tables, use the M-query that was already generated
            m_query = getattr(table, 'source_query', None)
        else:
            # For fact tables, generate M-query with composite keys
            m_query = self._generate_proper_m_query_with_composite_keys(table)
        
        # Add partitions with M-query
        partitions = []
        if m_query:
            partitions.append({
                "name": table.name,
                "source_type": "m",
                "expression": m_query
            })
        
        table_json["partitions"] = partitions
        table_json["has_widget_serialization"] = False
        table_json["visual_type"] = None
        table_json["column_settings"] = None
        
        # Save to file
        json_file = extracted_dir / f"table_{table.name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(table_json, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved table JSON file: {json_file}")
        
    def _identify_complex_relationships(self, relationships: List[Relationship]) -> List[Relationship]:
        """
        Identify relationships that are complex and require staging tables.
        
        A complex relationship is one where:
        1. A table has multiple relationships with the same table
        2. A table has composite key relationships (multiple columns in the join)
        
        Args:
            relationships: List of relationships to analyze
            
        Returns:
            List of relationships that are considered complex
        """
        complex_relationships = []
        relationship_counts = {}
        
        # Count relationships between each pair of tables
        for rel in relationships:
            pair_key = f"{rel.from_table}:{rel.to_table}"
            if pair_key not in relationship_counts:
                relationship_counts[pair_key] = 0
            relationship_counts[pair_key] += 1
            
            # Check for composite keys (indicated by multiple columns)
            if ',' in (rel.from_column or '') or ',' in (rel.to_column or ''):
                complex_relationships.append(rel)
                self.logger.info(f"Identified complex relationship with composite key: "
                                 f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
        
        # Add relationships where tables have multiple relationships between them
        for rel in relationships:
            pair_key = f"{rel.from_table}:{rel.to_table}"
            if relationship_counts[pair_key] > 1 and rel not in complex_relationships:
                complex_relationships.append(rel)
                self.logger.info(f"Identified complex relationship: {rel.from_table} has multiple relationships with {rel.to_table}")
        
        return complex_relationships
        
    def _group_relationships_by_tables(self, relationships: List[Relationship]) -> Dict[str, List[Relationship]]:
        """
        Group relationships by the tables they connect.
        
        Args:
            relationships: List of relationships to group
            
        Returns:
            Dictionary mapping table pairs to lists of relationships
        """
        groups = {}
        
        for rel in relationships:
            # Create a consistent key for the table pair
            if rel.from_table < rel.to_table:
                key = f"{rel.from_table}:{rel.to_table}"
            else:
                key = f"{rel.to_table}:{rel.from_table}"
                
            if key not in groups:
                groups[key] = []
                
            groups[key].append(rel)
            
        return groups
        
    def _extract_columns_for_staging_table(self, relationships: List[Relationship], 
                                           from_table: Table, to_table: Table) -> List[Dict[str, str]]:
        """
        Extract columns needed for a staging table based on relationships.
        
        Args:
            relationships: List of relationships that will use this staging table
            from_table: The 'from' table in the relationships
            to_table: The 'to' table in the relationships
            
        Returns:
            List of column definitions for the staging table
        """
        columns = []
        column_names = set()
        
        # Extract columns from relationships
        for rel in relationships:
            # Add from_column if not already added
            if rel.from_column and rel.from_column not in column_names:
                column_names.add(rel.from_column)
                columns.append({
                    'name': rel.from_column,
                    'dataType': 'string',  # Default to string, can be refined later
                    'summarizeBy': 'none',
                    'sourceColumn': rel.from_column
                })
                
            # Add to_column if not already added
            if rel.to_column and rel.to_column not in column_names:
                column_names.add(rel.to_column)
                columns.append({
                    'name': rel.to_column,
                    'dataType': 'string',  # Default to string, can be refined later
                    'summarizeBy': 'none',
                    'sourceColumn': rel.to_column
                })
        
        return columns
        
    def _create_staging_table_with_columns(self, table_name: str, columns: List[Dict[str, str]], 
                                          relationships: List[Relationship]) -> Table:
        """
        Create a staging table with specific columns and M-query.
        
        Args:
            table_name: Name for the staging table
            columns: List of column definitions
            relationships: List of relationships that will use this staging table
            
        Returns:
            A new Table object representing the staging table
        """
        # Create Column objects from column definitions
        column_objects = []
        for col_def in columns:
            col = Column(
                name=col_def['name'],
                data_type=col_def['dataType'],
                source_column=col_def['sourceColumn']
            )
            # Add additional properties
            col.summarize_by = col_def['summarizeBy']
            column_objects.append(col)
            
        # Extract table names from relationships for M-query generation
        source_tables = set()
        for rel in relationships:
            if isinstance(rel, dict):
                # SQL relationship dictionary
                source_tables.add(rel.get('table_a_one_side', ''))
                source_tables.add(rel.get('table_b_many_side', ''))
            else:
                # Relationship object
                source_tables.add(rel.from_table)
                source_tables.add(rel.to_table)
        
        # Remove empty strings
        source_tables.discard('')
        
        # Generate M-query for the staging table
        m_query = self._generate_staging_table_m_query(table_name, column_objects, list(source_tables))
        
        # Create metadata
        metadata = {
            'is_staging_table': True,
            'source_tables': list(source_tables),
            'is_source_table': False
        }
        
        # Create the staging table
        staging_table = Table(
            name=table_name,
            columns=column_objects,
            source_query=m_query,
            metadata=metadata
        )
        
        return staging_table
        
    def _generate_staging_table_m_query(self, table_name: str, columns: List[Column], 
                                       source_tables: List[str]) -> str:
        """
        Generate an M-query for a staging table.
        
        Args:
            table_name: Name of the staging table
            columns: List of columns in the staging table
            source_tables: List of source tables to extract data from
            
        Returns:
            M-query string for the staging table
        """
        # Extract column names for the query
        column_names = [col.name for col in columns]
        column_list = '", "'.join(column_names)
        
        # Build the M-query
        m_query_parts = ["let"]
        
        # Add steps for each source table
        for i, source_table in enumerate(source_tables):
            step_name = f"Data_From_{source_table.replace(' ', '_')}"
            m_query_parts.append(f"    // Get data from {source_table}")
            m_query_parts.append(f"    {step_name} = Table.SelectColumns({source_table},{{\"{ column_list }\"}}),")
            m_query_parts.append(f"    Distinct_{i} = Table.Distinct({step_name}),")
            
        # Combine data from all source tables
        if len(source_tables) > 1:
            combine_tables = [f"Distinct_{i}" for i in range(len(source_tables))]
            combine_list = ", ".join(combine_tables)
            m_query_parts.append(f"    // Combine data from all source tables")
            m_query_parts.append(f"    CombinedData = Table.Combine({{{combine_list}}}),")
            m_query_parts.append(f"    UniqueRows = Table.Distinct(CombinedData),")
            final_step = "UniqueRows"
        else:
            final_step = "Distinct_0"
        
        # Remove the trailing comma from the last step
        m_query_parts[-1] = m_query_parts[-1].rstrip(",")
        
        # Add the final in clause
        m_query_parts.append(f"in")
        m_query_parts.append(f"    {final_step}")
        
        # Join all parts with newlines
        m_query = "\n".join(m_query_parts)
        
        return m_query
        
    def _is_relationship_in_list(self, rel: Relationship, rel_list: List[Relationship]) -> bool:
        """
        Check if a relationship is in a list of relationships.
        
        Args:
            rel: The relationship to check
            rel_list: The list of relationships to check against
            
        Returns:
            True if the relationship is in the list, False otherwise
        """
        for r in rel_list:
            if r.id == rel.id:
                return True
        return False
    
    def _create_merged_table(self, original_table: Table, data_model: DataModel) -> Table:
        """
        Create a merged table that combines the original table with staging columns.
        
        Args:
            original_table: The original table to merge with staging columns
            data_model: The data model containing all tables and relationships
            
        Returns:
            A new table with merged columns
        """
        # Create a new table with staging prefix
        merged_name = f"{self.naming_prefix}{original_table.name}"
        
        # Copy all columns from the original table
        columns = list(original_table.columns)
        
        # Add metadata to indicate this is a staging table
        metadata = dict(original_table.metadata) if hasattr(original_table, 'metadata') else {}
        metadata['is_staging_table'] = True
        metadata['original_table'] = original_table.name
        
        # Create the merged table
        merged_table = Table(
            name=merged_name,
            columns=columns,
            source_query=original_table.source_query,
            metadata=metadata
        )
        
        # Copy any additional attributes from the original table
        for attr, value in vars(original_table).items():
            if attr not in ['name', 'columns', 'source_query', 'metadata']:
                setattr(merged_table, attr, value)
        
        return merged_table
    
    def _create_staging_table(self, original_table: Table) -> Table:
        """
        Create a staging table based on an original table.
        
        Args:
            original_table: The original table to create a staging table for
            
        Returns:
            A new staging table
        """
        # Create a new table with staging prefix
        staging_name = f"{self.naming_prefix}{original_table.name}"
        
        # Copy key columns from the original table
        # For now, we'll copy all columns, but this could be optimized
        columns = list(original_table.columns)
        
        # Add metadata to indicate this is a staging table
        metadata = dict(original_table.metadata) if hasattr(original_table, 'metadata') else {}
        metadata['is_staging_table'] = True
        metadata['original_table'] = original_table.name
        
        # Create the staging table with the same source query
        staging_table = Table(
            name=staging_name,
            columns=columns,
            source_query=original_table.source_query,
            metadata=metadata
        )
        
        return staging_table
    
    def _update_relationships_for_merged_tables(
            self, relationships: List[Relationship], complex_tables: Set[str]) -> List[Relationship]:
        """
        Update relationships to use merged tables for complex relationships.
        
        Args:
            relationships: List of original relationships
            complex_tables: Set of table names involved in complex relationships
            
        Returns:
            List of updated relationships
        """
        new_relationships = []
        
        for rel in relationships:
            # If either table is a complex table, update the relationship
            if rel.from_table in complex_tables or rel.to_table in complex_tables:
                new_rel = Relationship(
                    id=rel.id,
                    from_table=f"{self.naming_prefix}{rel.from_table}" if rel.from_table in complex_tables else rel.from_table,
                    from_column=rel.from_column,
                    to_table=f"{self.naming_prefix}{rel.to_table}" if rel.to_table in complex_tables else rel.to_table,
                    to_column=rel.to_column,
                    from_cardinality=rel.from_cardinality,
                    to_cardinality=rel.to_cardinality,
                    cross_filtering_behavior=rel.cross_filtering_behavior,
                    is_active=rel.is_active,
                    join_on_date_behavior=rel.join_on_date_behavior
                )
                new_relationships.append(new_rel)
                self.logger.info(f"Updated relationship to use merged tables: "
                                 f"{new_rel.from_table}.{new_rel.from_column} -> "
                                 f"{new_rel.to_table}.{new_rel.to_column}")
            else:
                # Keep the original relationship
                new_relationships.append(rel)
        
        return new_relationships
    
    def _update_relationships_for_star_schema(
            self, relationships: List[Relationship], staging_tables: Dict[str, str]) -> List[Relationship]:
        """
        Update relationships to use staging tables in a star schema approach.
        
        Args:
            relationships: List of original relationships
            staging_tables: Dictionary mapping original table names to staging table names
            
        Returns:
            List of updated relationships for complex joins
        """
        new_relationships = []
        
        for rel in relationships:
            # If both tables have staging tables, create a relationship between the staging tables
            if rel.from_table in staging_tables and rel.to_table in staging_tables:
                new_rel = Relationship(
                    id=f"Staging_{rel.id}",
                    from_table=staging_tables[rel.from_table],
                    from_column=rel.from_column,
                    to_table=staging_tables[rel.to_table],
                    to_column=rel.to_column,
                    from_cardinality=rel.from_cardinality,
                    to_cardinality=rel.to_cardinality,
                    cross_filtering_behavior=rel.cross_filtering_behavior,
                    is_active=rel.is_active,
                    join_on_date_behavior=rel.join_on_date_behavior
                )
                new_relationships.append(new_rel)
                self.logger.info(f"Created staging relationship: "
                                 f"{new_rel.from_table}.{new_rel.from_column} -> "
                                 f"{new_rel.to_table}.{new_rel.to_column}")
        
        return new_relationships
    
    def _identify_primary_key(self, table: Table, relationships: List[Relationship]) -> Optional[str]:
        """
        Identify the primary key of a table based on relationships.
        
        Args:
            table: The table to identify the primary key for
            relationships: List of relationships to analyze
            
        Returns:
            The name of the primary key column, or None if not found
        """
        # Look for columns that are used in relationships where this table is on the "one" side
        potential_keys = []
        
        for rel in relationships:
            if rel.from_table == table.name and rel.from_cardinality == "one":
                potential_keys.append(rel.from_column)
            elif rel.to_table == table.name and (rel.to_cardinality == "one" or rel.from_cardinality == "many"):
                potential_keys.append(rel.to_column)
        
        # Use the most common column as the primary key
        if potential_keys:
            from collections import Counter
            key_counts = Counter(potential_keys)
            primary_key = key_counts.most_common(1)[0][0]
            return primary_key
        
        # If no relationships indicate a primary key, look for common naming patterns
        for col in table.columns:
            col_name = col.name.lower()
            if col_name.endswith('_id') or col_name == 'id' or col_name == table.name.lower() + '_id':
                return col.name
        
        # If still no primary key found, use the first column
        if table.columns:
            return table.columns[0].name
        
        return None
    
    def _is_complex_relationship(self, relationship: Relationship, complex_tables: Set[str]) -> bool:
        """
        Determine if a relationship is complex based on the tables involved.
        
        Args:
            relationship: The relationship to check
            complex_tables: Set of table names involved in complex relationships
            
        Returns:
            True if the relationship is complex, False otherwise
        """
        return relationship.from_table in complex_tables and relationship.to_table in complex_tables

    def _identify_complex_sql_relationships(self, sql_relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify SQL relationships that are complex and require staging tables.
        
        A complex SQL relationship is one where:
        1. It has composite keys (multiple columns in join keys)
        2. It's marked with staging_table_reason
        
        Args:
            sql_relationships: List of SQL relationships to analyze
            
        Returns:
            List of SQL relationships that are considered complex
        """
        complex_relationships = []
        
        for rel in sql_relationships:
            # Check if it has composite keys or is marked for staging tables
            keys_a = rel.get('keys_a', [])
            keys_b = rel.get('keys_b', [])
            staging_reason = rel.get('staging_table_reason')
            
            if len(keys_a) > 1 or len(keys_b) > 1 or staging_reason:
                complex_relationships.append(rel)
                self.logger.info(f"Identified complex SQL relationship: {rel['relationship_name']} "
                               f"with {len(keys_a)} keys A and {len(keys_b)} keys B, reason: {staging_reason}")
        
        return complex_relationships
    
    def _group_sql_relationships_by_tables(self, sql_relationships: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group SQL relationships by the tables they connect.
        
        Args:
            sql_relationships: List of SQL relationships to group
            
        Returns:
            Dictionary mapping table pairs to lists of SQL relationships
        """
        groups = {}
        
        for rel in sql_relationships:
            table_a = rel.get('table_a_one_side', '')
            table_b = rel.get('table_b_many_side', '')
            
            # Create a consistent key for the table pair
            if table_a < table_b:
                key = f"{table_a}:{table_b}"
            else:
                key = f"{table_b}:{table_a}"
                
            if key not in groups:
                groups[key] = []
                
            groups[key].append(rel)
            
        return groups
    
    def _extract_columns_for_staging_table_from_sql(self, sql_relationships: List[Dict[str, Any]], 
                                                   from_table: Table, to_table: Table) -> List[Dict[str, str]]:
        """
        Extract columns needed for a staging table based on SQL relationships.
        
        Args:
            sql_relationships: List of SQL relationships that will use this staging table
            from_table: The 'from' table in the relationships
            to_table: The 'to' table in the relationships
            
        Returns:
            List of column definitions for the staging table
        """
        columns = []
        column_names = set()
        
        # Extract columns from SQL relationships
        for rel in sql_relationships:
            keys_a = rel.get('keys_a', [])
            keys_b = rel.get('keys_b', [])
            
            # Add all keys from both sides
            for key in keys_a:
                if key and key not in column_names:
                    column_names.add(key)
                    columns.append({
                        'name': key,
                        'dataType': 'string',  # Default to string, can be refined later
                        'summarizeBy': 'none',
                        'sourceColumn': key
                    })
                    
            for key in keys_b:
                if key and key not in column_names:
                    column_names.add(key)
                    columns.append({
                        'name': key,
                        'dataType': 'string',  # Default to string, can be refined later
                        'summarizeBy': 'none',
                        'sourceColumn': key
                    })
        
        self.logger.info(f"Extracted {len(columns)} columns from SQL relationships: {[col['name'] for col in columns]}")
        return columns
    
    def _create_dimension_table_with_composite_key(self, table_name: str, columns: List[Dict[str, str]], 
                                                    relationships: List[Relationship], from_table: Table, to_table: Table) -> Table:
        """
        Create a dimension table with a composite key based on relationships.
        
        Args:
            table_name: Name for the dimension table
            columns: List of column definitions (excluding composite key)
            relationships: List of relationships that will use this dimension table
            from_table: The 'from' table in the relationships
            to_table: The 'to' table in the relationships
            
        Returns:
            A new Table object representing the dimension table with composite key
        """
        # Create Column objects from column definitions
        column_objects = []
        for col_def in columns:
            col = Column(
                name=col_def['name'],
                data_type=col_def['dataType'],
                source_column=col_def['sourceColumn']
            )
            # Add additional properties
            col.summarize_by = col_def['summarizeBy']
            column_objects.append(col)
            
        # Extract table names from relationships for M-query generation
        source_tables = set()
        for rel in relationships:
            if isinstance(rel, dict):
                # SQL relationship dictionary
                source_tables.add(rel.get('table_a_one_side', ''))
                source_tables.add(rel.get('table_b_many_side', ''))
            else:
                # Relationship object
                source_tables.add(rel.from_table)
                source_tables.add(rel.to_table)
        
        # Remove empty strings
        source_tables.discard('')
        
        # Generate M-query for the dimension table
        m_query = self._generate_dimension_table_m_query(table_name, column_objects, list(source_tables), relationships)
        
        # Create metadata
        metadata = {
            'is_staging_table': False, # Dimension tables are not staging tables
            'source_tables': list(source_tables),
            'is_source_table': False
        }
        
        # Create the dimension table with composite key
        dimension_table = Table(
            name=table_name,
            columns=column_objects,
            source_query=m_query,
            metadata=metadata
        )
        
        # Add composite key columns
        composite_key_name = self._get_composite_key_name(relationships)
        composite_key_column = Column(
            name=composite_key_name,
            data_type='string',
            source_column=composite_key_name
        )
        dimension_table.columns.append(composite_key_column)
        
        return dimension_table
    
    def _get_composite_key_name(self, relationships: List[Relationship]) -> str:
        """
        Generate a composite key name for a dimension table.
        
        Args:
            relationships: List of relationships that will use this dimension table
            
        Returns:
            A string representing the composite key name
        """
        if self.sql_relationships and isinstance(relationships[0], dict):
            # For SQL relationships, use the actual key columns to create a meaningful name
            first_rel = relationships[0]
            keys_a = first_rel.get('keys_a', [])
            keys_b = first_rel.get('keys_b', [])
            all_keys = keys_a + keys_b
            unique_keys = list(dict.fromkeys(all_keys))  # Remove duplicates while preserving order
            if unique_keys:
                return f"{'_'.join(unique_keys)}_Key"
        
        # Fallback for basic relationships
        return "CompositeKey"
    
    def _generate_dimension_table_m_query(self, table_name: str, columns: List[Column], 
                                        source_tables: List[str], relationships: List[Relationship]) -> str:
        """
        Generate an M-query for a dimension table with composite key.
        
        Args:
            table_name: Name of the dimension table
            columns: List of columns in the dimension table (excluding composite key)
            source_tables: List of source tables to extract data from
            relationships: List of relationships to determine composite key logic
            
        Returns:
            M-query string for the dimension table
        """
        # Extract column names for the query (excluding the composite key)
        column_names = [col.name for col in columns]
        column_list = ', '.join([f'"{name}"' for name in column_names])
        
        # Get composite key name and logic
        composite_key_name = self._get_composite_key_name(relationships)
        composite_key_logic = self._generate_composite_key_logic(relationships)
        
        # Build the M-query
        m_query_parts = ["let"]
        
        # Add steps for each source table
        for i, source_table in enumerate(source_tables):
            step_name = f"Data_From_{source_table.replace(' ', '_')}"
            m_query_parts.append(f"                // Get data from {source_table}")
            m_query_parts.append(f"                {step_name} = Table.SelectColumns({source_table}, {{{column_list}}}),")
            
        # Combine data from all source tables
        if len(source_tables) > 1:
            combine_tables = [f"Data_From_{table.replace(' ', '_')}" for table in source_tables]
            combine_list = ", ".join(combine_tables)
            m_query_parts.append(f"                // Combine data from all source tables")
            m_query_parts.append(f"                CombinedData = Table.Combine({{{combine_list}}}),")
            m_query_parts.append(f"                // Get unique combinations of dimension keys")
            m_query_parts.append(f"                UniqueRows = Table.Distinct(CombinedData, {{{column_list}}}),")
            final_step_before_key = "UniqueRows"
        else:
            source_table_clean = source_tables[0].replace(' ', '_')
            m_query_parts.append(f"                // Get unique combinations of dimension keys")
            m_query_parts.append(f"                UniqueRows = Table.Distinct(Data_From_{source_table_clean}, {{{column_list}}}),")
            final_step_before_key = "UniqueRows"
        
        # Add composite key generation
        m_query_parts.append(f"                // Create composite key for relationships")
        m_query_parts.append(f"                AddCompositeKey = Table.AddColumn({final_step_before_key}, \"{composite_key_name}\", {composite_key_logic}, type text),")
        
        # Filter out null/empty keys
        m_query_parts.append(f"                // Filter out rows with null or empty composite keys")
        m_query_parts.append(f"                FilteredRows = Table.SelectRows(AddCompositeKey, each [{composite_key_name}] <> null and [{composite_key_name}] <> \"\"),")
        
        # Remove the trailing comma from the last step
        m_query_parts[-1] = m_query_parts[-1].rstrip(",")
        
        # Add the final in clause
        m_query_parts.append(f"            in")
        m_query_parts.append(f"                FilteredRows")
        
        # Join all parts with newlines
        m_query = "\n".join(m_query_parts)
        
        return m_query
    
    def _generate_composite_key_logic(self, relationships: List[Relationship]) -> str:
        """
        Generate the M-query logic for creating a composite key.
        
        Args:
            relationships: List of relationships to determine composite key logic
            
        Returns:
            M-query expression for creating the composite key
        """
        if self.sql_relationships and isinstance(relationships[0], dict):
            # For SQL relationships, use the actual key columns
            first_rel = relationships[0]
            keys_a = first_rel.get('keys_a', [])
            keys_b = first_rel.get('keys_b', [])
            all_keys = keys_a + keys_b
            unique_keys = list(dict.fromkeys(all_keys))  # Remove duplicates while preserving order
            
            if len(unique_keys) == 1:
                return f"each [{unique_keys[0]}]"
            elif len(unique_keys) > 1:
                # Create composite key by concatenating with "|" separator
                key_parts = [f"[{key}]" for key in unique_keys]
                return f"each Text.Combine({{{', '.join(key_parts)}}}, \"|\")"
        
        # Fallback for basic relationships
        return 'each "CompositeKey"'
    
    def _create_dimension_relationships_from_sql(self, sql_relationships: List[Dict[str, Any]], 
                                              dimension_table_name: str, from_table_name: str, 
                                              to_table_name: str, new_relationships: List[Relationship]) -> None:
        """
        Create dimension relationships from SQL relationship data using composite keys.
        
        Args:
            sql_relationships: List of SQL relationships
            dimension_table_name: Name of the dimension table
            from_table_name: Name of the 'from' table
            to_table_name: Name of the 'to' table
            new_relationships: List to append new relationships to
        """
        # Get the composite key name for this dimension table
        composite_key_name = self._get_composite_key_name(sql_relationships)
        
        # Create one relationship per fact table, not per key column
        related_tables = set()
        for rel in sql_relationships:
            table_a = rel.get('table_a_one_side', '')
            table_b = rel.get('table_b_many_side', '')
            
            if table_a in [from_table_name, to_table_name]:
                related_tables.add(table_a)
            if table_b in [from_table_name, to_table_name]:
                related_tables.add(table_b)
        
        # Create one relationship per related table using the composite key
        for i, table_name in enumerate(related_tables):
            rel_id_base = f"{dimension_table_name}_to_{table_name}".replace(' ', '_')
            
            # Create relationship from dimension table to fact table
            dim_rel = Relationship(
                id=rel_id_base,  # Remove the Dim_ prefix since dimension_table_name already has it
                from_table=dimension_table_name,
                from_column=composite_key_name,
                to_table=table_name,
                to_column=composite_key_name,  # Fact table should also have this composite key
                from_cardinality="one",
                to_cardinality="many",
                cross_filtering_behavior="OneDirection",
                is_active=True
            )
            new_relationships.append(dim_rel)
            
            self.logger.info(f"Created dimension relationship: {dimension_table_name}[{composite_key_name}] -> {table_name}[{composite_key_name}]")

    def _add_composite_keys_to_fact_tables(self, data_model: DataModel, relationship_groups: Dict[str, List]) -> DataModel:
        """
        Add composite key columns to fact tables based on their relationships with dimension tables.
        
        Args:
            data_model: The data model to enhance
            relationship_groups: Dictionary of relationship groups used to create dimension tables
            
        Returns:
            Enhanced data model with composite keys added to fact tables
        """
        self.logger.info("Adding composite keys to fact tables")
        
        # Track which fact tables need which composite keys
        fact_table_keys = {}  # {table_name: [(composite_key_name, composite_key_logic, relationships)]}
        
        for group_key, relationships in relationship_groups.items():
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            composite_key_name = self._get_composite_key_name(relationships)
            composite_key_logic = self._generate_composite_key_logic(relationships)
            
            # Add this composite key to both fact tables
            for table_name in [from_table_name, to_table_name]:
                if table_name not in fact_table_keys:
                    fact_table_keys[table_name] = []
                fact_table_keys[table_name].append((composite_key_name, composite_key_logic, relationships))
        
        # Update fact table queries to include composite keys
        updated_tables = []
        for table in data_model.tables:
            if table.name in fact_table_keys:
                # This is a fact table that needs composite keys
                updated_table = self._add_composite_keys_to_table(table, fact_table_keys[table.name])
                updated_tables.append(updated_table)
                self.logger.info(f"Added {len(fact_table_keys[table.name])} composite keys to fact table {table.name}")
            else:
                # Keep table as is
                updated_tables.append(table)
        
        # Create new data model with updated tables
        new_data_model = DataModel(
            name=data_model.name,
            tables=updated_tables,
            relationships=data_model.relationships,
            compatibility_level=data_model.compatibility_level
        )
        
        return new_data_model
    
    def _get_original_m_query_from_json(self, table_name: str) -> Optional[str]:
        """
        Read the original M-query from the table's JSON file before composite key processing.
        This should read from JSON files that were generated by the normal migration process.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Original M-query string if found, None otherwise
        """
        if not self.extracted_dir:
            return None
            
        json_file = self.extracted_dir / f"table_{table_name}.json"
        if not json_file.exists():
            self.logger.warning(f"JSON file not found for {table_name}: {json_file}")
            return None
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                table_json = json.load(f)
            
            partitions = table_json.get('partitions', [])
            if not partitions:
                self.logger.warning(f"No partitions found in JSON for {table_name}")
                return None
                
            expression = partitions[0].get('expression', '')
            if not expression:
                self.logger.warning(f"No expression found in partition for {table_name}")
                return None
            
            # Check if this is already a processed expression (contains our composite key additions)
            if 'AddCompositeKey_' in expression:
                self.logger.warning(f"Expression for {table_name} already contains composite keys, this may be a reprocessed file")
                return None
                
            # Check if this looks like a proper M-query (should start with 'let' or contain SQL)
            if not (expression.strip().startswith('let') or 'Sql.Database' in expression or 'Value.NativeQuery' in expression):
                self.logger.warning(f"Expression for {table_name} doesn't look like a proper M-query: {expression[:100]}...")
                return None
                
            self.logger.info(f"Successfully read original M-query for {table_name}: {expression[:200]}...")
            return expression
                    
        except Exception as e:
            self.logger.error(f"Error reading original M-query for {table_name}: {e}")
            return None
    
    def _get_composite_key_columns_from_relationships(self, composite_key_name: str, table_name: str) -> List[str]:
        """
        Get the actual column names for a composite key by looking up in SQL relationships.
        
        Args:
            composite_key_name: Name of the composite key (e.g., 'ITEM_NUMBER_SITE_NUMBER_Key')
            table_name: Name of the table this composite key belongs to
            
        Returns:
            List of actual column names that make up this composite key
        """
        if not self.sql_relationships:
            return []
        
        # Remove '_Key' suffix to get the key identifier
        key_identifier = composite_key_name.replace('_Key', '')
        
        # Look through SQL relationships to find matching patterns
        for rel in self.sql_relationships:
            # Check if this relationship involves our table
            table_a = rel.get('table_a_one_side', '')
            table_b = rel.get('table_b_many_side', '')
            
            if table_name in [table_a, table_b]:
                # Get the keys for this relationship
                keys_a = rel.get('keys_a', [])
                keys_b = rel.get('keys_b', [])
                
                # Try to match the composite key name with the key pattern
                if table_name == table_a:
                    key_columns = keys_a
                else:
                    key_columns = keys_b
                
                # Check if the key pattern matches our composite key name
                if key_columns:
                    # Create a key identifier from these columns
                    potential_key_id = '_'.join(key_columns)
                    if potential_key_id == key_identifier:
                        return key_columns
        
        # Fallback: try to parse the key name intelligently
        self.logger.warning(f"Could not find SQL relationship data for composite key {composite_key_name}, using fallback parsing")
        return self._parse_composite_key_name_fallback(key_identifier)
    
    def _parse_composite_key_name_fallback(self, key_identifier: str) -> List[str]:
        """
        Fallback method to parse composite key names when SQL relationship data is not available.
        
        Args:
            key_identifier: The key identifier without '_Key' suffix
            
        Returns:
            List of parsed column names
        """
        # This is a more intelligent parser that looks for common column patterns
        parts = []
        remaining = key_identifier
        
        # Common column suffixes that indicate the end of a column name
        suffixes = ['_NUMBER', '_DATE', '_ID', '_CODE', '_IND', '_STATUS', '_TYPE', '_FLAG']
        
        while remaining:
            found_part = False
            
            # Look for suffixes
            for suffix in suffixes:
                suffix_pos = remaining.find(suffix)
                if suffix_pos >= 0:
                    # Found a suffix, extract the column name
                    end_pos = suffix_pos + len(suffix)
                    column_name = remaining[:end_pos]
                    parts.append(column_name)
                    
                    # Remove this part and continue
                    remaining = remaining[end_pos:]
                    if remaining.startswith('_'):
                        remaining = remaining[1:]  # Remove leading underscore
                    
                    found_part = True
                    break
            
            if not found_part:
                # No suffix found, take the remaining as a single column
                if remaining:
                    parts.append(remaining)
                break
        
        return parts if parts else [key_identifier]
    
    def _generate_proper_m_query_with_composite_keys(self, table: Table) -> Optional[str]:
        """
        Generate proper M-query for a table that includes composite key generation.
        Reads the baseline M-query from JSON files generated by normal process,
        then extends it with composite keys.
        
        Args:
            table: Table object to generate M-query for
            
        Returns:
            M-query string with composite keys, or None if generation fails
        """
        try:
            # Find composite key columns (those marked as hidden)
            composite_key_columns = [col for col in table.columns if getattr(col, 'is_hidden', False)]
            
            if not composite_key_columns:
                # No composite keys, don't generate M-query here - let normal process handle it
                return None
            
            # Read the baseline M-query from JSON file that was generated by the normal process
            baseline_m_query = self._get_original_m_query_from_json(table.name)
            
            if not baseline_m_query:
                self.logger.warning(f"Could not read baseline M-query from JSON for {table.name}, skipping composite key generation")
                return None
            
            # Prepare composite keys data
            composite_keys = []
            for col in composite_key_columns:
                if '_Key' in col.name:
                    # Get the actual column names for this composite key
                    key_columns = self._get_composite_key_columns_from_relationships(col.name, table.name)
                    
                    if key_columns:
                        if len(key_columns) > 1:
                            # Multi-column composite key
                            logic = f"each Text.Combine({{" + ", ".join([f"[{col_name}]" for col_name in key_columns]) + "}, \"|\")"
                        else:
                            # Single column key
                            logic = f"each [{key_columns[0]}]"
                        
                        composite_keys.append((col.name, logic, []))
            
            # Extend the baseline M-query with composite key generation
            if composite_keys:
                extended_m_query = self._update_fact_table_m_query(baseline_m_query, composite_keys)
                self.logger.info(f"Extended baseline M-query for {table.name} with {len(composite_keys)} composite keys")
                return extended_m_query
            
            return baseline_m_query
            
        except Exception as e:
            self.logger.error(f"Failed to generate proper M-query with composite keys for {table.name}: {e}")
            return None
    
    def _add_composite_keys_to_table(self, table: Table, composite_keys: List[Tuple[str, str, List]], original_m_query: Optional[str] = None) -> Table:
        """
        Add composite key columns to a fact table.
        
        Args:
            table: The original table
            composite_keys: List of (composite_key_name, composite_key_logic, relationships) tuples
            
        Returns:
            Updated table with composite key columns and modified M-query
        """
        # Create new columns including composite keys
        new_columns = list(table.columns)
        
        for composite_key_name, composite_key_logic, relationships in composite_keys:
            # Add composite key column
            composite_key_column = Column(
                name=composite_key_name,
                data_type='string',
                source_column=composite_key_name
            )
            composite_key_column.summarize_by = 'none'
            composite_key_column.is_hidden = True  # Hide composite keys as they're for relationships only
            new_columns.append(composite_key_column)
        
        # Update M-query to include composite key generation
        # Get the baseline M-query from the JSON file (most reliable source)
        baseline_m_query = self._get_original_m_query_from_json(table.name)
        if not baseline_m_query:
            # Fallback to table.source_query or table.m_query
            baseline_m_query = table.source_query or table.m_query or ""
        
        updated_m_query = self._update_fact_table_m_query(baseline_m_query, composite_keys)
        
        # Debug logging
        if updated_m_query != baseline_m_query:
            self.logger.info(f"Successfully updated M-query for {table.name} with {len(composite_keys)} composite keys")
        else:
            self.logger.warning(f"M-query for {table.name} was not updated (returned same as baseline)")
        
        # Create updated table
        updated_table = Table(
            name=table.name,
            columns=new_columns,
            source_query=updated_m_query,
            m_query=updated_m_query,  # Also set m_query so package migration uses it
            metadata=table.metadata
        )
        
        # Copy any additional attributes
        for attr, value in vars(table).items():
            if attr not in ['name', 'columns', 'source_query', 'm_query', 'metadata']:
                setattr(updated_table, attr, value)
        
        return updated_table
    
    def _update_fact_table_m_query(self, original_m_query: str, composite_keys: List[Tuple[str, str, List]]) -> str:
        """
        Update a fact table's M-query to include composite key generation.
        
        Args:
            original_m_query: The original M-query
            composite_keys: List of (composite_key_name, composite_key_logic, relationships) tuples
            
        Returns:
            Updated M-query with composite key generation
        """
        if not composite_keys:
            return original_m_query
        
        # Parse the original query to find the final step
        lines = original_m_query.strip().split('\n')
        if not lines:
            return original_m_query
        
        # Find the 'in' clause and the step before it
        in_line_index = -1
        final_step = "Source"  # Default fallback
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "in":
                in_line_index = i
                # Find the final step name from the line before 'in'
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    # Extract step name from a line like: #"Step Name" = Table.Something(...)
                    if '=' in prev_line:
                        final_step = prev_line.split('=')[0].strip()
                    else:
                        # Fallback: use the line after 'in' (the result reference)
                        if i + 1 < len(lines):
                            final_step = lines[i + 1].strip()
                break
        
        if in_line_index == -1:
            # No 'in' clause found, append to the end
            new_lines = lines[:]
        else:
            # Insert before the 'in' clause
            new_lines = lines[:in_line_index]
        

        
        # Add composite key generation steps
        for i, (composite_key_name, composite_key_logic, relationships) in enumerate(composite_keys):
            step_name = f"AddCompositeKey_{i + 1}"
            if i == 0:
                previous_step = final_step
            else:
                previous_step = f"AddCompositeKey_{i}"
            
            new_lines.append(f"                    // Add composite key: {composite_key_name}")
            new_lines.append(f"                    {step_name} = Table.AddColumn({previous_step}, \"{composite_key_name}\", {composite_key_logic}, type text),")
        
        # Update the final step name
        if composite_keys:
            final_step = f"AddCompositeKey_{len(composite_keys)}"
            # Remove trailing comma from last step
            if new_lines and new_lines[-1].endswith(','):
                new_lines[-1] = new_lines[-1][:-1]
        
        # Add the 'in' clause back
        new_lines.append("                in")
        new_lines.append(f"                    {final_step}")
        
        return '\n'.join(new_lines)

    def _filter_replaced_relationships(self, new_relationships: List[Relationship], relationship_groups: Dict[str, List]) -> List[Relationship]:
        """
        Filter out relationships that are now handled by dimension tables.
        Keep only dimension relationships and other relationships not involved in composite keys.
        
        Args:
            new_relationships: List of relationships to filter (should only contain dimension relationships)
            relationship_groups: Dictionary of relationship groups used to create dimension tables
            
        Returns:
            List of filtered relationships (dimension relationships only)
        """
        # For star schema with dimension tables, we only keep the dimension relationships
        # All the old complex relationships are replaced by the dimension relationships
        
        # Filter to keep only dimension relationships (those starting with 'Dim_')
        dimension_relationships = [
            rel for rel in new_relationships 
            if rel.id.startswith('Dim_')
        ]
        
        # Log what we're keeping
        self.logger.info(f"Keeping {len(dimension_relationships)} dimension relationships")
        for rel in dimension_relationships:
            self.logger.info(f"Keeping dimension relationship: {rel.from_table}[{rel.from_column}] -> {rel.to_table}[{rel.to_column}]")
        
        return dimension_relationships
