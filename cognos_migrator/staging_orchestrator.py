"""
Staging Table Orchestrator for Power BI semantic model optimization.

This module coordinates all staging table functionality including SQL join analysis,
staging table creation, M-query generation, relationship creation, and fact table updates.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict

from .extractors.sql_join_analyzer import SQLJoinAnalyzer, JoinPattern, StagingTableDefinition
from .extractors.staging_table_analyzer import StagingTableAnalyzer, SharedKeyDefinition
from .converters.staging_mquery_converter import StagingMQueryConverter
from .generators.staging_relationship_generator import StagingRelationshipGenerator, StagingRelationship
from .processors.fact_table_updater import FactTableUpdater, FactTableUpdate
from .llm_service import LLMServiceClient
from .models import DataModel


class StagingTableOrchestrator:
    """Orchestrates the complete staging table implementation process"""
    
    def __init__(self, 
                 llm_service_client: Optional[LLMServiceClient] = None,
                 logger=None):
        """Initialize the staging table orchestrator
        
        Args:
            llm_service_client: Optional LLM service client
            logger: Optional logger instance
        """
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.sql_join_analyzer = SQLJoinAnalyzer(llm_service_client, logger)
        self.staging_analyzer = StagingTableAnalyzer(self.sql_join_analyzer, llm_service_client, logger)
        self.mquery_converter = StagingMQueryConverter(llm_service_client, logger=logger)
        self.relationship_generator = StagingRelationshipGenerator(logger)
        self.fact_table_updater = FactTableUpdater(
            self.mquery_converter, llm_service_client, logger
        )
    
    def implement_staging_tables(self,
                               package_info: Dict[str, Any],
                               report_queries: List[Dict[str, Any]],
                               data_model: DataModel,
                               output_path: Path,
                               settings: Dict[str, Any]) -> Dict[str, Any]:
        """Implement complete staging table solution
        
        Args:
            package_info: Extracted Cognos package information
            report_queries: List of report query definitions
            data_model: Current Power BI data model
            output_path: Output directory for generated files
            settings: Staging table configuration settings
            
        Returns:
            Dictionary containing implementation results
        """
        self.logger.info("Starting staging table implementation")
        
        # Check if staging tables are enabled
        staging_settings = settings.get('staging_tables', {})
        if not staging_settings.get('enabled', False):
            self.logger.info("Staging tables are disabled in settings")
            return {'staging_enabled': False}
        
        try:
            # Step 1: Analyze staging requirements
            self.logger.info("Step 1: Analyzing staging table requirements")
            staging_analysis = self.staging_analyzer.analyze_staging_requirements(
                package_info, report_queries, staging_settings
            )
            
            if not staging_analysis.get('staging_tables'):
                self.logger.info("No staging tables needed based on analysis")
                return {
                    'staging_enabled': True,
                    'staging_tables_created': 0,
                    'analysis': staging_analysis
                }
            
            # Step 2: Generate M-queries for staging tables
            self.logger.info("Step 2: Generating M-queries for staging tables")
            staging_m_queries = self._generate_staging_m_queries(
                staging_analysis['staging_tables'],
                staging_analysis['shared_keys'],
                staging_settings
            )
            
            # Step 3: Create staging table relationships
            self.logger.info("Step 3: Creating staging table relationships")
            staging_relationships = self._create_staging_relationships(
                staging_analysis['staging_tables'],
                staging_analysis['shared_keys'],
                data_model,
                staging_settings
            )
            
            # Step 4: Update fact tables
            self.logger.info("Step 4: Updating fact tables for staging integration")
            fact_table_updates = self._update_fact_tables(
                staging_analysis['staging_tables'],
                staging_analysis['shared_keys'],
                data_model,
                staging_settings
            )
            
            # Step 5: Generate TMDL files
            self.logger.info("Step 5: Generating TMDL files")
            tmdl_files = self._generate_tmdl_files(
                staging_analysis['staging_tables'],
                staging_relationships,
                staging_m_queries,
                output_path
            )
            
            # Step 6: Generate documentation
            self.logger.info("Step 6: Generating documentation")
            documentation = self._generate_documentation(
                staging_analysis,
                staging_relationships,
                fact_table_updates,
                output_path
            )
            
            # Compile results
            results = {
                'staging_enabled': True,
                'staging_tables_created': len(staging_analysis['staging_tables']),
                'shared_keys_created': len(staging_analysis['shared_keys']),
                'relationships_created': len(staging_relationships),
                'fact_tables_updated': len([u for u in fact_table_updates if u.success]),
                'analysis': staging_analysis,
                'staging_m_queries': staging_m_queries,
                'relationships': [asdict(r) for r in staging_relationships],
                'fact_table_updates': [asdict(u) for u in fact_table_updates],
                'tmdl_files': tmdl_files,
                'documentation': documentation,
                'recommendations': self._generate_implementation_recommendations(
                    staging_analysis, staging_relationships, fact_table_updates
                )
            }
            
            self.logger.info(f"Staging table implementation complete: "
                           f"{results['staging_tables_created']} staging tables, "
                           f"{results['relationships_created']} relationships, "
                           f"{results['fact_tables_updated']} fact tables updated")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error implementing staging tables: {e}")
            return {
                'staging_enabled': True,
                'error': str(e),
                'staging_tables_created': 0
            }
    
    def validate_staging_implementation(self,
                                      staging_tables: List[Dict[str, Any]],
                                      relationships: List[Dict[str, Any]],
                                      data_model: DataModel) -> Dict[str, Any]:
        """Validate the staging table implementation
        
        Args:
            staging_tables: List of staging table definitions
            relationships: List of staging relationships
            data_model: Data model to validate against
            
        Returns:
            Validation results
        """
        self.logger.info("Validating staging table implementation")
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Validate staging table definitions
        for staging_table in staging_tables:
            table_validation = self._validate_staging_table_definition(staging_table, data_model)
            if table_validation['errors']:
                validation_results['errors'].extend(table_validation['errors'])
                validation_results['is_valid'] = False
            validation_results['warnings'].extend(table_validation['warnings'])
        
        # Validate relationships
        for relationship in relationships:
            rel_validation = self._validate_staging_relationship(relationship, staging_tables, data_model)
            if rel_validation['errors']:
                validation_results['errors'].extend(rel_validation['errors'])
                validation_results['is_valid'] = False
            validation_results['warnings'].extend(rel_validation['warnings'])
        
        # Generate optimization recommendations
        optimization_recs = self._generate_optimization_recommendations(
            staging_tables, relationships, data_model
        )
        validation_results['recommendations'].extend(optimization_recs)
        
        return validation_results
    
    def _generate_staging_m_queries(self,
                                  staging_tables: List[Dict[str, Any]],
                                  shared_keys: List[Dict[str, Any]],
                                  settings: Dict[str, Any]) -> Dict[str, str]:
        """Generate M-queries for all staging tables"""
        m_queries = {}
        
        # Convert dictionaries back to objects
        staging_definitions = [
            StagingTableDefinition(**st) for st in staging_tables
        ]
        shared_key_definitions = [
            SharedKeyDefinition(**sk) for sk in shared_keys
        ]
        
        connection_info = {
            'server': settings.get('database_server', 'server'),
            'database': settings.get('database_name', 'database')
        }
        
        for staging_table in staging_definitions:
            # Find relevant shared keys
            relevant_keys = [
                sk for sk in shared_key_definitions 
                if any(table in sk.target_tables for table in staging_table.source_tables)
            ]
            
            # Generate M-query
            m_query = self.mquery_converter.convert_staging_table_to_m_query(
                staging_table,
                relevant_keys,
                connection_info,
                settings
            )
            
            m_queries[staging_table.name] = m_query
        
        return m_queries
    
    def _create_staging_relationships(self,
                                    staging_tables: List[Dict[str, Any]],
                                    shared_keys: List[Dict[str, Any]],
                                    data_model: DataModel,
                                    settings: Dict[str, Any]) -> List[StagingRelationship]:
        """Create relationships for staging tables"""
        # Convert dictionaries back to objects
        staging_definitions = [
            StagingTableDefinition(**st) for st in staging_tables
        ]
        shared_key_definitions = [
            SharedKeyDefinition(**sk) for sk in shared_keys
        ]
        
        return self.relationship_generator.generate_staging_relationships(
            staging_definitions,
            shared_key_definitions,
            data_model,
            settings
        )
    
    def _update_fact_tables(self,
                          staging_tables: List[Dict[str, Any]],
                          shared_keys: List[Dict[str, Any]],
                          data_model: DataModel,
                          settings: Dict[str, Any]) -> List[FactTableUpdate]:
        """Update fact tables for staging integration"""
        # Convert dictionaries back to objects
        staging_definitions = [
            StagingTableDefinition(**st) for st in staging_tables
        ]
        shared_key_definitions = [
            SharedKeyDefinition(**sk) for sk in shared_keys
        ]
        
        return self.fact_table_updater.update_fact_tables_for_staging(
            staging_definitions,
            shared_key_definitions,
            data_model,
            settings
        )
    
    def _generate_tmdl_files(self,
                           staging_tables: List[Dict[str, Any]],
                           relationships: List[StagingRelationship],
                           m_queries: Dict[str, str],
                           output_path: Path) -> Dict[str, str]:
        """Generate TMDL files for staging tables"""
        tmdl_files = {}
        
        # Create staging tables directory
        staging_dir = output_path / "staging_tables"
        staging_dir.mkdir(exist_ok=True)
        
        # Generate table TMDL files
        for staging_table in staging_tables:
            table_name = staging_table['name']
            m_query = m_queries.get(table_name, '')
            
            tmdl_content = self._generate_table_tmdl(staging_table, m_query)
            tmdl_file = staging_dir / f"{table_name}.tmdl"
            
            with open(tmdl_file, 'w', encoding='utf-8') as f:
                f.write(tmdl_content)
            
            tmdl_files[f"tables/{table_name}.tmdl"] = tmdl_content
        
        # Generate relationships TMDL
        relationships_tmdl = self.relationship_generator.generate_relationship_tmdl(
            relationships, staging_dir
        )
        tmdl_files["staging_relationships.tmdl"] = relationships_tmdl
        
        return tmdl_files
    
    def _generate_table_tmdl(self, staging_table: Dict[str, Any], m_query: str) -> str:
        """Generate TMDL content for a staging table"""
        lines = []
        
        lines.append(f"table {staging_table['name']}")
        lines.append(f"    lineageTag: staging-{staging_table['name'].lower()}")
        lines.append("")
        
        # Add columns
        for column in staging_table.get('columns', []):
            lines.append(f"    column {column['name']}")
            lines.append(f"        dataType: {column.get('datatype', 'string')}")
            lines.append(f"        sourceColumn: {column['name']}")
            
            if column.get('is_key'):
                lines.append("        isKey")
            
            lines.append(f"        lineageTag: staging-{column['name'].lower()}")
            lines.append("")
        
        # Add partition
        lines.append(f"    partition {staging_table['name']} = m")
        lines.append("        mode: import")
        lines.append("        source =")
        
        # Add M-query with proper indentation
        for line in m_query.split('\n'):
            lines.append(f"            {line}")
        
        return '\n'.join(lines)
    
    def _generate_documentation(self,
                              staging_analysis: Dict[str, Any],
                              relationships: List[StagingRelationship],
                              fact_updates: List[FactTableUpdate],
                              output_path: Path) -> Dict[str, str]:
        """Generate comprehensive documentation"""
        documentation = {}
        
        # Main staging implementation documentation
        main_doc = self._generate_main_documentation(
            staging_analysis, relationships, fact_updates
        )
        
        doc_file = output_path / "staging_implementation_guide.md"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(main_doc)
        documentation['main_guide'] = main_doc
        
        # Relationship documentation
        rel_doc = self.relationship_generator.generate_relationship_documentation(
            relationships, output_path
        )
        documentation['relationships'] = rel_doc
        
        # Fact table update documentation
        fact_doc = self.fact_table_updater.generate_update_documentation(
            fact_updates, output_path
        )
        documentation['fact_updates'] = fact_doc
        
        return documentation
    
    def _generate_main_documentation(self,
                                   staging_analysis: Dict[str, Any],
                                   relationships: List[StagingRelationship],
                                   fact_updates: List[FactTableUpdate]) -> str:
        """Generate main implementation documentation"""
        doc_lines = []
        
        doc_lines.append("# Staging Table Implementation Guide")
        doc_lines.append("")
        doc_lines.append("This document describes the staging table implementation for the Power BI semantic model.")
        doc_lines.append("")
        
        # Overview
        doc_lines.append("## Overview")
        doc_lines.append("")
        doc_lines.append(f"- **Staging Tables Created**: {len(staging_analysis.get('staging_tables', []))}")
        doc_lines.append(f"- **Shared Keys Defined**: {len(staging_analysis.get('shared_keys', []))}")
        doc_lines.append(f"- **Relationships Created**: {len(relationships)}")
        doc_lines.append(f"- **Fact Tables Updated**: {len([u for u in fact_updates if u.success])}")
        doc_lines.append("")
        
        # Staging tables
        staging_tables = staging_analysis.get('staging_tables', [])
        if staging_tables:
            doc_lines.append("## Staging Tables")
            doc_lines.append("")
            
            for table in staging_tables:
                doc_lines.append(f"### {table['name']}")
                doc_lines.append(f"- **Source Tables**: {', '.join(table['source_tables'])}")
                doc_lines.append(f"- **Shared Keys**: {', '.join(table['shared_keys'])}")
                doc_lines.append(f"- **Join Patterns**: {len(table.get('join_patterns', []))}")
                doc_lines.append("")
        
        # Implementation recommendations
        recommendations = staging_analysis.get('recommendations', [])
        if recommendations:
            doc_lines.append("## Implementation Recommendations")
            doc_lines.append("")
            for rec in recommendations:
                doc_lines.append(f"- {rec}")
            doc_lines.append("")
        
        return '\n'.join(doc_lines)
    
    def _generate_implementation_recommendations(self,
                                               staging_analysis: Dict[str, Any],
                                               relationships: List[StagingRelationship],
                                               fact_updates: List[FactTableUpdate]) -> List[str]:
        """Generate implementation recommendations"""
        recommendations = []
        
        staging_tables = staging_analysis.get('staging_tables', [])
        
        if staging_tables:
            recommendations.append(
                f"Successfully created {len(staging_tables)} staging tables to optimize join performance"
            )
        
        # Relationship recommendations
        active_relationships = [r for r in relationships if r.is_active]
        inactive_relationships = [r for r in relationships if not r.is_active]
        
        if inactive_relationships:
            recommendations.append(
                f"Created {len(inactive_relationships)} inactive relationships to avoid circular references - "
                "use USERELATIONSHIP in DAX when needed"
            )
        
        # Fact table update recommendations
        successful_updates = [u for u in fact_updates if u.success]
        failed_updates = [u for u in fact_updates if not u.success]
        
        if failed_updates:
            recommendations.append(
                f"Review {len(failed_updates)} failed fact table updates manually"
            )
        
        # Performance recommendations
        large_staging_tables = [st for st in staging_tables if len(st['source_tables']) > 3]
        if large_staging_tables:
            recommendations.append(
                "Monitor performance of large staging tables and consider further optimization if needed"
            )
        
        return recommendations
    
    def _validate_staging_table_definition(self, 
                                         staging_table: Dict[str, Any],
                                         data_model: DataModel) -> Dict[str, List[str]]:
        """Validate a single staging table definition"""
        errors = []
        warnings = []
        
        # Check if source tables exist in the model
        for source_table in staging_table.get('source_tables', []):
            if not any(t.name == source_table for t in data_model.tables):
                errors.append(f"Source table {source_table} not found in data model")
        
        # Check for shared keys
        if not staging_table.get('shared_keys'):
            warnings.append(f"Staging table {staging_table['name']} has no shared keys defined")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_staging_relationship(self,
                                     relationship: Dict[str, Any],
                                     staging_tables: List[Dict[str, Any]],
                                     data_model: DataModel) -> Dict[str, List[str]]:
        """Validate a staging relationship"""
        errors = []
        warnings = []
        
        # Check if tables exist
        from_table = relationship.get('from_table')
        to_table = relationship.get('to_table')
        
        all_table_names = [t.name for t in data_model.tables] + [st['name'] for st in staging_tables]
        
        if from_table not in all_table_names:
            errors.append(f"From table {from_table} not found")
        
        if to_table not in all_table_names:
            errors.append(f"To table {to_table} not found")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _generate_optimization_recommendations(self,
                                             staging_tables: List[Dict[str, Any]],
                                             relationships: List[Dict[str, Any]],
                                             data_model: DataModel) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Check for potential performance issues
        if len(staging_tables) > 5:
            recommendations.append(
                "Consider reviewing the number of staging tables - "
                "too many might complicate the model"
            )
        
        # Check relationship complexity
        bidirectional_rels = [r for r in relationships 
                            if r.get('cross_filtering_behavior') == 'bothDirections']
        
        if len(bidirectional_rels) > 3:
            recommendations.append(
                "Review bidirectional relationships - "
                "they can impact performance and create ambiguity"
            )
        
        return recommendations 