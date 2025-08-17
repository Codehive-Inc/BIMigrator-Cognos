"""
Staging Table M-Query Converter for Power BI semantic model optimization.

This module generates optimized M-queries for staging tables using LLM service calls
to create efficient queries that implement shared keys and follow Power BI best practices.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict

from .base_mquery_converter import BaseMQueryConverter
from ..extractors.staging_table_analyzer import StagingTableDefinition, SharedKeyDefinition
from ..llm_service import LLMServiceClient


class StagingMQueryConverter(BaseMQueryConverter):
    """Converts staging table definitions to optimized Power BI M-queries using LLM service"""
    
    def __init__(self, llm_service_client: Optional[LLMServiceClient] = None, 
                 output_path: Optional[str] = None, logger=None):
        """Initialize the staging M-query converter
        
        Args:
            llm_service_client: LLM service client for generating queries
            output_path: Output path for generated files
            logger: Optional logger instance
        """
        super().__init__(output_path)
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)

    def convert_to_m_query(self, table: Table, spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """Implementation of abstract method from BaseMQueryConverter
        
        Args:
            table: Table object
            spec: Optional specification
            data_sample: Optional data sample
            
        Returns:
            M-query string
        """
        # This method is implemented for compatibility with the base class
        # The main staging functionality is in convert_staging_table_to_m_query
        return self._build_default_m_query(table)

    def convert_staging_table_to_m_query(self, staging_definition: StagingTableDefinition,
                                       shared_keys: List[SharedKeyDefinition],
                                       connection_info: Dict[str, Any],
                                       settings: Dict[str, Any]) -> str:
        """Convert staging table definition to M-query
        
        Args:
            staging_definition: Staging table definition
            shared_keys: List of shared key definitions
            connection_info: Database connection information
            settings: Staging table settings
            
        Returns:
            Generated M-query string
        """
        self.logger.info(f"Converting staging table {staging_definition.name} to M-query")
        
        if self.llm_service_client and settings.get('join_analysis', {}).get('use_llm', True):
            # Use LLM service for advanced M-query generation
            return self._generate_m_query_with_llm(
                staging_definition, shared_keys, connection_info, settings
            )
        else:
            # Fallback to template-based generation
            return self._generate_m_query_template(
                staging_definition, shared_keys, connection_info, settings
            )

    def generate_shared_key_m_queries(self, fact_table: str,
                                    shared_keys: List[SharedKeyDefinition],
                                    connection_info: Dict[str, Any],
                                    settings: Dict[str, Any]) -> str:
        """Generate M-query for fact table with shared key additions
        
        Args:
            fact_table: Name of the fact table
            shared_keys: List of shared keys to add
            connection_info: Database connection information
            settings: Configuration settings
            
        Returns:
            M-query with shared key columns added
        """
        self.logger.info(f"Generating shared key M-query for fact table {fact_table}")
        
        if self.llm_service_client:
            return self._generate_fact_table_m_query_with_llm(
                fact_table, shared_keys, connection_info, settings
            )
        else:
            return self._generate_fact_table_m_query_template(
                fact_table, shared_keys, connection_info
            )

    def _generate_m_query_with_llm(self, staging_definition: StagingTableDefinition,
                                 shared_keys: List[SharedKeyDefinition],
                                 connection_info: Dict[str, Any],
                                 settings: Dict[str, Any]) -> str:
        """Generate M-query using LLM service"""
        try:
            # Prepare context for LLM
            context = {
                "task": "generate_staging_table_m_query",
                "staging_table": {
                    "name": staging_definition.name,
                    "source_tables": staging_definition.source_tables,
                    "join_patterns": [
                        {
                            "left_table": jp.left_table,
                            "right_table": jp.right_table,
                            "left_columns": jp.left_columns,
                            "right_columns": jp.right_columns,
                            "join_type": jp.join_type,
                            "composite_key": jp.composite_key
                        } for jp in staging_definition.join_patterns
                    ],
                    "columns": staging_definition.columns,
                    "sql_definition": staging_definition.sql_definition
                },
                "shared_keys": [asdict(sk) for sk in shared_keys],
                "connection_info": connection_info,
                "powerbi_best_practices": [
                    "Create efficient star schema relationships",
                    "Use proper data types for performance",
                    "Implement shared keys for relationship optimization",
                    "Handle composite keys with surrogate keys",
                    "Optimize for VertiPaq engine compression"
                ],
                "requirements": [
                    "Generate M-query that combines source tables using specified joins",
                    "Add shared key columns for relationships",
                    "Handle composite keys with surrogate key generation",
                    "Ensure proper data type handling",
                    "Include data cleaning and transformation steps",
                    "Follow Power BI M-query best practices"
                ]
            }
            
            # Call LLM service
            response = self._call_llm_staging_service(context)
            
            if response and response.get('m_query'):
                m_query = response['m_query']
                
                # Validate and clean the generated M-query
                cleaned_m_query = self._validate_and_clean_m_query(m_query)
                
                # Log any issues or recommendations
                if response.get('recommendations'):
                    self.logger.info(f"LLM recommendations for {staging_definition.name}: {response['recommendations']}")
                
                return cleaned_m_query
            else:
                self.logger.warning(f"LLM service returned invalid response for {staging_definition.name}")
                return self._generate_m_query_template(staging_definition, shared_keys, connection_info, settings)
                
        except Exception as e:
            self.logger.error(f"Error generating M-query with LLM for {staging_definition.name}: {e}")
            return self._generate_m_query_template(staging_definition, shared_keys, connection_info, settings)

    def _generate_fact_table_m_query_with_llm(self, fact_table: str,
                                            shared_keys: List[SharedKeyDefinition],
                                            connection_info: Dict[str, Any],
                                            settings: Dict[str, Any]) -> str:
        """Generate fact table M-query with shared keys using LLM"""
        try:
            context = {
                "task": "add_shared_keys_to_fact_table",
                "fact_table": fact_table,
                "shared_keys": [asdict(sk) for sk in shared_keys],
                "connection_info": connection_info,
                "requirements": [
                    "Add shared key columns to existing fact table",
                    "Preserve all existing columns and data",
                    "Handle composite keys with proper formulas",
                    "Ensure proper data types for keys",
                    "Optimize for performance and relationships"
                ]
            }
            
            response = self._call_llm_staging_service(context)
            
            if response and response.get('m_query'):
                return self._validate_and_clean_m_query(response['m_query'])
            else:
                return self._generate_fact_table_m_query_template(fact_table, shared_keys, connection_info)
                
        except Exception as e:
            self.logger.error(f"Error generating fact table M-query with LLM for {fact_table}: {e}")
            return self._generate_fact_table_m_query_template(fact_table, shared_keys, connection_info)

    def _call_llm_staging_service(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call LLM service for staging table M-query generation"""
        try:
            if not self.llm_service_client:
                return None
                
            # Prepare the request payload according to API specification
            if context.get("task") == "generate_staging_table_m_query":
                staging_table = context.get("staging_table", {})
                
                # Format for /api/mquery/staging endpoint
                api_payload = {
                    "table_name": staging_table.get("name", ""),
                    "source_info": {
                        "source_type": "sqlserver",  # or get from context
                        "server": context.get("connection_info", {}).get("server", "server"),
                        "database": context.get("connection_info", {}).get("database", "database"),
                        "source_tables": staging_table.get("source_tables", [])
                    },
                    "join_patterns": staging_table.get("join_patterns", []),
                    "shared_keys": context.get("shared_keys", []),
                    "etl_options": {
                        "add_shared_keys": True,
                        "optimize_for_powerbi": True,
                        "handle_composite_keys": True
                    },
                    "powerbi_requirements": context.get("requirements", []),
                    "best_practices": context.get("powerbi_best_practices", [])
                }
                
                # Call the staging M-query endpoint
                response = self.llm_service_client.call_api_endpoint(
                    endpoint="/api/mquery/staging",
                    method="POST",
                    payload=api_payload
                )
                
                if response and response.get("m_query"):
                    return {
                        "m_query": response["m_query"],
                        "etl_patterns_applied": response.get("etl_patterns_applied", []),
                        "processing_time": response.get("processing_time", 0),
                        "metadata": response.get("metadata", {}),
                        "recommendations": response.get("recommendations", [])
                    }
                    
            elif context.get("task") == "add_shared_keys_to_fact_table":
                # Format for /api/mquery/generate endpoint
                api_payload = {
                    "context": {
                        "table_name": context.get("fact_table", ""),
                        "existing_m_query": context.get("original_m_query", ""),
                        "shared_keys": context.get("shared_keys", []),
                        "source_info": context.get("connection_info", {}),
                        "modification_type": "add_shared_keys"
                    },
                    "options": {
                        "preserve_existing_logic": True,
                        "optimize_for_performance": True,
                        "add_comments": True
                    }
                }
                
                response = self.llm_service_client.call_api_endpoint(
                    endpoint="/api/mquery/generate",
                    method="POST", 
                    payload=api_payload
                )
                
                if response and response.get("m_query"):
                    return {
                        "m_query": response["m_query"],
                        "performance_notes": response.get("performance_notes", ""),
                        "confidence": response.get("confidence", 0.8),
                        "processing_time": response.get("processing_time", 0)
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calling LLM staging service: {e}")
            return None

    def _generate_m_query_template(self, staging_definition: StagingTableDefinition,
                                 shared_keys: List[SharedKeyDefinition],
                                 connection_info: Dict[str, Any],
                                 settings: Dict[str, Any]) -> str:
        """Generate M-query using templates (fallback method)"""
        
        # Extract connection details
        server = connection_info.get('server', 'server')
        database = connection_info.get('database', 'database')
        
        # Start building the M-query
        query_parts = []
        
        # Add let statement
        query_parts.append("let")
        
        # Add source connection
        query_parts.append(f'    Source = Sql.Database("{server}", "{database}"),')
        
        # Load each source table
        for i, table in enumerate(staging_definition.source_tables):
            var_name = f"Table{i+1}_{table}"
            query_parts.append(f'    {var_name} = Source{{[Schema="dbo",Item="{table}"]}}[Data],')
        
        # Create the main join logic
        if len(staging_definition.source_tables) == 2:
            # Simple two-table join
            join_query = self._generate_two_table_join(
                staging_definition.source_tables,
                staging_definition.join_patterns[0] if staging_definition.join_patterns else None
            )
            query_parts.append(f'    JoinedData = {join_query},')
        else:
            # Multi-table join
            join_query = self._generate_multi_table_join(
                staging_definition.source_tables,
                staging_definition.join_patterns
            )
            query_parts.append(f'    JoinedData = {join_query},')
        
        # Add shared key columns
        if shared_keys:
            key_additions = self._generate_shared_key_additions(shared_keys)
            for key_addition in key_additions:
                query_parts.append(f'    {key_addition},')
        
        # Final result
        final_step = "AddedSharedKeys" if shared_keys else "JoinedData"
        query_parts.append(f'    Result = {final_step}')
        
        # Add in statement
        query_parts.append("in")
        query_parts.append("    Result")
        
        return '\n'.join(query_parts)

    def _generate_two_table_join(self, tables: List[str], 
                               join_pattern: Optional[object]) -> str:
        """Generate M-query for two-table join"""
        table1, table2 = tables[0], tables[1]
        
        if not join_pattern:
            # Default merge
            return f'Table.NestedJoin(Table1_{table1}, {{"Key"}}, Table2_{table2}, {{"Key"}}, "JoinedTable", JoinKind.Inner)'
        
        # Build proper join based on pattern
        left_keys = [f'"{col}"' for col in join_pattern.left_columns]
        right_keys = [f'"{col}"' for col in join_pattern.right_columns]
        
        join_kind_map = {
            'INNER': 'JoinKind.Inner',
            'LEFT': 'JoinKind.LeftOuter',
            'RIGHT': 'JoinKind.RightOuter',
            'FULL': 'JoinKind.FullOuter'
        }
        
        join_kind = join_kind_map.get(join_pattern.join_type, 'JoinKind.Inner')
        
        return f'Table.NestedJoin(Table1_{table1}, {{{", ".join(left_keys)}}}, Table2_{table2}, {{{", ".join(right_keys)}}}, "JoinedTable", {join_kind})'

    def _generate_multi_table_join(self, tables: List[str], 
                                 join_patterns: List[object]) -> str:
        """Generate M-query for multi-table join"""
        # For multi-table joins, we'll use a more complex approach
        # Start with first table and progressively join others
        
        result = f"Table1_{tables[0]}"
        
        for i in range(1, len(tables)):
            table = tables[i]
            # Find relevant join pattern
            join_pattern = None
            for pattern in join_patterns:
                if (pattern.left_table == tables[0] and pattern.right_table == table) or \
                   (pattern.right_table == tables[0] and pattern.left_table == table):
                    join_pattern = pattern
                    break
            
            if join_pattern:
                left_keys = [f'"{col}"' for col in join_pattern.left_columns]
                right_keys = [f'"{col}"' for col in join_pattern.right_columns]
                
                result = f'Table.NestedJoin({result}, {{{", ".join(left_keys)}}}, Table{i+1}_{table}, {{{", ".join(right_keys)}}}, "Step{i}", JoinKind.Inner)'
            else:
                # Default join if no pattern found
                result = f'Table.NestedJoin({result}, {{"Key"}}, Table{i+1}_{table}, {{"Key"}}, "Step{i}", JoinKind.Inner)'
        
        return result

    def _generate_shared_key_additions(self, shared_keys: List[SharedKeyDefinition]) -> List[str]:
        """Generate M-query steps for adding shared key columns"""
        additions = []
        
        for i, key in enumerate(shared_keys):
            if key.is_composite and key.surrogate_key_formula:
                # Composite key with surrogate formula
                formula = self._convert_surrogate_formula_to_m_query(key.surrogate_key_formula)
                step_name = f"AddedKey{i+1}"
                prev_step = f"AddedKey{i}" if i > 0 else "JoinedData"
                
                additions.append(f'{step_name} = Table.AddColumn({prev_step}, "{key.name}", each {formula}, type text)')
            else:
                # Simple key
                step_name = f"AddedKey{i+1}"
                prev_step = f"AddedKey{i}" if i > 0 else "JoinedData"
                
                if len(key.source_columns) == 1:
                    additions.append(f'{step_name} = Table.AddColumn({prev_step}, "{key.name}", each [{key.source_columns[0]}], type text)')
                else:
                    # Multi-column key
                    formula = " & \"_\" & ".join([f'[{col}]' for col in key.source_columns])
                    additions.append(f'{step_name} = Table.AddColumn({prev_step}, "{key.name}", each {formula}, type text)')
        
        return additions

    def _generate_fact_table_m_query_template(self, fact_table: str,
                                            shared_keys: List[SharedKeyDefinition],
                                            connection_info: Dict[str, Any]) -> str:
        """Generate fact table M-query template with shared keys"""
        
        server = connection_info.get('server', 'server')
        database = connection_info.get('database', 'database')
        
        query_parts = []
        query_parts.append("let")
        query_parts.append(f'    Source = Sql.Database("{server}", "{database}"),')
        query_parts.append(f'    {fact_table}Data = Source{{[Schema="dbo",Item="{fact_table}"]}}[Data],')
        
        # Add shared key columns
        if shared_keys:
            key_additions = self._generate_shared_key_additions(shared_keys)
            for key_addition in key_additions:
                query_parts.append(f'    {key_addition},')
            
            final_step = f"AddedKey{len(shared_keys)}"
        else:
            final_step = f"{fact_table}Data"
        
        query_parts.append(f'    Result = {final_step}')
        query_parts.append("in")
        query_parts.append("    Result")
        
        return '\n'.join(query_parts)

    def _convert_surrogate_formula_to_m_query(self, formula: str) -> str:
        """Convert surrogate key formula to M-query syntax"""
        # Convert DAX-style formula to M-query
        # Example: [Col1] & "_" & [Col2] -> [Col1] & "_" & [Col2]
        # M-query syntax is similar but may need adjustments
        
        # Replace & with M-query concatenation
        m_formula = formula.replace(' & ', ' & ')
        
        # Ensure proper text conversion if needed
        m_formula = f'Text.From({m_formula})'
        
        return m_formula

    def _validate_and_clean_m_query(self, m_query: str) -> str:
        """Validate and clean generated M-query"""
        # Basic validation and cleaning
        cleaned = m_query.strip()
        
        # Ensure proper let/in structure
        if not cleaned.startswith('let'):
            cleaned = 'let\n' + cleaned
        
        if not cleaned.endswith('in\n    Result') and not cleaned.endswith('in Result'):
            if not 'in' in cleaned:
                cleaned += '\nin\n    Result'
        
        # Clean up extra whitespace
        lines = cleaned.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Preserve indentation but clean up extra spaces
            stripped = line.rstrip()
            if stripped:
                cleaned_lines.append(stripped)
        
        return '\n'.join(cleaned_lines)

    def generate_staging_table_relationships_m_query(self, staging_tables: List[StagingTableDefinition],
                                                   shared_keys: List[SharedKeyDefinition]) -> Dict[str, str]:
        """Generate M-queries for all staging table relationships
        
        Args:
            staging_tables: List of staging table definitions
            shared_keys: List of shared key definitions
            
        Returns:
            Dictionary mapping table names to M-queries
        """
        m_queries = {}
        
        for staging_table in staging_tables:
            # Get relevant shared keys for this staging table
            table_shared_keys = [
                sk for sk in shared_keys 
                if any(table in sk.target_tables for table in staging_table.source_tables)
            ]
            
            # Generate connection info (would typically come from settings)
            connection_info = {
                'server': 'server',
                'database': 'database'
            }
            
            # Generate M-query for this staging table
            m_query = self.convert_staging_table_to_m_query(
                staging_table,
                table_shared_keys,
                connection_info,
                {'join_analysis': {'use_llm': False}}  # Use template for batch generation
            )
            
            m_queries[staging_table.name] = m_query
        
        return m_queries 