"""
SQL Join Analyzer for extracting join patterns from Cognos packages and reports.

This module analyzes SQL queries, relationships, and report specifications to
identify join patterns and derive staging table requirements for Power BI migration.
"""

import logging
import re
import json
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from ..llm_service import LLMServiceClient


@dataclass
class JoinPattern:
    """Represents a join pattern extracted from Cognos artifacts"""
    left_table: str
    right_table: str
    left_columns: List[str]
    right_columns: List[str]
    join_type: str  # INNER, LEFT, RIGHT, FULL, CROSS
    join_expression: str
    confidence: float
    source: str  # "package_relationship", "report_sql", "inferred"
    composite_key: bool = False


@dataclass
class StagingTableDefinition:
    """Defines a staging table based on join analysis"""
    name: str
    source_tables: List[str]
    shared_keys: List[str]
    join_patterns: List[JoinPattern]
    columns: List[Dict[str, Any]]
    sql_definition: str
    m_query: Optional[str] = None


class SQLJoinAnalyzer:
    """Analyzes SQL joins and relationships from Cognos packages and reports"""
    
    def __init__(self, llm_service_client: Optional[LLMServiceClient] = None, logger=None):
        """Initialize the SQL join analyzer
        
        Args:
            llm_service_client: Optional LLM service client for advanced analysis
            logger: Optional logger instance
        """
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)
        
        # SQL parsing patterns
        self.join_patterns = {
            'inner_join': re.compile(r'\bINNER\s+JOIN\b', re.IGNORECASE),
            'left_join': re.compile(r'\bLEFT\s+(?:OUTER\s+)?JOIN\b', re.IGNORECASE),
            'right_join': re.compile(r'\bRIGHT\s+(?:OUTER\s+)?JOIN\b', re.IGNORECASE),
            'full_join': re.compile(r'\bFULL\s+(?:OUTER\s+)?JOIN\b', re.IGNORECASE),
            'cross_join': re.compile(r'\bCROSS\s+JOIN\b', re.IGNORECASE)
        }
        
        self.table_reference_pattern = re.compile(
            r'(?:FROM|JOIN)\s+(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?)\s*(?:AS\s+)?(\w+)?',
            re.IGNORECASE
        )
        
        self.join_condition_pattern = re.compile(
            r'ON\s+(.*?)(?=\s+(?:INNER|LEFT|RIGHT|FULL|CROSS|WHERE|GROUP|ORDER|$))',
            re.IGNORECASE | re.DOTALL
        )

    def analyze_package_joins(self, package_info: Dict[str, Any]) -> List[JoinPattern]:
        """Analyze join patterns from Cognos package relationships
        
        Args:
            package_info: Extracted package information containing relationships
            
        Returns:
            List of identified join patterns
        """
        self.logger.info("Analyzing join patterns from package relationships")
        join_patterns = []
        
        relationships = package_info.get('relationships', [])
        
        for rel in relationships:
            pattern = self._analyze_package_relationship(rel)
            if pattern:
                join_patterns.append(pattern)
        
        self.logger.info(f"Extracted {len(join_patterns)} join patterns from package relationships")
        return join_patterns

    def analyze_report_joins(self, report_queries: List[Dict[str, Any]]) -> List[JoinPattern]:
        """Analyze join patterns from report SQL queries
        
        Args:
            report_queries: List of report query definitions
            
        Returns:
            List of identified join patterns
        """
        self.logger.info("Analyzing join patterns from report queries")
        join_patterns = []
        
        for query in report_queries:
            patterns = self._analyze_report_query(query)
            join_patterns.extend(patterns)
        
        self.logger.info(f"Extracted {len(join_patterns)} join patterns from report queries")
        return join_patterns

    def infer_joins_from_field_usage(self, report_queries: List[Dict[str, Any]], 
                                   package_relationships: List[JoinPattern]) -> List[JoinPattern]:
        """Infer join patterns from multi-table field usage in reports
        
        Args:
            report_queries: List of report query definitions
            package_relationships: Known relationships from package analysis
            
        Returns:
            List of inferred join patterns
        """
        self.logger.info("Inferring join patterns from field usage")
        inferred_patterns = []
        
        for query in report_queries:
            table_usage = self._extract_table_usage_from_query(query)
            if len(table_usage) > 1:
                # Multi-table usage detected, infer joins
                patterns = self._infer_joins_from_table_usage(table_usage, package_relationships)
                inferred_patterns.extend(patterns)
        
        self.logger.info(f"Inferred {len(inferred_patterns)} join patterns from field usage")
        return inferred_patterns

    def generate_staging_tables(self, all_join_patterns: List[JoinPattern], 
                              settings: Dict[str, Any]) -> List[StagingTableDefinition]:
        """Generate staging table definitions based on join analysis
        
        Args:
            all_join_patterns: All identified join patterns
            settings: Staging table configuration settings
            
        Returns:
            List of staging table definitions
        """
        self.logger.info("Generating staging table definitions from join analysis")
        
        staging_tables = []
        
        # Group join patterns by connected components
        table_groups = self._group_tables_by_joins(all_join_patterns)
        
        for group in table_groups:
            if len(group) > 1:  # Only create staging tables for multi-table groups
                staging_table = self._create_staging_table_definition(group, all_join_patterns, settings)
                if staging_table:
                    staging_tables.append(staging_table)
        
        self.logger.info(f"Generated {len(staging_tables)} staging table definitions")
        return staging_tables

    def _analyze_package_relationship(self, relationship: Dict[str, Any]) -> Optional[JoinPattern]:
        """Analyze a single package relationship to extract join pattern"""
        try:
            left_info = relationship.get('left', {})
            right_info = relationship.get('right', {})
            join_expression = relationship.get('join_expression', '')
            
            # Extract table names
            left_table = self._extract_table_name_from_ref(left_info.get('ref', ''))
            right_table = self._extract_table_name_from_ref(right_info.get('ref', ''))
            
            if not left_table or not right_table:
                return None
            
            # Determine join type based on cardinality
            left_cardinality = left_info.get('maxcard', '')
            right_cardinality = right_info.get('maxcard', '')
            
            join_type = self._determine_join_type_from_cardinality(left_cardinality, right_cardinality)
            
            # Extract join columns from expression
            left_columns, right_columns = self._parse_join_expression(join_expression)
            
            return JoinPattern(
                left_table=left_table,
                right_table=right_table,
                left_columns=left_columns,
                right_columns=right_columns,
                join_type=join_type,
                join_expression=join_expression,
                confidence=0.9,  # High confidence for package relationships
                source="package_relationship",
                composite_key=len(left_columns) > 1
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing package relationship: {e}")
            return None

    def _analyze_report_query(self, query: Dict[str, Any]) -> List[JoinPattern]:
        """Analyze a single report query for join patterns"""
        patterns = []
        
        # Extract SQL if available
        sql = query.get('sql', '')
        if not sql:
            return patterns
        
        # Find join types
        for join_name, pattern in self.join_patterns.items():
            if pattern.search(sql):
                # Extract join details using LLM if available
                if self.llm_service_client:
                    join_pattern = self._extract_join_with_llm(sql, join_name)
                    if join_pattern:
                        patterns.append(join_pattern)
                else:
                    # Fallback to regex parsing
                    join_pattern = self._extract_join_with_regex(sql, join_name)
                    if join_pattern:
                        patterns.append(join_pattern)
        
        return patterns

    def _extract_table_usage_from_query(self, query: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract which tables and columns are used in a query"""
        table_usage = {}
        
        # Look for dataItem expressions that reference tables
        selections = query.get('selection', [])
        for item in selections:
            expression = item.get('expression', '')
            table_refs = self._extract_table_references_from_expression(expression)
            for table, columns in table_refs.items():
                if table not in table_usage:
                    table_usage[table] = []
                table_usage[table].extend(columns)
        
        return table_usage

    def _group_tables_by_joins(self, join_patterns: List[JoinPattern]) -> List[Set[str]]:
        """Group tables into connected components based on join patterns"""
        # Build adjacency list
        graph = {}
        all_tables = set()
        
        for pattern in join_patterns:
            all_tables.add(pattern.left_table)
            all_tables.add(pattern.right_table)
            
            if pattern.left_table not in graph:
                graph[pattern.left_table] = set()
            if pattern.right_table not in graph:
                graph[pattern.right_table] = set()
            
            graph[pattern.left_table].add(pattern.right_table)
            graph[pattern.right_table].add(pattern.left_table)
        
        # Find connected components using DFS
        visited = set()
        components = []
        
        for table in all_tables:
            if table not in visited:
                component = set()
                self._dfs(table, graph, visited, component)
                if len(component) > 1:  # Only include multi-table components
                    components.append(component)
        
        return components

    def _dfs(self, node: str, graph: Dict[str, Set[str]], visited: Set[str], component: Set[str]):
        """Depth-first search to find connected components"""
        visited.add(node)
        component.add(node)
        
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                self._dfs(neighbor, graph, visited, component)

    def _create_staging_table_definition(self, table_group: Set[str], 
                                       join_patterns: List[JoinPattern],
                                       settings: Dict[str, Any]) -> Optional[StagingTableDefinition]:
        """Create a staging table definition for a group of related tables"""
        try:
            # Find all join patterns involving tables in this group
            relevant_patterns = [
                p for p in join_patterns 
                if p.left_table in table_group and p.right_table in table_group
            ]
            
            if not relevant_patterns:
                return None
            
            # Generate staging table name
            table_names = sorted(list(table_group))
            staging_name = f"{settings.get('prefix', 'Staging_')}{'_'.join(table_names[:3])}"
            
            # Extract shared keys from join patterns
            shared_keys = self._extract_shared_keys(relevant_patterns)
            
            # Generate SQL definition
            sql_definition = self._generate_staging_sql(table_group, relevant_patterns)
            
            # Extract all columns from the involved tables
            columns = self._extract_columns_for_staging_table(table_group, relevant_patterns)
            
            return StagingTableDefinition(
                name=staging_name,
                source_tables=list(table_group),
                shared_keys=shared_keys,
                join_patterns=relevant_patterns,
                columns=columns,
                sql_definition=sql_definition
            )
            
        except Exception as e:
            self.logger.error(f"Error creating staging table definition: {e}")
            return None

    def _extract_shared_keys(self, join_patterns: List[JoinPattern]) -> List[str]:
        """Extract shared key columns from join patterns"""
        shared_keys = set()
        
        for pattern in join_patterns:
            # Add composite key handling
            if pattern.composite_key:
                # Create a composite key name
                composite_key = f"{'_'.join(pattern.left_columns)}_Key"
                shared_keys.add(composite_key)
            else:
                shared_keys.update(pattern.left_columns)
                shared_keys.update(pattern.right_columns)
        
        return list(shared_keys)

    def _generate_staging_sql(self, table_group: Set[str], 
                            join_patterns: List[JoinPattern]) -> str:
        """Generate SQL definition for staging table"""
        # Start with the first table
        main_table = sorted(list(table_group))[0]
        sql_parts = [f"SELECT * FROM {main_table}"]
        
        # Add joins
        joined_tables = {main_table}
        
        for pattern in join_patterns:
            if pattern.left_table in joined_tables and pattern.right_table not in joined_tables:
                join_sql = self._format_join_sql(pattern, pattern.right_table)
                sql_parts.append(join_sql)
                joined_tables.add(pattern.right_table)
            elif pattern.right_table in joined_tables and pattern.left_table not in joined_tables:
                join_sql = self._format_join_sql(pattern, pattern.left_table)
                sql_parts.append(join_sql)
                joined_tables.add(pattern.left_table)
        
        return '\n'.join(sql_parts)

    def _format_join_sql(self, pattern: JoinPattern, table_to_join: str) -> str:
        """Format a join SQL clause"""
        join_type_map = {
            'INNER': 'INNER JOIN',
            'LEFT': 'LEFT JOIN',
            'RIGHT': 'RIGHT JOIN',
            'FULL': 'FULL OUTER JOIN',
            'CROSS': 'CROSS JOIN'
        }
        
        join_clause = join_type_map.get(pattern.join_type, 'INNER JOIN')
        
        if pattern.join_type == 'CROSS':
            return f"{join_clause} {table_to_join}"
        
        # Build ON condition
        conditions = []
        for left_col, right_col in zip(pattern.left_columns, pattern.right_columns):
            conditions.append(f"{pattern.left_table}.{left_col} = {pattern.right_table}.{right_col}")
        
        on_clause = " AND ".join(conditions)
        return f"{join_clause} {table_to_join} ON {on_clause}"

    def _extract_columns_for_staging_table(self, table_group: Set[str], 
                                         join_patterns: List[JoinPattern]) -> List[Dict[str, Any]]:
        """Extract column definitions for staging table"""
        # This would typically require access to table metadata
        # For now, return a placeholder structure
        columns = []
        
        for table in table_group:
            # Add table identifier column
            columns.append({
                'name': f'{table}_Key',
                'datatype': 'string',
                'source_table': table,
                'is_key': True
            })
        
        return columns

    # Helper methods for parsing and extraction
    
    def _extract_table_name_from_ref(self, ref: str) -> str:
        """Extract table name from a Cognos reference"""
        if not ref:
            return ""
        
        # Handle different reference formats
        # e.g., "[Database_Layer].[TABLE_NAME]" -> "TABLE_NAME"
        parts = ref.split('.')
        if len(parts) >= 2:
            return parts[-1].strip('[]')
        return ref.strip('[]')

    def _determine_join_type_from_cardinality(self, left_card: str, right_card: str) -> str:
        """Determine join type from cardinality information"""
        if left_card == "many" and right_card == "one":
            return "LEFT"  # Many-to-one suggests left join
        elif left_card == "one" and right_card == "many":
            return "RIGHT"  # One-to-many suggests right join
        elif left_card == "many" and right_card == "many":
            return "FULL"  # Many-to-many suggests full outer join
        else:
            return "INNER"  # Default to inner join

    def _parse_join_expression(self, expression: str) -> Tuple[List[str], List[str]]:
        """Parse join expression to extract column names"""
        if not expression:
            return [], []
        
        # Simple regex to extract column references
        # This is a simplified version - real implementation would be more robust
        column_pattern = re.compile(r'\[([^\]]+)\]\.\[([^\]]+)\]')
        matches = column_pattern.findall(expression)
        
        left_columns = []
        right_columns = []
        
        # Group by table
        table_columns = {}
        for table, column in matches:
            if table not in table_columns:
                table_columns[table] = []
            table_columns[table].append(column)
        
        # Assume first table is left, second is right
        table_names = list(table_columns.keys())
        if len(table_names) >= 2:
            left_columns = table_columns[table_names[0]]
            right_columns = table_columns[table_names[1]]
        
        return left_columns, right_columns

    def _extract_join_with_llm(self, sql: str, join_type: str) -> Optional[JoinPattern]:
        """Extract join pattern using LLM service"""
        if not self.llm_service_client:
            return None
        
        try:
            # Format for /api/sql/analyze-report endpoint
            api_payload = {
                "sql_query": sql,
                "analysis_type": "join_extraction",
                "analysis_options": {
                    "extract_join_patterns": True,
                    "identify_table_relationships": True,
                    "detect_composite_keys": True,
                    "classify_join_types": True
                },
                "context": {
                    "expected_join_type": join_type,
                    "target_platform": "powerbi"
                }
            }
            
            response = self.llm_service_client.call_api_endpoint(
                endpoint="/api/sql/analyze-report", 
                method="POST",
                payload=api_payload
            )
            
            if response and response.get("join_patterns"):
                join_data = response["join_patterns"][0]  # Get first pattern
                
                return JoinPattern(
                    left_table=join_data.get("left_table", ""),
                    right_table=join_data.get("right_table", ""),
                    left_columns=join_data.get("left_columns", []),
                    right_columns=join_data.get("right_columns", []),
                    join_type=join_data.get("join_type", "INNER"),
                    join_expression=join_data.get("join_expression", ""),
                    confidence=response.get("confidence", 0.8),
                    source="llm_sql_analysis",
                    composite_key=len(join_data.get("left_columns", [])) > 1
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting join with LLM: {e}")
            return None

    def _extract_join_with_regex(self, sql: str, join_type: str) -> Optional[JoinPattern]:
        """Extract join pattern using regex (fallback method)"""
        # Simplified regex-based extraction
        # This would be more sophisticated in a real implementation
        return None

    def _extract_table_references_from_expression(self, expression: str) -> Dict[str, List[str]]:
        """Extract table and column references from a Cognos expression"""
        table_refs = {}
        
        # Pattern to match Cognos expressions like [Database_Layer].[TABLE].[COLUMN]
        pattern = re.compile(r'\[([^\]]+)\]\.\[([^\]]+)\]\.\[([^\]]+)\]')
        matches = pattern.findall(expression)
        
        for layer, table, column in matches:
            if table not in table_refs:
                table_refs[table] = []
            table_refs[table].append(column)
        
        return table_refs

    def _infer_joins_from_table_usage(self, table_usage: Dict[str, List[str]], 
                                    known_relationships: List[JoinPattern]) -> List[JoinPattern]:
        """Infer join patterns from table usage and known relationships"""
        inferred_patterns = []
        
        tables = list(table_usage.keys())
        
        # For each pair of tables used together
        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                table1, table2 = tables[i], tables[j]
                
                # Check if we have a known relationship
                existing_pattern = None
                for pattern in known_relationships:
                    if ((pattern.left_table == table1 and pattern.right_table == table2) or
                        (pattern.left_table == table2 and pattern.right_table == table1)):
                        existing_pattern = pattern
                        break
                
                if existing_pattern:
                    # Use the known relationship with lower confidence
                    inferred_pattern = JoinPattern(
                        left_table=existing_pattern.left_table,
                        right_table=existing_pattern.right_table,
                        left_columns=existing_pattern.left_columns,
                        right_columns=existing_pattern.right_columns,
                        join_type=existing_pattern.join_type,
                        join_expression=existing_pattern.join_expression,
                        confidence=0.7,  # Lower confidence for inferred
                        source="inferred",
                        composite_key=existing_pattern.composite_key
                    )
                    inferred_patterns.append(inferred_pattern)
        
        return inferred_patterns 