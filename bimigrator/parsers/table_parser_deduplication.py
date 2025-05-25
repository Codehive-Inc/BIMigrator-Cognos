"""Handles deduplication of tables and partitions."""
from typing import Dict, List

from bimigrator.config.data_classes import PowerBiTable, PowerBiPartition


class TableDeduplicator:
    """Handles deduplication of tables and partitions."""

    @staticmethod
    def deduplicate_tables(tables: List[PowerBiTable], relationship_table_names: set = None) -> List[PowerBiTable]:
        """Deduplicate tables based on source_name while preserving tables referenced in relationships.
        
        Args:
            tables: List of PowerBiTable objects
            relationship_table_names: Set of table names referenced in relationships
            
        Returns:
            List of deduplicated PowerBiTable objects
        """
        unique_tables = {}
        for table in tables:
            key = table.source_name
            if key in unique_tables:
                existing_table = unique_tables[key]
                # If this is a relationship table, always keep it
                if relationship_table_names and key in relationship_table_names:
                    unique_tables[key] = table
                else:
                    # Otherwise keep the table with more columns/measures
                    existing_complexity = len(existing_table.columns) + len(existing_table.measures)
                    new_complexity = len(table.columns) + len(table.measures)
                    if new_complexity > existing_complexity:
                        unique_tables[key] = table
            else:
                unique_tables[key] = table

        return list(unique_tables.values())

    @staticmethod
    def deduplicate_partitions(partitions: List[PowerBiPartition]) -> List[PowerBiPartition]:
        """Deduplicate partitions based on name and source file.
        
        Args:
            partitions: List of PowerBiPartition objects
            
        Returns:
            List of deduplicated PowerBiPartition objects
        """
        seen_partitions = {}
        for partition in partitions:
            # Extract file name from M code
            file_key = None
            if 'File.Contents' in partition.expression:
                start = partition.expression.find('File.Contents("') + len('File.Contents("')
                end = partition.expression.find('"', start)
                if start > -1 and end > -1:
                    file_key = partition.expression[start:end]

            # Create unique key from file name and partition name
            key = (file_key, partition.name) if file_key else partition.name

            if key not in seen_partitions:
                seen_partitions[key] = partition

        return list(seen_partitions.values())
