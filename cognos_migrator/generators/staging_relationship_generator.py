"""
Staging Table Relationship Generator for Power BI semantic models.

This module generates relationship definitions between staging tables and fact tables,
following Power BI best practices for star schema design with proper cardinality and
cross-filtering behavior.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from ..extractors.staging_table_analyzer import StagingTableDefinition, SharedKeyDefinition
from ..models import Relationship, DataModel


@dataclass
class StagingRelationship:
    """Represents a relationship involving staging tables"""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str  # "oneToMany", "manyToOne", "oneToOne", "manyToMany"
    cross_filtering_behavior: str  # "oneDirection", "bothDirections"
    is_active: bool
    staging_relationship: bool = True
    relationship_type: str = "staging_to_fact"  # "staging_to_fact", "fact_to_staging", "staging_internal"


class StagingRelationshipGenerator:
    """Generates relationship definitions for staging tables in Power BI models"""
    
    def __init__(self, logger=None):
        """Initialize the staging relationship generator
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def generate_staging_relationships(self, 
                                     staging_tables: List[StagingTableDefinition],
                                     shared_keys: List[SharedKeyDefinition],
                                     existing_data_model: DataModel,
                                     settings: Dict[str, Any]) -> List[StagingRelationship]:
        """Generate all relationships for staging tables
        
        Args:
            staging_tables: List of staging table definitions
            shared_keys: List of shared key definitions  
            existing_data_model: Current data model
            settings: Staging configuration settings
            
        Returns:
            List of staging relationships
        """
        self.logger.info("Generating staging table relationships")
        
        relationships = []
        
        # Generate relationships between staging tables and fact tables
        for staging_table in staging_tables:
            staging_rels = self._generate_staging_to_fact_relationships(
                staging_table, shared_keys, existing_data_model, settings
            )
            relationships.extend(staging_rels)
        
        # Generate internal staging relationships if needed
        internal_rels = self._generate_internal_staging_relationships(
            staging_tables, shared_keys, settings
        )
        relationships.extend(internal_rels)
        
        # Optimize relationship directions and cardinalities
        optimized_rels = self._optimize_relationship_directions(relationships, existing_data_model)
        
        self.logger.info(f"Generated {len(optimized_rels)} staging relationships")
        return optimized_rels
    
    def _generate_staging_to_fact_relationships(self,
                                              staging_table: StagingTableDefinition,
                                              shared_keys: List[SharedKeyDefinition],
                                              data_model: DataModel,
                                              settings: Dict[str, Any]) -> List[StagingRelationship]:
        """Generate relationships between a staging table and its related fact tables"""
        relationships = []
        
        # Find shared keys relevant to this staging table
        relevant_keys = [
            sk for sk in shared_keys 
            if any(table in sk.target_tables for table in staging_table.source_tables)
        ]
        
        for source_table in staging_table.source_tables:
            # Determine if source table is a fact or dimension
            table_type = self._classify_table_type(source_table, data_model)
            
            # Find relevant shared keys for this source table
            table_keys = [sk for sk in relevant_keys if source_table in sk.target_tables]
            
            for shared_key in table_keys:
                if table_type == "fact":
                    # Fact table relationship: Staging (One) -> Fact (Many)
                    relationship = StagingRelationship(
                        from_table=staging_table.name,
                        from_column=shared_key.name,
                        to_table=source_table,
                        to_column=self._get_target_column_name(shared_key, source_table),
                        cardinality="oneToMany",
                        cross_filtering_behavior="oneDirection",
                        is_active=True,
                        relationship_type="staging_to_fact"
                    )
                    relationships.append(relationship)
                    
                elif table_type == "dimension":
                    # Dimension table relationship: Staging (Many) -> Dimension (One)
                    relationship = StagingRelationship(
                        from_table=source_table,
                        from_column=self._get_target_column_name(shared_key, source_table),
                        to_table=staging_table.name,
                        to_column=shared_key.name,
                        cardinality="manyToOne",
                        cross_filtering_behavior="oneDirection",
                        is_active=True,
                        relationship_type="fact_to_staging"
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _generate_internal_staging_relationships(self,
                                               staging_tables: List[StagingTableDefinition],
                                               shared_keys: List[SharedKeyDefinition],
                                               settings: Dict[str, Any]) -> List[StagingRelationship]:
        """Generate relationships between staging tables if needed"""
        relationships = []
        
        # Only create internal relationships if explicitly configured
        if not settings.get('create_internal_staging_relationships', False):
            return relationships
        
        # Find staging tables that share common source tables
        for i, staging1 in enumerate(staging_tables):
            for j, staging2 in enumerate(staging_tables[i+1:], i+1):
                common_tables = set(staging1.source_tables) & set(staging2.source_tables)
                
                if common_tables:
                    # Find shared keys that apply to both staging tables
                    common_keys = self._find_common_shared_keys(staging1, staging2, shared_keys)
                    
                    for shared_key in common_keys:
                        relationship = StagingRelationship(
                            from_table=staging1.name,
                            from_column=shared_key.name,
                            to_table=staging2.name,
                            to_column=shared_key.name,
                            cardinality="oneToOne",
                            cross_filtering_behavior="bothDirections",
                            is_active=False,  # Inactive to avoid circular references
                            relationship_type="staging_internal"
                        )
                        relationships.append(relationship)
        
        return relationships
    
    def _optimize_relationship_directions(self,
                                        relationships: List[StagingRelationship],
                                        data_model: DataModel) -> List[StagingRelationship]:
        """Optimize relationship directions and cardinalities"""
        optimized = []
        
        # Group relationships by table pairs
        relationship_groups = self._group_relationships_by_tables(relationships)
        
        for (table1, table2), group_rels in relationship_groups.items():
            if len(group_rels) == 1:
                optimized.extend(group_rels)
                continue
            
            # Multiple relationships between same tables - optimize
            optimized_group = self._resolve_multiple_relationships(group_rels, data_model)
            optimized.extend(optimized_group)
        
        return optimized
    
    def generate_relationship_tmdl(self,
                                 relationships: List[StagingRelationship],
                                 output_path: Path) -> str:
        """Generate TMDL relationship definitions
        
        Args:
            relationships: List of staging relationships
            output_path: Output path for the TMDL file
            
        Returns:
            TMDL relationship content
        """
        self.logger.info(f"Generating TMDL for {len(relationships)} staging relationships")
        
        tmdl_lines = []
        tmdl_lines.append("// Staging Table Relationships")
        tmdl_lines.append("// Generated automatically from staging table analysis")
        tmdl_lines.append("")
        
        for rel in relationships:
            tmdl_lines.extend(self._generate_single_relationship_tmdl(rel))
            tmdl_lines.append("")
        
        tmdl_content = '\n'.join(tmdl_lines)
        
        # Save to file if output path provided
        if output_path:
            relationships_file = output_path / "staging_relationships.tmdl"
            with open(relationships_file, 'w', encoding='utf-8') as f:
                f.write(tmdl_content)
            self.logger.info(f"Saved staging relationships TMDL to {relationships_file}")
        
        return tmdl_content
    
    def _generate_single_relationship_tmdl(self, relationship: StagingRelationship) -> List[str]:
        """Generate TMDL for a single relationship"""
        lines = []
        
        # Generate relationship name
        rel_name = f"{relationship.from_table}_to_{relationship.to_table}"
        if relationship.staging_relationship:
            rel_name += "_Staging"
        
        lines.append(f"relationship '{rel_name}' = {{")
        lines.append(f"    fromTable: {relationship.from_table}")
        lines.append(f"    fromColumn: {relationship.from_column}")
        lines.append(f"    toTable: {relationship.to_table}")
        lines.append(f"    toColumn: {relationship.to_column}")
        lines.append(f"    cardinality: {relationship.cardinality}")
        lines.append(f"    crossFilteringBehavior: {relationship.cross_filtering_behavior}")
        lines.append(f"    isActive: {str(relationship.is_active).lower()}")
        
        # Add staging-specific annotations
        if relationship.staging_relationship:
            lines.append("    annotations: [")
            lines.append('        Annotation(Name="StagingRelationship", Value="true"),')
            lines.append(f'        Annotation(Name="RelationshipType", Value="{relationship.relationship_type}")')
            lines.append("    ]")
        
        lines.append("}")
        
        return lines
    
    def update_existing_relationships(self,
                                    existing_relationships: List[Relationship],
                                    staging_relationships: List[StagingRelationship],
                                    settings: Dict[str, Any]) -> List[Relationship]:
        """Update existing relationships to work with staging tables
        
        Args:
            existing_relationships: Current model relationships
            staging_relationships: New staging relationships
            settings: Configuration settings
            
        Returns:
            Updated list of relationships
        """
        self.logger.info("Updating existing relationships for staging tables")
        
        updated_relationships = []
        
        # Convert staging relationships to standard relationships
        for staging_rel in staging_relationships:
            standard_rel = Relationship(
                from_table=staging_rel.from_table,
                from_column=staging_rel.from_column,
                to_table=staging_rel.to_table,
                to_column=staging_rel.to_column,
                cross_filtering_behavior=staging_rel.cross_filtering_behavior
            )
            # Add staging metadata
            if not hasattr(standard_rel, 'metadata'):
                standard_rel.metadata = {}
            standard_rel.metadata['is_staging_relationship'] = True
            standard_rel.metadata['relationship_type'] = staging_rel.relationship_type
            
            updated_relationships.append(standard_rel)
        
        # Handle existing relationships
        staging_table_names = set()
        for staging_rel in staging_relationships:
            staging_table_names.add(staging_rel.from_table)
            staging_table_names.add(staging_rel.to_table)
        
        for existing_rel in existing_relationships:
            # Check if this relationship conflicts with staging relationships
            if self._relationship_conflicts_with_staging(existing_rel, staging_relationships):
                # Mark as inactive or modify
                if settings.get('deactivate_conflicting_relationships', True):
                    existing_rel.metadata = getattr(existing_rel, 'metadata', {})
                    existing_rel.metadata['deactivated_for_staging'] = True
                    # Keep the relationship but mark it for review
                    updated_relationships.append(existing_rel)
                # else: skip conflicting relationship
            else:
                # Keep non-conflicting relationships
                updated_relationships.append(existing_rel)
        
        return updated_relationships
    
    # Helper methods
    
    def _classify_table_type(self, table_name: str, data_model: DataModel) -> str:
        """Classify table as fact or dimension based on characteristics"""
        # Find the table in the data model
        table = None
        for t in data_model.tables:
            if t.name == table_name:
                table = t
                break
        
        if not table:
            return "unknown"
        
        # Simple heuristic: tables with many numeric columns are likely facts
        numeric_columns = 0
        total_columns = len(table.columns)
        
        for column in table.columns:
            if column.data_type in ['Int64', 'Double', 'Decimal', 'Currency']:
                numeric_columns += 1
        
        if total_columns > 0 and (numeric_columns / total_columns) > 0.3:
            return "fact"
        else:
            return "dimension"
    
    def _get_target_column_name(self, shared_key: SharedKeyDefinition, table_name: str) -> str:
        """Get the target column name for a shared key in a specific table"""
        # If it's a composite key, use the shared key name
        if shared_key.is_composite:
            return shared_key.name
        
        # For simple keys, use the original column name
        if len(shared_key.source_columns) == 1:
            return shared_key.source_columns[0]
        
        # Fallback to shared key name
        return shared_key.name
    
    def _find_common_shared_keys(self,
                               staging1: StagingTableDefinition,
                               staging2: StagingTableDefinition,
                               shared_keys: List[SharedKeyDefinition]) -> List[SharedKeyDefinition]:
        """Find shared keys that apply to both staging tables"""
        common_keys = []
        
        for shared_key in shared_keys:
            # Check if this key applies to both staging tables
            staging1_tables = set(staging1.source_tables)
            staging2_tables = set(staging2.source_tables)
            key_tables = set(shared_key.target_tables)
            
            if (key_tables & staging1_tables) and (key_tables & staging2_tables):
                common_keys.append(shared_key)
        
        return common_keys
    
    def _group_relationships_by_tables(self,
                                     relationships: List[StagingRelationship]) -> Dict[Tuple[str, str], List[StagingRelationship]]:
        """Group relationships by table pairs"""
        groups = {}
        
        for rel in relationships:
            # Create a consistent key regardless of direction
            key = tuple(sorted([rel.from_table, rel.to_table]))
            if key not in groups:
                groups[key] = []
            groups[key].append(rel)
        
        return groups
    
    def _resolve_multiple_relationships(self,
                                      relationships: List[StagingRelationship],
                                      data_model: DataModel) -> List[StagingRelationship]:
        """Resolve conflicts when multiple relationships exist between the same tables"""
        if len(relationships) <= 1:
            return relationships
        
        # Prioritize staging-to-fact relationships
        staging_to_fact = [r for r in relationships if r.relationship_type == "staging_to_fact"]
        if staging_to_fact:
            # Keep the first staging-to-fact relationship active
            result = [staging_to_fact[0]]
            
            # Mark others as inactive
            for rel in relationships[1:]:
                rel.is_active = False
                result.append(rel)
            
            return result
        
        # If no staging-to-fact relationships, keep first one active
        result = [relationships[0]]
        for rel in relationships[1:]:
            rel.is_active = False
            result.append(rel)
        
        return result
    
    def _relationship_conflicts_with_staging(self,
                                           existing_rel: Relationship,
                                           staging_relationships: List[StagingRelationship]) -> bool:
        """Check if an existing relationship conflicts with staging relationships"""
        for staging_rel in staging_relationships:
            # Check for same table pair with same columns
            if ((existing_rel.from_table == staging_rel.from_table and 
                 existing_rel.to_table == staging_rel.to_table and
                 existing_rel.from_column == staging_rel.from_column and
                 existing_rel.to_column == staging_rel.to_column) or
                (existing_rel.from_table == staging_rel.to_table and 
                 existing_rel.to_table == staging_rel.from_table and
                 existing_rel.from_column == staging_rel.to_column and
                 existing_rel.to_column == staging_rel.from_column)):
                return True
        
        return False
    
    def generate_relationship_documentation(self,
                                          relationships: List[StagingRelationship],
                                          output_path: Path) -> str:
        """Generate documentation for staging relationships"""
        doc_lines = []
        doc_lines.append("# Staging Table Relationships Documentation")
        doc_lines.append("")
        doc_lines.append("This document describes the relationships created for staging tables in the Power BI semantic model.")
        doc_lines.append("")
        
        # Group by relationship type
        by_type = {}
        for rel in relationships:
            rel_type = rel.relationship_type
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append(rel)
        
        for rel_type, type_rels in by_type.items():
            doc_lines.append(f"## {rel_type.replace('_', ' ').title()} Relationships")
            doc_lines.append("")
            
            for rel in type_rels:
                doc_lines.append(f"### {rel.from_table} → {rel.to_table}")
                doc_lines.append(f"- **From Column**: {rel.from_column}")
                doc_lines.append(f"- **To Column**: {rel.to_column}")
                doc_lines.append(f"- **Cardinality**: {rel.cardinality}")
                doc_lines.append(f"- **Cross-Filtering**: {rel.cross_filtering_behavior}")
                doc_lines.append(f"- **Active**: {rel.is_active}")
                doc_lines.append("")
        
        doc_content = '\n'.join(doc_lines)
        
        # Save documentation
        if output_path:
            doc_file = output_path / "staging_relationships_documentation.md"
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(doc_content)
            self.logger.info(f"Saved staging relationships documentation to {doc_file}")
        
        return doc_content 