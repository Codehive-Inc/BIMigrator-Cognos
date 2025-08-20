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
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with merged staging tables for import mode
        """
        self.logger.info("Processing data model with 'merged_tables' + 'import' approach")
        
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
