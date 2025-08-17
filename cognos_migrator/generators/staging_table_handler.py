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
        with relationships established between the staging tables and the original tables.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with star schema staging tables
        """
        self.logger.info("Processing data model with 'star_schema' approach")
        
        # Identify tables involved in complex relationships
        complex_tables = self._identify_complex_relationship_tables(data_model.relationships)
        self.logger.info(f"Identified {len(complex_tables)} tables involved in complex relationships")
        
        # Create staging tables for complex tables
        new_tables = list(data_model.tables)  # Start with all original tables
        staging_tables = {}
        
        for table_name in complex_tables:
            # Find the original table
            original_table = next((t for t in data_model.tables if t.name == table_name), None)
            if original_table:
                # Create a staging table
                staging_table = self._create_staging_table(original_table)
                new_tables.append(staging_table)
                staging_tables[table_name] = staging_table.name
                self.logger.info(f"Created staging table {staging_table.name} for {table_name}")
        
        # Create new relationships between staging tables and original tables
        new_relationships = list(data_model.relationships)  # Start with all original relationships
        
        # Add relationships between staging tables and original tables
        for original_name, staging_name in staging_tables.items():
            # Find the original table and staging table
            original_table = next((t for t in data_model.tables if t.name == original_name), None)
            staging_table = next((t for t in new_tables if t.name == staging_name), None)
            
            if original_table and staging_table:
                # Create a relationship between the staging table and original table
                # Use the primary key of the original table
                primary_key = self._identify_primary_key(original_table, data_model.relationships)
                
                if primary_key:
                    relationship = Relationship(
                        id=f"Staging_{original_name}_{staging_name}",
                        from_table=staging_name,
                        from_column=primary_key,
                        to_table=original_name,
                        to_column=primary_key,
                        from_cardinality="many",
                        cross_filtering_behavior="BothDirections",
                        is_active=True
                    )
                    new_relationships.append(relationship)
                    self.logger.info(f"Created relationship between {staging_name} and {original_name} "
                                     f"on column {primary_key}")
        
        # Update complex relationships to use staging tables
        updated_relationships = self._update_relationships_for_star_schema(
            data_model.relationships, staging_tables)
        
        # Replace original relationships with updated ones
        new_relationships = [r for r in new_relationships if not self._is_complex_relationship(r, complex_tables)]
        new_relationships.extend(updated_relationships)
        
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
    
    def _identify_complex_relationship_tables(self, relationships: List[Relationship]) -> Set[str]:
        """
        Identify tables involved in complex relationships.
        
        A complex relationship is one where:
        1. A table has multiple relationships with the same table
        2. A table has composite key relationships (multiple columns in the join)
        
        Args:
            relationships: List of relationships to analyze
            
        Returns:
            Set of table names involved in complex relationships
        """
        complex_tables = set()
        relationship_counts = {}
        
        # Count relationships between each pair of tables
        for rel in relationships:
            pair_key = f"{rel.from_table}:{rel.to_table}"
            if pair_key not in relationship_counts:
                relationship_counts[pair_key] = 0
            relationship_counts[pair_key] += 1
            
            # Check for composite keys (indicated by multiple columns)
            if ',' in (rel.from_column or '') or ',' in (rel.to_column or ''):
                complex_tables.add(rel.from_table)
                complex_tables.add(rel.to_table)
                self.logger.info(f"Identified complex relationship with composite key: "
                                 f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
        
        # Identify tables with multiple relationships to the same table
        for pair_key, count in relationship_counts.items():
            if count > 1:
                from_table, to_table = pair_key.split(':')
                complex_tables.add(from_table)
                complex_tables.add(to_table)
                self.logger.info(f"Identified complex relationship: {from_table} has {count} relationships with {to_table}")
        
        return complex_tables
    
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
