"""
Base handler with common functionality for all staging table approaches.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from cognos_migrator.models import DataModel, Table, Column, Relationship, DataType


class BaseHandler:
    """Base class for staging table handlers with common functionality."""
    
    def __init__(self, settings: Dict[str, Any], extracted_dir: Optional[Path] = None, 
                 mquery_converter: Optional[Any] = None):
        """
        Initialize the base handler.
        
        Args:
            settings: Full settings dictionary (will extract staging_tables section)
            extracted_dir: Directory containing extracted files (for SQL relationships)
            mquery_converter: M-query converter instance for generating baseline queries
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.extracted_dir = extracted_dir
        self.mquery_converter = mquery_converter
        
        # Extract staging table settings from the full settings dictionary
        staging_settings = settings.get('staging_tables', {}) if isinstance(settings, dict) else settings
        
        # Extract common settings from staging_tables section
        self.enabled = staging_settings.get('enabled', False)
        self.naming_prefix = staging_settings.get('naming_prefix', 'stg_')
        self.data_load_mode = staging_settings.get('data_load_mode', 'import')
        self.model_handling = staging_settings.get('model_handling', 'none')
        
        # Log the extracted settings for debugging
        self.logger.info(f"BaseHandler initialized with staging settings: enabled={self.enabled}, "
                         f"naming_prefix={self.naming_prefix}, data_load_mode={self.data_load_mode}, "
                         f"model_handling={self.model_handling}")
        
        # Load SQL relationships if available
        self.sql_relationships = []
        if self.extracted_dir and self.enabled:
            self._load_sql_relationships()
    
    def _load_sql_relationships(self) -> None:
        """Load SQL relationships from the extracted directory."""
        sql_file = self.extracted_dir / "sql_filtered_relationships.json"
        if sql_file.exists():
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Handle both direct array and wrapped object formats
                if isinstance(data, list):
                    self.sql_relationships = data
                elif isinstance(data, dict) and 'sql_relationships' in data:
                    self.sql_relationships = data['sql_relationships']
                else:
                    self.logger.warning(f"Unexpected SQL relationships file format: {type(data)}")
                    self.sql_relationships = []
                self.logger.info(f"Loaded {len(self.sql_relationships)} SQL relationships from {sql_file}")
            except Exception as e:
                self.logger.error(f"Error loading SQL relationships from {sql_file}: {e}")
                self.sql_relationships = []
        else:
            self.logger.warning(f"SQL relationships file not found at {sql_file}")
    
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
        
        # Find relationships with multiple connections between same tables
        for rel in relationships:
            pair_key = f"{rel.from_table}:{rel.to_table}"
            if relationship_counts[pair_key] > 1 and rel not in complex_relationships:
                complex_relationships.append(rel)
                self.logger.info(f"Identified complex relationship with multiple connections: "
                                 f"{rel.from_table} -> {rel.to_table} ({relationship_counts[pair_key]} connections)")
        
        return complex_relationships
    
    def _identify_complex_sql_relationships(self, sql_relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify complex SQL relationships that need staging tables.
        
        Args:
            sql_relationships: List of SQL relationship dictionaries
            
        Returns:
            List of complex SQL relationships
        """
        complex_relationships = []
        
        for rel in sql_relationships:
            # Check if relationship has composite keys
            keys_a = rel.get('keys_a', [])
            keys_b = rel.get('keys_b', [])
            
            if len(keys_a) > 1 or len(keys_b) > 1:
                complex_relationships.append(rel)
                table_a = rel.get('table_a_one_side', 'Unknown')
                table_b = rel.get('table_b_many_side', 'Unknown')
                self.logger.info(f"Identified complex SQL relationship: {table_a} <-> {table_b} "
                                 f"with {len(keys_a)} keys A and {len(keys_b)} keys B, reason: composite_keys")
                continue
            
            # Check if relationship has staging_table_reason
            if rel.get('staging_table_reason'):
                complex_relationships.append(rel)
                table_a = rel.get('table_a_one_side', 'Unknown')
                table_b = rel.get('table_b_many_side', 'Unknown')
                reason = rel.get('staging_table_reason', 'unknown')
                self.logger.info(f"Identified complex SQL relationship: {table_a} <-> {table_b} "
                                 f"with {len(keys_a)} keys A and {len(keys_b)} keys B, reason: {reason}")
        
        return complex_relationships
    
    def _save_table_as_json(self, table: Table, extracted_dir: Path) -> None:
        """
        Save a table as a JSON file in the extracted directory.
        
        Args:
            table: Table to save
            extracted_dir: Directory to save the JSON file in
        """
        # Build table JSON structure
        table_json = {
            "name": table.name,
            "columns": []
        }
        
        # Add columns
        for col in table.columns:
            column_json = {
                "name": col.name,
                "dataType": col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
                "sourceColumn": col.source_column,
                "summarizeBy": col.summarize_by,
                "isKey": col.is_key,
                "isNullable": col.is_nullable
            }
            
            if col.format_string:
                column_json["formatString"] = col.format_string
            if col.description:
                column_json["description"] = col.description
                
            table_json["columns"].append(column_json)
        
        # Add measures if any
        if table.measures:
            table_json["measures"] = []
            for measure in table.measures:
                measure_json = {
                    "name": measure.name,
                    "expression": measure.expression
                }
                if hasattr(measure, 'format_string') and measure.format_string:
                    measure_json["formatString"] = measure.format_string
                if hasattr(measure, 'description') and measure.description:
                    measure_json["description"] = measure.description
                table_json["measures"].append(measure_json)
        
        # Add M-query if available
        m_query = None
        if hasattr(table, 'm_query') and table.m_query:
            m_query = table.m_query
        elif hasattr(table, 'source_query') and table.source_query:
            m_query = table.source_query
        
        # Add partitions with M-query
        partitions = []
        if m_query:
            partitions.append({
                "name": table.name,
                "source_type": "m",
                "mode": self._get_partition_mode(),
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
    
    def _get_original_m_query_from_json(self, table_name: str) -> Optional[str]:
        """
        Get the original M-query for a table from its JSON file.
        
        Args:
            table_name: Name of the table
            
        Returns:
            The original M-query string, or None if not found
        """
        if not self.extracted_dir:
            return None
            
        json_file = self.extracted_dir / f"table_{table_name}.json"
        if not json_file.exists():
            self.logger.warning(f"JSON file not found for table {table_name}: {json_file}")
            return None
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                table_data = json.load(f)
            
            # Get M-query from partitions
            partitions = table_data.get('partitions', [])
            for partition in partitions:
                if partition.get('source_type') == 'm':
                    m_query = partition.get('expression', '')
                    if m_query:
                        self.logger.info(f"Successfully read original M-query for {table_name}:\n"
                                         f"{m_query[:200]}{'...' if len(m_query) > 200 else ''}")
                        return m_query
            
            self.logger.warning(f"No M-query found in partitions for table {table_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading M-query from JSON for table {table_name}: {e}")
            return None
    
    def _get_partition_mode(self) -> str:
        """Get partition mode from staging table settings."""
        # Use the correctly extracted data_load_mode from __init__
        return 'directQuery' if self.data_load_mode == 'direct_query' else 'import'
