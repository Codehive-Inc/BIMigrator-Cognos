"""Handles deduplication of tables and partitions."""
from typing import Dict, List, Set, Tuple, Optional
import re
from collections import defaultdict

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiTable, PowerBiPartition, PowerBiColumn


class TableDeduplicator:
    """Handles deduplication of tables and partitions."""

    @staticmethod
    def deduplicate_tables(tables: List[PowerBiTable], relationship_table_names: set = None) -> List[PowerBiTable]:
        """Deduplicate tables based on source_name and column similarity.
        
        Args:
            tables: List of PowerBiTable objects
            relationship_table_names: Set of table names referenced in relationships
            
        Returns:
            List of deduplicated PowerBiTable objects
        """
        if not tables:
            return []
        
        # First pass: Group tables by exact source_name match
        name_groups = defaultdict(list)
        for table in tables:
            name_groups[table.source_name].append(table)
        
        # Second pass: For each group, check column similarity to identify similar tables
        similarity_groups = []
        processed_tables = set()
        
        for source_name, group_tables in name_groups.items():
            # If only one table with this name, keep it as is
            if len(group_tables) == 1:
                similarity_groups.append(group_tables)
                processed_tables.add(id(group_tables[0]))
                continue
            
            # For multiple tables with the same name, check column similarity
            current_group = []
            remaining_tables = [t for t in group_tables if id(t) not in processed_tables]
            
            if remaining_tables:
                # Start with the first table
                current_group.append(remaining_tables[0])
                processed_tables.add(id(remaining_tables[0]))
                
                # Compare each remaining table to see if it should be merged
                for table in remaining_tables[1:]:
                    if id(table) in processed_tables:
                        continue
                    
                    # Check if this table is similar to any in the current group
                    if any(TableDeduplicator._are_tables_similar(table, existing) for existing in current_group):
                        current_group.append(table)
                        processed_tables.add(id(table))
                    else:
                        # Start a new group if not similar
                        similarity_groups.append([table])
                        processed_tables.add(id(table))
                
                # Add the current group
                if current_group:
                    similarity_groups.append(current_group)
        
        # Third pass: Merge similar tables and create the final list
        final_tables = []
        for group in similarity_groups:
            if len(group) == 1:
                final_tables.append(group[0])
            else:
                # Merge tables in this group
                merged_table = TableDeduplicator._merge_similar_tables(group, relationship_table_names)
                final_tables.append(merged_table)
        
        logger.info(f"Deduplicated {len(tables)} tables into {len(final_tables)} unique tables")
        return final_tables
    
    @staticmethod
    def _are_tables_similar(table1: PowerBiTable, table2: PowerBiTable) -> bool:
        """Check if two tables are similar based on column names and structure.
        
        Args:
            table1: First PowerBiTable object
            table2: Second PowerBiTable object
            
        Returns:
            True if tables are similar, False otherwise
        """
        # If tables have the same name, they're potentially similar
        if table1.source_name == table2.source_name:
            # Get column names for comparison
            cols1 = {col.source_name.lower() for col in table1.columns}
            cols2 = {col.source_name.lower() for col in table2.columns}
            
            # Calculate Jaccard similarity (intersection over union)
            if not cols1 or not cols2:
                return False
                
            intersection = len(cols1.intersection(cols2))
            union = len(cols1.union(cols2))
            
            # Consider tables similar if they share at least 70% of columns
            similarity = intersection / union if union > 0 else 0
            return similarity >= 0.7
        
        return False
    
    @staticmethod
    def _merge_similar_tables(tables: List[PowerBiTable], relationship_table_names: Optional[Set[str]] = None) -> PowerBiTable:
        """Merge similar tables into a single table with combined columns and measures.
        
        Args:
            tables: List of similar PowerBiTable objects to merge
            relationship_table_names: Set of table names referenced in relationships
            
        Returns:
            Merged PowerBiTable object
        """
        if not tables:
            raise ValueError("Cannot merge empty list of tables")
        
        # Start with the most complex table or relationship table as the base
        base_table = None
        max_complexity = -1
        
        for table in tables:
            # Prioritize tables referenced in relationships
            if relationship_table_names and table.source_name in relationship_table_names:
                base_table = table
                break
                
            # Otherwise use complexity (number of columns + measures)
            complexity = len(table.columns) + len(table.measures)
            if complexity > max_complexity:
                max_complexity = complexity
                base_table = table
        
        if not base_table:
            base_table = tables[0]  # Fallback
        
        # Create a new merged table based on the base table
        merged_table = PowerBiTable(
            name=base_table.name,
            source_name=base_table.source_name,
            description=base_table.description,
            columns=[],  # Will be populated below
            measures=[],  # Will be populated below
            partitions=[]  # Will be populated below
        )
        
        # Track columns and measures by name to avoid duplicates
        column_map = {}
        measure_map = {}
        
        # Process all tables and collect unique columns and measures
        for table in tables:
            # Add columns if not already present
            for col in table.columns:
                col_key = col.source_name.lower()
                if col_key not in column_map:
                    column_map[col_key] = col
                elif col.pbi_datatype != 'string' and column_map[col_key].pbi_datatype == 'string':
                    # Prefer non-string datatypes when merging
                    column_map[col_key] = col
            
            # Add measures if not already present
            for measure in table.measures:
                measure_key = measure.name.lower()
                if measure_key not in measure_map:
                    measure_map[measure_key] = measure
            
            # Collect partitions
            merged_table.partitions.extend(table.partitions)
        
        # Populate the merged table
        merged_table.columns = list(column_map.values())
        merged_table.measures = list(measure_map.values())
        
        # Deduplicate partitions
        merged_table.partitions = TableDeduplicator.deduplicate_partitions(merged_table.partitions)
        
        logger.info(f"Merged {len(tables)} similar tables into {merged_table.source_name} with {len(merged_table.columns)} columns and {len(merged_table.measures)} measures")
        
        return merged_table

    @staticmethod
    def deduplicate_partitions(partitions: List[PowerBiPartition]) -> List[PowerBiPartition]:
        """Deduplicate partitions based on name, source file, and SQL query.
        
        Args:
            partitions: List of PowerBiPartition objects
            
        Returns:
            List of deduplicated PowerBiPartition objects
        """
        if not partitions:
            return []
            
        # Group partitions by their deduplication key
        partition_groups = {}
        
        for partition in partitions:
            # Try to extract keys from different sources
            dedup_key = TableDeduplicator._generate_partition_key(partition)
            
            # Store the partition with its key
            if dedup_key not in partition_groups:
                partition_groups[dedup_key] = [partition]
            else:
                partition_groups[dedup_key].append(partition)
        
        # For each group, select the best partition
        result = []
        for key, group in partition_groups.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Select the partition with the most detailed information
                best_partition = TableDeduplicator._select_best_partition(group)
                result.append(best_partition)
        
        logger.info(f"Deduplicated {len(partitions)} partitions into {len(result)} unique partitions")
        return result
    
    @staticmethod
    def _generate_partition_key(partition: PowerBiPartition) -> Tuple:
        """Generate a deduplication key for a partition based on various attributes.
        
        Args:
            partition: PowerBiPartition object
            
        Returns:
            Tuple that can be used as a dictionary key for deduplication
        """
        # Start with the partition name
        key_parts = [partition.name]
        
        # Check for relation_key in metadata
        if partition.metadata and 'relation_key' in partition.metadata:
            key_parts.append(partition.metadata['relation_key'])
        
        # Extract file name from M code for Excel connections
        file_key = None
        if partition.expression and 'File.Contents' in partition.expression:
            file_pattern = r'File\.Contents\("([^"]+)"\)'
            file_match = re.search(file_pattern, partition.expression)
            if file_match:
                file_key = file_match.group(1)
                key_parts.append(f"file:{file_key}")
        
        # Extract SQL query hash from M code for SQL connections
        if partition.expression and ('Sql.Database' in partition.expression or 
                                   'Oracle.Database' in partition.expression or 
                                   'Snowflake.Databases' in partition.expression):
            # Look for SQL query in the M code
            sql_pattern = r'"(SELECT[^"]+)"'
            sql_match = re.search(sql_pattern, partition.expression, re.IGNORECASE)
            if sql_match:
                # Use first 50 chars of SQL as part of the key
                sql_part = sql_match.group(1)[:50].replace(' ', '').replace('\n', '')
                key_parts.append(f"sql:{sql_part}")
        
        # Add server and database info if available in metadata
        if partition.metadata:
            if 'server' in partition.metadata and partition.metadata['server']:
                key_parts.append(f"server:{partition.metadata['server']}")
            if 'database' in partition.metadata and partition.metadata['database']:
                key_parts.append(f"db:{partition.metadata['database']}")
        
        # Convert to tuple for use as dictionary key
        return tuple(key_parts)
    
    @staticmethod
    def _select_best_partition(partitions: List[PowerBiPartition]) -> PowerBiPartition:
        """Select the best partition from a group of similar partitions.
        
        Args:
            partitions: List of similar PowerBiPartition objects
            
        Returns:
            The best PowerBiPartition object from the group
        """
        if not partitions:
            raise ValueError("Cannot select from empty list of partitions")
        
        if len(partitions) == 1:
            return partitions[0]
        
        # Score each partition based on completeness
        scored_partitions = []
        for partition in partitions:
            score = 0
            
            # Prefer partitions with SQL queries
            if partition.metadata and partition.metadata.get('has_sql_query') == 'true':
                score += 10
            
            # Prefer partitions with more detailed metadata
            if partition.metadata:
                score += len(partition.metadata)
            
            # Prefer partitions with longer expressions (likely more detailed)
            if partition.expression:
                score += min(len(partition.expression) / 100, 5)  # Cap at 5 points
            
            # Prefer partitions with descriptions
            if partition.description:
                score += 2
                # Extra points for SQL in description
                if 'SQL Query:' in partition.description:
                    score += 3
            
            scored_partitions.append((score, partition))
        
        # Return the partition with the highest score
        scored_partitions.sort(key=lambda x: x[0], reverse=True)
        return scored_partitions[0][1]
