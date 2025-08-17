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
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the staging table handler.
        
        Args:
            settings: Optional settings dictionary. If not provided, will attempt to load from settings.json
        """
        self.logger = logging.getLogger(__name__)
        
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
        
        # Identify relationships that need staging tables
        complex_relationships = self._identify_complex_relationships(data_model.relationships)
        self.logger.info(f"Identified {len(complex_relationships)} complex relationships that need staging tables")
        
        if not complex_relationships:
            self.logger.info("No complex relationships found, returning original model")
            return data_model
        
        # Group relationships by tables they connect
        relationship_groups = self._group_relationships_by_tables(complex_relationships)
        self.logger.info(f"Grouped complex relationships into {len(relationship_groups)} groups")
        
        # Create staging tables for each relationship group
        new_tables = list(data_model.tables)  # Start with all original tables
        staging_tables = []
        staging_table_map = {}  # Maps original table pairs to staging tables
        
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
                
            # Create a staging table for this relationship group
            staging_table_name = f"{self.naming_prefix}{from_table_name}_{to_table_name}"
            
            # Get all columns needed for the relationships in this group
            columns = self._extract_columns_for_staging_table(relationships, from_table, to_table)
            
            # Create the staging table
            staging_table = self._create_staging_table_with_columns(staging_table_name, columns, relationships)
            new_tables.append(staging_table)
            staging_tables.append(staging_table)
            staging_table_map[group_key] = staging_table_name
            
            self.logger.info(f"Created staging table {staging_table_name} with {len(columns)} columns")
        
        # Create new relationships using staging tables
        new_relationships = []
        
        # Keep non-complex relationships
        for rel in data_model.relationships:
            if not self._is_relationship_in_list(rel, complex_relationships):
                new_relationships.append(rel)
        
        # Create new relationships using staging tables
        for group_key, relationships in relationship_groups.items():
            if group_key not in staging_table_map:
                continue
                
            staging_table_name = staging_table_map[group_key]
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            
            # Create relationships between staging table and original tables
            for rel in relationships:
                # Create relationship from staging table to from_table
                from_rel = Relationship(
                    id=f"Staging_{rel.id}_From",
                    from_table=staging_table_name,
                    from_column=rel.from_column,
                    to_table=from_table_name,
                    to_column=rel.from_column,
                    from_cardinality="many",
                    to_cardinality="one",
                    cross_filtering_behavior="BothDirections",
                    is_active=True
                )
                new_relationships.append(from_rel)
                
                # Create relationship from staging table to to_table
                to_rel = Relationship(
                    id=f"Staging_{rel.id}_To",
                    from_table=staging_table_name,
                    from_column=rel.to_column,
                    to_table=to_table_name,
                    to_column=rel.to_column,
                    from_cardinality="many",
                    to_cardinality="one",
                    cross_filtering_behavior="BothDirections",
                    is_active=True
                )
                new_relationships.append(to_rel)
                
                self.logger.info(f"Created staging relationships for {rel.id} using {staging_table_name}")
        
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
        
        self.logger.info(f"Processed data model with 'star_schema' approach: "
                         f"{len(new_tables)} tables, {len(new_relationships)} relationships")
        return new_data_model
    
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
            source_tables.add(rel.from_table)
            source_tables.add(rel.to_table)
            
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
