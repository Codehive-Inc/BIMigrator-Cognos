"""
Staging Table Analyzer for Power BI semantic model optimization.

This module analyzes join patterns and creates optimized staging table definitions
that follow Power BI best practices for star schema design.
"""

import logging
import json
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from .sql_join_analyzer import SQLJoinAnalyzer, JoinPattern, StagingTableDefinition
from ..llm_service import LLMServiceClient
from ..models import Table, Column, DataType


@dataclass
class SharedKeyDefinition:
    """Defines a shared key for staging tables"""
    name: str
    source_columns: List[str]
    target_tables: List[str]
    is_composite: bool
    surrogate_key_formula: Optional[str] = None


@dataclass
class StagingTableMetadata:
    """Extended metadata for staging tables"""
    fact_table_mappings: Dict[str, List[str]]  # fact table -> columns from staging
    dimension_candidates: List[str]  # tables that could become dimensions
    relationship_definitions: List[Dict[str, Any]]
    performance_notes: List[str]


class StagingTableAnalyzer:
    """Analyzes and optimizes staging table definitions for Power BI"""
    
    def __init__(self, sql_join_analyzer: SQLJoinAnalyzer, 
                 llm_service_client: Optional[LLMServiceClient] = None, 
                 logger=None):
        """Initialize the staging table analyzer
        
        Args:
            sql_join_analyzer: SQL join analyzer instance
            llm_service_client: Optional LLM service client
            logger: Optional logger instance
        """
        self.sql_join_analyzer = sql_join_analyzer
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)

    def analyze_staging_requirements(self, package_info: Dict[str, Any], 
                                   report_queries: List[Dict[str, Any]],
                                   settings: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze staging table requirements from package and report data
        
        Args:
            package_info: Extracted package information
            report_queries: List of report query definitions
            settings: Staging table configuration settings
            
        Returns:
            Dictionary containing staging analysis results
        """
        self.logger.info("Starting staging table analysis")
        
        # Step 1: Extract all join patterns
        package_joins = self.sql_join_analyzer.analyze_package_joins(package_info)
        report_joins = self.sql_join_analyzer.analyze_report_joins(report_queries)
        inferred_joins = self.sql_join_analyzer.infer_joins_from_field_usage(
            report_queries, package_joins
        )
        
        all_joins = package_joins + report_joins + inferred_joins
        
        # Step 2: Analyze table relationships and identify staging candidates
        staging_candidates = self._identify_staging_candidates(all_joins, settings)
        
        # Step 3: Generate optimized staging table definitions
        staging_tables = self._generate_optimized_staging_tables(
            staging_candidates, all_joins, package_info, settings
        )
        
        # Step 4: Create shared key definitions
        shared_keys = self._create_shared_key_definitions(staging_tables, settings)
        
        # Step 5: Generate relationship definitions
        relationships = self._generate_staging_relationships(staging_tables, shared_keys)
        
        # Step 6: Create fact table update recommendations
        fact_table_updates = self._analyze_fact_table_updates(staging_tables, package_info)
        
        analysis_result = {
            'staging_enabled': settings.get('enabled', False),
            'staging_tables': [asdict(st) for st in staging_tables],
            'shared_keys': [asdict(sk) for sk in shared_keys],
            'relationships': relationships,
            'fact_table_updates': fact_table_updates,
            'join_analysis': {
                'total_joins': len(all_joins),
                'package_joins': len(package_joins),
                'report_joins': len(report_joins),
                'inferred_joins': len(inferred_joins)
            },
            'recommendations': self._generate_recommendations(staging_tables, all_joins)
        }
        
        self.logger.info(f"Staging analysis complete: {len(staging_tables)} staging tables identified")
        return analysis_result

    def _identify_staging_candidates(self, join_patterns: List[JoinPattern], 
                                   settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify which table groups are candidates for staging tables"""
        candidates = []
        
        # Group tables by connectivity
        table_groups = self._group_connected_tables(join_patterns)
        
        for group in table_groups:
            if len(group) < 2:
                continue  # Skip single tables
                
            # Analyze the group's characteristics
            group_joins = [jp for jp in join_patterns 
                          if jp.left_table in group and jp.right_table in group]
            
            # Calculate complexity score
            complexity_score = self._calculate_group_complexity(group, group_joins)
            
            # Determine if this group should have a staging table
            should_create_staging = self._should_create_staging_table(
                group, group_joins, complexity_score, settings
            )
            
            if should_create_staging:
                candidates.append({
                    'tables': list(group),
                    'joins': group_joins,
                    'complexity_score': complexity_score,
                    'staging_type': self._determine_staging_type(group, group_joins)
                })
        
        return candidates

    def _generate_optimized_staging_tables(self, candidates: List[Dict[str, Any]], 
                                         all_joins: List[JoinPattern],
                                         package_info: Dict[str, Any],
                                         settings: Dict[str, Any]) -> List[StagingTableDefinition]:
        """Generate optimized staging table definitions"""
        staging_tables = []
        
        for candidate in candidates:
            tables = candidate['tables']
            joins = candidate['joins']
            staging_type = candidate['staging_type']
            
            # Generate staging table definition
            staging_table = self._create_staging_table_definition(
                tables, joins, package_info, settings, staging_type
            )
            
            if staging_table:
                # Add metadata
                metadata = self._generate_staging_metadata(staging_table, package_info)
                staging_table.metadata = metadata
                staging_tables.append(staging_table)
        
        return staging_tables

    def _create_staging_table_definition(self, tables: List[str], 
                                       joins: List[JoinPattern],
                                       package_info: Dict[str, Any],
                                       settings: Dict[str, Any],
                                       staging_type: str) -> Optional[StagingTableDefinition]:
        """Create a staging table definition for a group of tables"""
        try:
            # Generate name
            prefix = settings.get('prefix', 'Staging_')
            staging_name = self._generate_staging_table_name(tables, prefix, staging_type)
            
            # Extract columns from package info
            columns = self._extract_staging_columns(tables, package_info, joins)
            
            # Generate shared keys
            shared_keys = self._generate_shared_keys_for_staging(joins, settings)
            
            # Generate SQL definition
            sql_definition = self._generate_optimized_sql(tables, joins, staging_type)
            
            return StagingTableDefinition(
                name=staging_name,
                source_tables=tables,
                shared_keys=shared_keys,
                join_patterns=joins,
                columns=columns,
                sql_definition=sql_definition
            )
            
        except Exception as e:
            self.logger.error(f"Error creating staging table definition: {e}")
            return None

    def _create_shared_key_definitions(self, staging_tables: List[StagingTableDefinition],
                                     settings: Dict[str, Any]) -> List[SharedKeyDefinition]:
        """Create shared key definitions for staging tables"""
        shared_keys = []
        
        for staging_table in staging_tables:
            # Extract unique keys from join patterns
            for pattern in staging_table.join_patterns:
                if pattern.composite_key:
                    # Create composite key
                    key_name = f"{staging_table.name}_CompositeKey"
                    
                    # Generate surrogate key formula if needed
                    surrogate_formula = None
                    if settings.get('join_analysis', {}).get('composite_key_handling') == 'create_surrogate':
                        surrogate_formula = self._generate_surrogate_key_formula(
                            pattern.left_columns + pattern.right_columns
                        )
                    
                    shared_key = SharedKeyDefinition(
                        name=key_name,
                        source_columns=pattern.left_columns + pattern.right_columns,
                        target_tables=[pattern.left_table, pattern.right_table],
                        is_composite=True,
                        surrogate_key_formula=surrogate_formula
                    )
                    shared_keys.append(shared_key)
                else:
                    # Simple key
                    for left_col, right_col in zip(pattern.left_columns, pattern.right_columns):
                        if left_col == right_col:  # Same column name
                            shared_key = SharedKeyDefinition(
                                name=f"{staging_table.name}_{left_col}",
                                source_columns=[left_col],
                                target_tables=[pattern.left_table, pattern.right_table],
                                is_composite=False
                            )
                            shared_keys.append(shared_key)
        
        return shared_keys

    def _generate_staging_relationships(self, staging_tables: List[StagingTableDefinition],
                                      shared_keys: List[SharedKeyDefinition]) -> List[Dict[str, Any]]:
        """Generate relationship definitions between staging and fact tables"""
        relationships = []
        
        for staging_table in staging_tables:
            for source_table in staging_table.source_tables:
                # Find applicable shared keys
                table_keys = [sk for sk in shared_keys 
                             if source_table in sk.target_tables]
                
                for key in table_keys:
                    relationship = {
                        'from_table': staging_table.name,
                        'from_column': key.name,
                        'to_table': source_table,
                        'to_column': key.source_columns[0] if not key.is_composite else key.name,
                        'cardinality': 'oneToMany',
                        'cross_filtering_behavior': 'oneDirection',
                        'is_active': True,
                        'staging_relationship': True
                    }
                    relationships.append(relationship)
        
        return relationships

    def _analyze_fact_table_updates(self, staging_tables: List[StagingTableDefinition],
                                  package_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze required updates to fact tables to use staging tables"""
        updates = []
        
        for staging_table in staging_tables:
            for source_table in staging_table.source_tables:
                # Find the table in package info
                table_info = self._find_table_in_package(source_table, package_info)
                if table_info:
                    update = {
                        'table_name': source_table,
                        'staging_table': staging_table.name,
                        'required_changes': {
                            'add_shared_key_column': True,
                            'update_m_query': True,
                            'modify_relationships': True
                        },
                        'shared_keys_to_add': staging_table.shared_keys,
                        'new_m_query_template': self._generate_fact_table_m_query_template(
                            source_table, staging_table
                        )
                    }
                    updates.append(update)
        
        return updates

    def _generate_recommendations(self, staging_tables: List[StagingTableDefinition],
                                join_patterns: List[JoinPattern]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        if staging_tables:
            recommendations.append(
                f"Created {len(staging_tables)} staging tables to optimize complex joins"
            )
        
        # Analyze join complexity
        complex_joins = [jp for jp in join_patterns if jp.composite_key]
        if complex_joins:
            recommendations.append(
                f"Found {len(complex_joins)} composite key relationships - "
                "consider creating surrogate keys for better performance"
            )
        
        # Performance recommendations
        large_staging_tables = [st for st in staging_tables if len(st.source_tables) > 3]
        if large_staging_tables:
            recommendations.append(
                "Some staging tables involve many source tables - "
                "monitor performance and consider further decomposition if needed"
            )
        
        return recommendations

    # Helper methods
    
    def _group_connected_tables(self, join_patterns: List[JoinPattern]) -> List[Set[str]]:
        """Group tables into connected components"""
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
        
        # Find connected components
        visited = set()
        components = []
        
        for table in all_tables:
            if table not in visited:
                component = set()
                self._dfs_connected_tables(table, graph, visited, component)
                components.append(component)
        
        return components

    def _dfs_connected_tables(self, node: str, graph: Dict[str, Set[str]], 
                            visited: Set[str], component: Set[str]):
        """DFS for connected components"""
        visited.add(node)
        component.add(node)
        
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                self._dfs_connected_tables(neighbor, graph, visited, component)

    def _calculate_group_complexity(self, tables: Set[str], 
                                  joins: List[JoinPattern]) -> float:
        """Calculate complexity score for a table group"""
        score = 0.0
        
        # Base score from number of tables
        score += len(tables) * 0.2
        
        # Add score for number of joins
        score += len(joins) * 0.3
        
        # Add score for composite keys
        composite_joins = [j for j in joins if j.composite_key]
        score += len(composite_joins) * 0.5
        
        # Add score for different join types
        join_types = set(j.join_type for j in joins)
        score += len(join_types) * 0.1
        
        return score

    def _should_create_staging_table(self, tables: Set[str], 
                                   joins: List[JoinPattern],
                                   complexity_score: float,
                                   settings: Dict[str, Any]) -> bool:
        """Determine if a staging table should be created for this group"""
        mode = settings.get('mode', 'auto')
        
        if mode == 'off':
            return False
        elif mode == 'manual':
            # Manual mode - only create if explicitly configured
            return False  # Would need additional configuration
        elif mode == 'auto':
            # Auto mode - use heuristics
            return (
                len(tables) >= 2 and  # At least 2 tables
                complexity_score >= 0.5 and  # Minimum complexity
                len(joins) >= 1  # At least one join
            )
        
        return False

    def _determine_staging_type(self, tables: Set[str], 
                              joins: List[JoinPattern]) -> str:
        """Determine the type of staging table needed"""
        if len(tables) == 2:
            return "simple_join"
        elif len(tables) <= 4:
            return "multi_table"
        else:
            return "complex_hub"

    def _generate_staging_table_name(self, tables: List[str], 
                                   prefix: str, staging_type: str) -> str:
        """Generate a meaningful name for the staging table"""
        # Sort tables for consistent naming
        sorted_tables = sorted(tables)
        
        if staging_type == "simple_join":
            return f"{prefix}{sorted_tables[0]}_{sorted_tables[1]}"
        elif len(sorted_tables) <= 3:
            return f"{prefix}{'_'.join(sorted_tables)}"
        else:
            # For complex staging tables, use a more generic name
            return f"{prefix}Hub_{len(sorted_tables)}Tables"

    def _extract_staging_columns(self, tables: List[str], 
                               package_info: Dict[str, Any],
                               joins: List[JoinPattern]) -> List[Dict[str, Any]]:
        """Extract column definitions for staging table"""
        columns = []
        
        # Add shared key columns
        for join in joins:
            for col in join.left_columns + join.right_columns:
                if not any(c['name'] == col for c in columns):
                    columns.append({
                        'name': col,
                        'datatype': 'string',  # Default type
                        'is_key': True,
                        'source_tables': [join.left_table, join.right_table]
                    })
        
        return columns

    def _generate_shared_keys_for_staging(self, joins: List[JoinPattern],
                                        settings: Dict[str, Any]) -> List[str]:
        """Generate shared key definitions for staging table"""
        shared_keys = set()
        
        for join in joins:
            if join.composite_key:
                # Create composite key name
                composite_key = f"{'_'.join(join.left_columns)}_CompositeKey"
                shared_keys.add(composite_key)
            else:
                shared_keys.update(join.left_columns)
        
        return list(shared_keys)

    def _generate_optimized_sql(self, tables: List[str], 
                              joins: List[JoinPattern],
                              staging_type: str) -> str:
        """Generate optimized SQL for staging table"""
        # Start with main table
        main_table = sorted(tables)[0]
        sql_parts = [f"SELECT"]
        
        # Add column selections
        column_selections = []
        for table in sorted(tables):
            column_selections.append(f"{table}.*")
        
        sql_parts.append(f"    {', '.join(column_selections)}")
        sql_parts.append(f"FROM {main_table}")
        
        # Add joins
        joined_tables = {main_table}
        for join in joins:
            if join.left_table in joined_tables and join.right_table not in joined_tables:
                join_sql = self._format_join_clause(join, join.right_table)
                sql_parts.append(join_sql)
                joined_tables.add(join.right_table)
            elif join.right_table in joined_tables and join.left_table not in joined_tables:
                join_sql = self._format_join_clause(join, join.left_table)
                sql_parts.append(join_sql)
                joined_tables.add(join.left_table)
        
        return '\n'.join(sql_parts)

    def _format_join_clause(self, join: JoinPattern, table_to_join: str) -> str:
        """Format a JOIN clause"""
        join_type_map = {
            'INNER': 'INNER JOIN',
            'LEFT': 'LEFT JOIN',
            'RIGHT': 'RIGHT JOIN',
            'FULL': 'FULL OUTER JOIN'
        }
        
        join_clause = join_type_map.get(join.join_type, 'INNER JOIN')
        
        # Build ON condition
        conditions = []
        for left_col, right_col in zip(join.left_columns, join.right_columns):
            conditions.append(f"{join.left_table}.{left_col} = {join.right_table}.{right_col}")
        
        on_clause = " AND ".join(conditions)
        return f"{join_clause} {table_to_join} ON {on_clause}"

    def _generate_surrogate_key_formula(self, columns: List[str]) -> str:
        """Generate a surrogate key formula for composite keys"""
        # Create a formula that concatenates the columns
        return " & \"_\" & ".join([f"[{col}]" for col in columns])

    def _find_table_in_package(self, table_name: str, 
                             package_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find table information in package data"""
        query_subjects = package_info.get('query_subjects', [])
        for qs in query_subjects:
            if qs.get('name') == table_name:
                return qs
        return None

    def _generate_fact_table_m_query_template(self, fact_table: str,
                                            staging_table: StagingTableDefinition) -> str:
        """Generate M-query template for fact table to use staging table"""
        template = f"""let
    Source = Sql.Database("server", "database"),
    {fact_table}Data = Source{{[Schema="schema",Item="{fact_table}"]}}[Data],
    StagingData = {staging_table.name},
    // Add shared key columns
    AddSharedKeys = Table.AddColumn({fact_table}Data, "SharedKey", 
        each {self._generate_shared_key_expression(staging_table.shared_keys)}),
    // Join with staging table if needed
    Result = AddSharedKeys
in
    Result"""
        return template

    def _generate_shared_key_expression(self, shared_keys: List[str]) -> str:
        """Generate M-query expression for shared key creation"""
        if len(shared_keys) == 1:
            return f"[{shared_keys[0]}]"
        else:
            return " & \"_\" & ".join([f"[{key}]" for key in shared_keys])

    def _generate_staging_metadata(self, staging_table: StagingTableDefinition,
                                 package_info: Dict[str, Any]) -> StagingTableMetadata:
        """Generate metadata for staging table"""
        # Analyze which tables are likely facts vs dimensions
        fact_candidates = []
        dimension_candidates = []
        
        for table in staging_table.source_tables:
            table_info = self._find_table_in_package(table, package_info)
            if table_info:
                # Simple heuristic: tables with many numeric columns are likely facts
                numeric_columns = [
                    col for col in table_info.get('columns', [])
                    if col.get('datatype', '').lower() in ['int', 'decimal', 'float', 'double']
                ]
                
                if len(numeric_columns) > 2:
                    fact_candidates.append(table)
                else:
                    dimension_candidates.append(table)
        
        return StagingTableMetadata(
            fact_table_mappings={},  # Would be populated with detailed analysis
            dimension_candidates=dimension_candidates,
            relationship_definitions=[],  # Would be populated with relationship details
            performance_notes=[
                f"Staging table combines {len(staging_table.source_tables)} source tables",
                f"Uses {len(staging_table.shared_keys)} shared keys for relationships"
            ]
        ) 