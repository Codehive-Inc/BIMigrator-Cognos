"""
Merged Tables handler for creating staging tables merged with original tables.
"""

from typing import Dict, List, Any, Optional, Set
from pathlib import Path

from cognos_migrator.models import DataModel, Table, Column, Relationship, DataType
from .base_handler import BaseHandler


class MergedTablesHandler(BaseHandler):
    """Handler for merged tables approach with staging columns added to original tables."""
    
    def process_import_mode(self, data_model: DataModel) -> DataModel:
        """
        Process data model using merged tables approach with import mode.
        
        This approach creates combination tables (C_tables) that join multiple source tables
        together using nested joins rather than creating separate dimension tables.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with combination tables (C_tables) for import mode
        """
        self.logger.info("Processing data model with 'merged_tables' + 'import' approach for C_tables")
        
        # Identify complex relationships that need combination tables
        complex_relationships = self._identify_complex_relationships(data_model.relationships)
        self.logger.info(f"Identified {len(complex_relationships)} complex relationships")
        
        if not complex_relationships:
            self.logger.info("No complex relationships found, returning original model")
            return data_model
        
        # Group relationships by table pairs to create combination tables
        relationship_groups = self._group_relationships_by_tables(complex_relationships)
        self.logger.info(f"Grouped complex relationships into {len(relationship_groups)} combination table groups")
        
        # Start with all original tables
        new_tables = list(data_model.tables)
        combination_tables = []
        
        # Create combination tables (C_tables) for each relationship group
        for group_key, relationships in relationship_groups.items():
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            
            # Find the actual table objects
            from_table = next((t for t in data_model.tables if t.name == from_table_name), None)
            to_table = next((t for t in data_model.tables if t.name == to_table_name), None)
            
            if not from_table or not to_table:
                self.logger.warning(f"Could not find tables for relationship group: {group_key}")
                continue
            
            # Create combination table with C_ prefix
            combination_table = self._create_combination_table(
                from_table, to_table, relationships)
            
            combination_tables.append(combination_table)
            new_tables.append(combination_table)
            self.logger.info(f"Created combination table {combination_table.name} for {from_table_name} + {to_table_name}")
        
        # Keep original relationships as-is (combination tables don't replace them)
        new_relationships = list(data_model.relationships)
        
        # Create new data model with combination tables added
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
        
        self.logger.info(f"Processed data model with 'merged_tables' C_table approach: "
                         f"{len(new_tables)} tables ({len(combination_tables)} combination tables), "
                         f"{len(new_relationships)} relationships")
        return new_data_model
    
    def process_direct_query_mode(self, data_model: DataModel) -> DataModel:
        """
        Process data model using merged tables approach with DirectQuery mode.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with merged staging tables for DirectQuery mode
        """
        self.logger.info("Processing data model with 'merged_tables' + 'direct_query' approach")
        
        # TODO: Implement merged tables with DirectQuery optimizations
        # Key differences from import mode:
        # - M-queries should be optimized for query folding
        # - Minimize complex transformations that can't be pushed to the database
        # - Use native SQL operations where possible
        # - Avoid operations that break query folding (like Table.AddColumn with complex logic)
        
        self.logger.warning("merged_tables + direct_query mode is not yet implemented, using import mode")
        return self.process_import_mode(data_model)
    
    def _identify_complex_relationship_tables(self, relationships: List[Relationship]) -> Set[str]:
        """
        Identify tables that are involved in complex relationships.
        
        Args:
            relationships: List of relationships to analyze
            
        Returns:
            Set of table names that are involved in complex relationships
        """
        complex_relationships = self._identify_complex_relationships(relationships)
        complex_tables = set()
        
        for rel in complex_relationships:
            complex_tables.add(rel.from_table)
            complex_tables.add(rel.to_table)
        
        return complex_tables
    
    def _create_merged_table(self, original_table: Table, data_model: DataModel) -> Table:
        """
        Create a merged table by adding staging columns to the original table.
        
        This approach preserves the original table structure while adding necessary
        columns for complex joins. The table gets a staging prefix in its name.
        
        Args:
            original_table: The original table to merge
            data_model: The full data model for context
            
        Returns:
            A new table with merged staging columns
        """
        # Create new table name with staging prefix
        merged_table_name = f"{self.naming_prefix}{original_table.name}"
        
        # Start with all original columns
        merged_columns = list(original_table.columns)
        
        # Find relationships involving this table
        related_columns = set()
        for rel in data_model.relationships:
            if rel.from_table == original_table.name:
                if rel.from_column:
                    related_columns.update(rel.from_column.split(','))
            if rel.to_table == original_table.name:
                if rel.to_column:
                    related_columns.update(rel.to_column.split(','))
        
        # Add staging columns for complex relationships
        existing_column_names = {col.name for col in merged_columns}
        
        for col_name in related_columns:
            col_name = col_name.strip()
            staging_col_name = f"stg_{col_name}"
            
            if staging_col_name not in existing_column_names:
                staging_column = Column(
                    name=staging_col_name,
                    data_type=DataType.STRING,  # Default to string
                    source_column=staging_col_name,
                    summarize_by="none",
                    description=f"Staging column for complex relationship on {col_name}"
                )
                merged_columns.append(staging_column)
        
        # Create merged table
        merged_table = Table(
            name=merged_table_name,
            columns=merged_columns,
            measures=original_table.measures,
            source_query=original_table.source_query,
            m_query=original_table.m_query,
            partition_mode=original_table.partition_mode,
            description=f"Merged staging table based on {original_table.name}",
            annotations=original_table.annotations,
            metadata=original_table.metadata
        )
        
        return merged_table
    
    def _update_relationships_for_merged_tables(self, relationships: List[Relationship], 
                                              complex_tables: Set[str]) -> List[Relationship]:
        """
        Update relationships to point to merged tables where applicable.
        
        Args:
            relationships: Original relationships
            complex_tables: Set of table names that were converted to merged tables
            
        Returns:
            Updated list of relationships
        """
        updated_relationships = []
        
        for rel in relationships:
            # Create a copy of the relationship
            updated_rel = Relationship(
                from_table=rel.from_table,
                from_column=rel.from_column,
                to_table=rel.to_table,
                to_column=rel.to_column,
                id=rel.id,
                from_cardinality=rel.from_cardinality,
                to_cardinality=rel.to_cardinality,
                cross_filtering_behavior=rel.cross_filtering_behavior,
                is_active=rel.is_active
            )
            
            # Update table names to use merged tables if they were converted
            if rel.from_table in complex_tables:
                updated_rel.from_table = f"{self.naming_prefix}{rel.from_table}"
                updated_rel.id = f"merged_{rel.id}"
            
            if rel.to_table in complex_tables:
                updated_rel.to_table = f"{self.naming_prefix}{rel.to_table}"
                if not updated_rel.id.startswith("merged_"):
                    updated_rel.id = f"merged_{rel.id}"
            
            updated_relationships.append(updated_rel)
        
        return updated_relationships
    
    def _group_relationships_by_tables(self, relationships: List[Relationship]) -> Dict[str, List[Relationship]]:
        """
        Group relationships by the table pairs they connect.
        
        Args:
            relationships: List of relationships to group
            
        Returns:
            Dictionary mapping table pair keys to lists of relationships
        """
        relationship_groups = {}
        
        for rel in relationships:
            # Create a standardized key for the table pair (alphabetically sorted)
            table_pair = [rel.from_table, rel.to_table]
            table_pair.sort()
            group_key = f"{table_pair[0]}:{table_pair[1]}"
            
            if group_key not in relationship_groups:
                relationship_groups[group_key] = []
            relationship_groups[group_key].append(rel)
        
        return relationship_groups
    
    def _create_combination_table(self, from_table: Table, to_table: Table, 
                                 relationships: List[Relationship]) -> Table:
        """
        Create a combination table (C_table) that joins two source tables using nested joins.
        
        Args:
            from_table: First source table
            to_table: Second source table
            relationships: List of relationships between the tables
            
        Returns:
            A new combination table with nested join M-query
        """
        # Create combination table name with C_ prefix
        table_names = [from_table.name, to_table.name]
        table_names.sort()  # Ensure consistent naming
        combination_table_name = f"C_{table_names[0]}_{table_names[1]}"
        
        # Combine columns from both tables, avoiding duplicates
        combined_columns = []
        existing_column_names = set()
        
        # Add columns from first table
        for col in from_table.columns:
            combined_columns.append(col)
            existing_column_names.add(col.name)
        
        # Add only unique columns from second table (skip duplicates completely)
        for col in to_table.columns:
            if col.name not in existing_column_names:
                combined_columns.append(col)
                existing_column_names.add(col.name)
        
        # Generate nested join M-query
        m_query = self._generate_nested_join_query(from_table, to_table, relationships)
        
        # Create combination table
        combination_table = Table(
            name=combination_table_name,
            columns=combined_columns,
            measures=[],  # Combination tables typically don't have measures
            source_query="",  # M-query provides the source
            m_query=m_query,
            partition_mode="import",
            description=f"Combination table joining {from_table.name} and {to_table.name}",
            annotations={},
            metadata={}
        )
        
        return combination_table
    
    def _generate_nested_join_query(self, from_table: Table, to_table: Table, 
                                   relationships: List[Relationship]) -> str:
        """
        Generate M-query with nested join logic for combination table.
        
        Args:
            from_table: First source table
            to_table: Second source table
            relationships: List of relationships between the tables
            
        Returns:
            M-query string with nested join logic
        """
        # Extract join columns from relationships
        join_columns = []
        for rel in relationships:
            if rel.from_column and rel.to_column:
                # Handle comma-separated columns for composite keys
                from_cols = [col.strip() for col in rel.from_column.split(',')]
                to_cols = [col.strip() for col in rel.to_column.split(',')]
                
                for from_col, to_col in zip(from_cols, to_cols):
                    join_columns.append((from_col, to_col))
        
        if not join_columns:
            self.logger.warning(f"No join columns found for {from_table.name} and {to_table.name}")
            return f"// No join columns found\n{from_table.name}"
        
        # Build join key arrays for M-query
        from_table_keys = ', '.join([f'"{col[0]}"' for col in join_columns])
        to_table_keys = ', '.join([f'"{col[1]}"' for col in join_columns])
        
        # Get column names from first table to identify duplicates
        from_table_column_names = {col.name for col in from_table.columns}
        
        # Get only unique column names from second table for expansion (skip duplicates)
        unique_to_table_columns = []
        for col in to_table.columns:
            if col.name not in from_table_column_names:
                unique_to_table_columns.append(col.name)
        
        to_table_columns_str = ', '.join([f'"{col}"' for col in unique_to_table_columns])
        expanded_columns_str = ', '.join([f'"{col}"' for col in unique_to_table_columns])
        
        # Generate the nested join M-query with proper indentation
        m_query = f'''let
                Source = Table.NestedJoin({from_table.name}, {{{from_table_keys}}}, {to_table.name}, {{{to_table_keys}}}, "{to_table.name}", JoinKind.Inner),
                #"Expanded {to_table.name}" = Table.ExpandTableColumn(Source, "{to_table.name}", {{{to_table_columns_str}}}, {{{expanded_columns_str}}})
            in
                #"Expanded {to_table.name}"'''
        
        return m_query
