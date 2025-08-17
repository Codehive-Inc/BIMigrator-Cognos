"""
SQL relationship extractor for Cognos Framework Manager packages.

This module provides functionality to extract relationships from
Cognos Framework Manager (FM) package files and generate SQL with appropriate joins.
"""

import logging
import os
import csv
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .package_relationship_extractor import PackageRelationshipExtractor


class SQLRelationshipExtractor:
    """Extractor for generating SQL based on relationships in Cognos Framework Manager packages"""
    
    def __init__(self, logger=None, model_tables=None):
        """Initialize the SQL relationship extractor
        
        Args:
            logger: Optional logger instance
            model_tables: Optional list of table names in the current semantic model
        """
        self.logger = logger or logging.getLogger(__name__)
        self.relationship_extractor = PackageRelationshipExtractor(logger)
        self.model_tables = model_tables or []
    
    def extract_and_save(self, package_file_path: str, output_dir: str) -> Dict[str, Any]:
        """Extract relationships, generate SQL, and save to output files
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted relationships and SQL
        """
        try:
            # Parse the XML file
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Update namespaces on the relationship extractor
            self.relationship_extractor.update_namespaces_from_root(root)
            
            # Extract relationships using the existing extractor
            relationships = self.relationship_extractor.extract_relationships(root)
            
            # Process relationships to determine join types and generate SQL
            processed_relationships = self._process_relationships(relationships)
            
            # Save to CSV file
            csv_path = os.path.join(output_dir, "sql_relationship_joins.csv")
            self._save_to_csv(processed_relationships, csv_path)
            
            # Save to JSON file
            json_path = os.path.join(output_dir, "sql_relationships.json")
            self.relationship_extractor.save_to_json(
                {"sql_relationships": processed_relationships}, 
                output_dir, 
                "sql_relationships.json"
            )
            
            # Save filtered version with only relationships used for staging tables
            filtered_relationships = self._filter_staging_table_relationships(processed_relationships)
            self.relationship_extractor.save_to_json(
                {"sql_relationships": filtered_relationships}, 
                output_dir, 
                "sql_filtered_relationships.json"
            )
            self.logger.info(f"Saved filtered relationships for staging tables: {len(filtered_relationships)} relationships")
            
            self.logger.info(f"Extracted and processed {len(processed_relationships)} relationships")
            return {"sql_relationships": processed_relationships}
            
        except Exception as e:
            self.logger.error(f"Failed to extract SQL relationships from {package_file_path}: {e}")
            return {"error": str(e)}
    
    def _process_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process relationships to determine join types and generate SQL
        
        Args:
            relationships: List of relationships extracted from XML
            
        Returns:
            List of processed relationships with join types and SQL
        """
        processed_relationships = []
        
        for rel in relationships:
            try:
                # Extract relationship name
                rel_name = rel.get('name', 'Unknown Relationship')
                
                # Extract left and right sides
                left_side = rel.get('left', {})
                right_side = rel.get('right', {})
                
                # Skip if missing essential information
                if not left_side or not right_side:
                    self.logger.warning(f"Skipping relationship {rel_name} - missing left or right side")
                    continue
                
                # Extract query subjects (tables)
                left_qs = left_side.get('query_subject', '')
                right_qs = right_side.get('query_subject', '')
                
                # Extract simple table names from qualified names
                left_table = self._extract_table_name(left_qs)
                right_table = self._extract_table_name(right_qs)
                
                # Extract cardinality
                left_mincard = left_side.get('mincard', 'one')
                left_maxcard = left_side.get('maxcard', 'one')
                right_mincard = right_side.get('mincard', 'one')
                right_maxcard = right_side.get('maxcard', 'one')
                
                # Determine one and many sides
                one_side_table, one_side_keys, many_side_table, many_side_keys = self._determine_one_many_sides(
                    left_table, right_table, left_maxcard, right_maxcard, rel
                )
                
                # Determine join type based on cardinality
                join_type, cognos_cardinality, power_bi_config = self._determine_join_type(
                    left_mincard, left_maxcard, right_mincard, right_maxcard
                )
                
                # Generate SQL JOIN clause
                sql_join = self._generate_sql_join(
                    one_side_table, one_side_keys,
                    many_side_table, many_side_keys,
                    join_type
                )
                
                # Create processed relationship
                processed_rel = {
                    'relationship_name': rel_name,
                    'table_a_one_side': one_side_table,
                    'keys_a': one_side_keys,
                    'table_b_many_side': many_side_table,
                    'keys_b': many_side_keys,
                    'cognos_cardinality': cognos_cardinality,
                    'join_type': join_type,
                    'power_bi_config': power_bi_config,
                    'sql_join': sql_join,
                    'original_relationship': rel
                }
                
                processed_relationships.append(processed_rel)
                
            except Exception as e:
                self.logger.warning(f"Error processing relationship {rel.get('name', 'Unknown')}: {e}")
                continue
        
        return processed_relationships
    
    def _extract_table_name(self, qualified_name: str) -> str:
        """Extract simple table name from qualified name
        
        Args:
            qualified_name: Qualified name like '[Database_Layer].[TABLE]'
            
        Returns:
            Simple table name
        """
        if not qualified_name:
            return ""
        
        # Split by dots and remove brackets
        parts = qualified_name.split('.')
        if len(parts) >= 2:
            return parts[-1].strip('[]')
        
        return qualified_name.strip('[]')
    
    def _extract_column_name(self, qualified_name: str) -> str:
        """Extract column name from qualified name
        
        Args:
            qualified_name: Qualified name like '[Database_Layer].[TABLE].[COLUMN]'
            
        Returns:
            Column name
        """
        if not qualified_name:
            return ""
        
        # Split by dots and remove brackets
        parts = qualified_name.split('.')
        if len(parts) >= 3:
            return parts[-1].strip('[]')
        
        return qualified_name.strip('[]')
        
    def _extract_table_and_column(self, qualified_name: str) -> Tuple[str, str]:
        """Extract both table and column names from a qualified name
        
        Args:
            qualified_name: Qualified name like '[Database_Layer].[TABLE].[COLUMN]'
            
        Returns:
            Tuple of (table_name, column_name)
        """
        if not qualified_name:
            return "", ""
        
        # Split by dots and remove brackets
        parts = qualified_name.split('.')
        if len(parts) >= 3:
            table = parts[-2].strip('[]')
            column = parts[-1].strip('[]')
            return table, column
        
        return "", qualified_name.strip('[]')
    
    def _determine_one_many_sides(
        self, left_table: str, right_table: str, 
        left_maxcard: str, right_maxcard: str,
        relationship: Dict[str, Any]
    ) -> Tuple[str, List[str], str, List[str]]:
        """Determine which side is 'one' and which is 'many'
        
        Args:
            left_table: Left table name
            right_table: Right table name
            left_maxcard: Left max cardinality
            right_maxcard: Right max cardinality
            relationship: Full relationship dictionary
            
        Returns:
            Tuple of (one_side_table, one_side_keys, many_side_table, many_side_keys)
        """
        # Extract join keys from determinants or expression
        left_keys = []
        right_keys = []
        
        # Try to extract from determinants first
        determinants = relationship.get('determinants', [])
        if determinants:
            for det in determinants:
                left_col = det.get('left_column', '')
                right_col = det.get('right_column', '')
                
                if left_col:
                    left_keys.append(self._extract_column_name(left_col))
                if right_col:
                    right_keys.append(self._extract_column_name(right_col))
        
        # If no determinants, try to extract from join expression
        if not left_keys or not right_keys:
            join_expr = relationship.get('join_expression', '')
            if join_expr:
                # Parse complex expressions with multiple AND conditions
                self._parse_join_expression(join_expr, left_table, right_table, left_keys, right_keys)
        
        # Determine one and many sides based on maxcard
        if left_maxcard.lower() == 'one' and right_maxcard.lower() == 'many':
            return left_table, left_keys, right_table, right_keys
        elif left_maxcard.lower() == 'many' and right_maxcard.lower() == 'one':
            return right_table, right_keys, left_table, left_keys
        else:
            # If both are 'one' or both are 'many', default to left as 'one'
            return left_table, left_keys, right_table, right_keys
    
    def _determine_join_type(
        self, left_mincard: str, left_maxcard: str, 
        right_mincard: str, right_maxcard: str
    ) -> Tuple[str, str, str]:
        """Determine join type based on cardinality
        
        Args:
            left_mincard: Left min cardinality
            left_maxcard: Left max cardinality
            right_mincard: Right min cardinality
            right_maxcard: Right max cardinality
            
        Returns:
            Tuple of (join_type, cognos_cardinality, power_bi_config)
        """
        # Convert to lowercase for consistent comparison
        left_mincard = left_mincard.lower()
        left_maxcard = left_maxcard.lower()
        right_mincard = right_mincard.lower()
        right_maxcard = right_maxcard.lower()
        
        # Format Cognos cardinality
        left_card = f"{0 if left_mincard == 'zero' else 1}..{1 if left_maxcard == 'one' else 'n'}"
        right_card = f"{0 if right_mincard == 'zero' else 1}..{1 if right_maxcard == 'one' else 'n'}"
        cognos_cardinality = f"{left_card} to {right_card}"
        
        # Determine join type based on cardinality rules
        if left_mincard == 'one' and right_mincard == 'one':
            # 1..1 to 1..1 = INNER JOIN
            join_type = "INNER JOIN"
            power_bi_config = "One-to-One, Bidirectional Filter."
        elif left_mincard == 'one' and right_mincard == 'zero':
            # 1..1 to 0..n = LEFT OUTER JOIN (from the 1..1 side)
            join_type = "LEFT OUTER JOIN"
            power_bi_config = "One-to-Many, Single Direction Filter."
        elif left_mincard == 'zero' and right_mincard == 'one':
            # 0..1 to 1..1 = RIGHT OUTER JOIN (from the 1..1 side)
            join_type = "RIGHT OUTER JOIN"
            power_bi_config = "Many-to-One, Single Direction Filter."
        elif left_mincard == 'zero' and right_mincard == 'zero':
            # 0..1 to 0..n = FULL OUTER JOIN
            join_type = "FULL OUTER JOIN"
            power_bi_config = "Many-to-Many, Bidirectional Filter."
        else:
            # Default to INNER JOIN if cardinality is unclear
            join_type = "INNER JOIN"
            power_bi_config = "One-to-Many, Single Direction Filter."
        
        return join_type, cognos_cardinality, power_bi_config
    
    def _parse_join_expression(self, join_expr: str, left_table: str, right_table: str, 
                           left_keys: List[str], right_keys: List[str]) -> None:
        """Parse join expression to extract keys for composite joins
        
        Args:
            join_expr: Join expression string
            left_table: Left table name
            right_table: Right table name
            left_keys: List to populate with left keys
            right_keys: List to populate with right keys
        """
        # Skip if join expression is empty
        if not join_expr:
            return
            
        # Split by AND to handle composite keys
        conditions = join_expr.split(' AND ')
        
        for condition in conditions:
            # Handle each equality condition
            parts = condition.split('=')
            if len(parts) == 2:
                left_expr = parts[0].strip()
                right_expr = parts[1].strip()
                
                # Extract table and column names
                left_table_from_expr, left_col = self._extract_table_and_column(left_expr)
                right_table_from_expr, right_col = self._extract_table_and_column(right_expr)
                
                # Skip if we couldn't extract column names
                if not left_col or not right_col:
                    continue
                    
                # Determine which column belongs to which table
                if left_table_from_expr and left_table_from_expr.lower() in left_table.lower():
                    left_keys.append(left_col)
                    right_keys.append(right_col)
                elif right_table_from_expr and right_table_from_expr.lower() in right_table.lower():
                    left_keys.append(right_col)
                    right_keys.append(left_col)
                # If table names don't match exactly, try partial matching
                elif left_table_from_expr and left_table_from_expr in left_table:
                    left_keys.append(left_col)
                    right_keys.append(right_col)
                elif right_table_from_expr and right_table_from_expr in right_table:
                    left_keys.append(right_col)
                    right_keys.append(left_col)
                # If we can't determine from table names, make a best guess based on which is left/right in the expression
                elif '.' in left_expr and '.' in right_expr:
                    left_keys.append(self._extract_column_name(left_expr))
                    right_keys.append(self._extract_column_name(right_expr))
    
    def _generate_sql_join(
        self, one_side_table: str, one_side_keys: List[str],
        many_side_table: str, many_side_keys: List[str],
        join_type: str
    ) -> str:
        """Generate SQL JOIN clause
        
        Args:
            one_side_table: One side table name
            one_side_keys: One side join keys
            many_side_table: Many side table name
            many_side_keys: Many side join keys
            join_type: Type of join (INNER, LEFT OUTER, etc.)
            
        Returns:
            SQL JOIN clause
        """
        # Ensure we have keys to join on
        if not one_side_keys or not many_side_keys or len(one_side_keys) != len(many_side_keys):
            return f"-- Unable to generate JOIN: missing or mismatched keys for {one_side_table} and {many_side_table}"
        
        # Generate the ON clause
        on_conditions = []
        for i in range(len(one_side_keys)):
            on_conditions.append(f"{one_side_table}.{one_side_keys[i]} = {many_side_table}.{many_side_keys[i]}")
        
        on_clause = " AND ".join(on_conditions)
        
        # Generate the full JOIN clause
        sql = f"{join_type} {many_side_table} ON {on_clause}"
        
        return sql
    
    def _filter_staging_table_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter relationships to only include those used for staging table creation.
        
        This method exactly matches the logic in StagingTableHandler._identify_complex_relationships.
        A relationship is considered for staging table creation if:
        1. It has composite keys (multiple columns in join keys)
        2. There are multiple relationships between the same tables
        3. Both tables in the relationship are present in the current semantic model
        
        Args:
            relationships: List of processed relationships
            
        Returns:
            Filtered list of relationships used for staging tables
        """
        # First, filter relationships to only include those where both tables are in the model
        model_relationships = []
        for rel in relationships:
            table_a = rel['table_a_one_side']
            table_b = rel['table_b_many_side']
            
            # Skip relationships where either table is not in the model
            if self.model_tables and (table_a not in self.model_tables or table_b not in self.model_tables):
                self.logger.info(f"Skipping relationship between {table_a} and {table_b} - tables not in current model")
                continue
            
            model_relationships.append(rel)
        
        if self.model_tables:
            self.logger.info(f"Filtered to {len(model_relationships)} relationships with tables in the current model")
        
        filtered_relationships = []
        table_pair_counts = {}
        
        # First pass: Count relationships between each pair of tables
        for rel in model_relationships:
            table_a = rel['table_a_one_side']
            table_b = rel['table_b_many_side']
            
            # Create a consistent key for the table pair (same as StagingTableHandler)
            pair_key = f"{table_a}:{table_b}"
            
            if pair_key not in table_pair_counts:
                table_pair_counts[pair_key] = 0
            table_pair_counts[pair_key] += 1
            
            # Check for composite keys (multiple columns in join)
            if len(rel['keys_a']) > 1 or len(rel['keys_b']) > 1:
                rel['staging_table_reason'] = 'composite_keys'
                filtered_relationships.append(rel)
                self.logger.info(f"Identified complex relationship with composite key: "
                               f"{table_a}.{', '.join(rel['keys_a'])} -> {table_b}.{', '.join(rel['keys_b'])}")
        
        # Second pass: Add relationships where tables have multiple relationships between them
        for rel in model_relationships:
            table_a = rel['table_a_one_side']
            table_b = rel['table_b_many_side']
            pair_key = f"{table_a}:{table_b}"
            
            if table_pair_counts[pair_key] > 1 and 'staging_table_reason' not in rel:
                rel['staging_table_reason'] = 'multiple_relationships'
                filtered_relationships.append(rel)
                self.logger.info(f"Identified complex relationship: {table_a} has multiple relationships with {table_b}")
        
        self.logger.info(f"Filtered {len(filtered_relationships)} relationships for staging tables")
        return filtered_relationships
    
    def _save_to_csv(self, relationships: List[Dict[str, Any]], csv_path: str) -> None:
        """Save relationships to CSV file
        
        Args:
            relationships: List of relationships to save
            csv_path: Path to save CSV file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Define CSV headers
            headers = [
                'Relationship Name', 
                'Table A (One Side)', 
                'Key(s) A', 
                'Table B (Many Side)', 
                'Key(s) B',
                'Cognos Cardinality', 
                'Implied Join Type',
                'SQL Join'
            ]
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(headers)
                
                # Write data rows
                for rel in relationships:
                    writer.writerow([
                        rel['relationship_name'],
                        rel['table_a_one_side'],
                        ', '.join(rel['keys_a']),
                        rel['table_b_many_side'],
                        ', '.join(rel['keys_b']),
                        rel['cognos_cardinality'],
                        f"{rel['join_type']}. Config: {rel['power_bi_config']}"
                    ])
            
            self.logger.info(f"Saved relationships to CSV: {csv_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save relationships to CSV: {e}")


def extract_sql_relationships(package_file_path: str, output_dir: str, logger=None, model_tables=None) -> Dict[str, Any]:
    """Extract SQL relationships from a package file
    
    Args:
        package_file_path: Path to the FM package file
        output_dir: Directory to save extracted data
        logger: Optional logger instance
        model_tables: Optional list of table names in the current semantic model
        
    Returns:
        Dictionary with extracted relationships and SQL
    """
    extractor = SQLRelationshipExtractor(logger, model_tables)
    return extractor.extract_and_save(package_file_path, output_dir)
