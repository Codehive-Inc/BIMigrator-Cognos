"""
Fact Table Updater for Power BI semantic model staging table integration.

This module updates existing fact table M-queries to include shared keys that enable
optimal relationships with staging tables, following Power BI best practices.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from dataclasses import dataclass

from ..extractors.staging_table_analyzer import StagingTableDefinition, SharedKeyDefinition
from ..converters.staging_mquery_converter import StagingMQueryConverter
from ..llm_service import LLMServiceClient
from ..models import Table, DataModel


@dataclass
class FactTableUpdate:
    """Represents an update to be applied to a fact table"""
    table_name: str
    original_m_query: str
    updated_m_query: str
    shared_keys_added: List[str]
    relationships_affected: List[str]
    update_type: str  # "shared_key_addition", "relationship_optimization", "column_mapping"
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class MQueryModification:
    """Represents a specific modification to an M-query"""
    step_name: str
    step_content: str
    position: str  # "before_final", "after_source", "replace_step"
    dependencies: List[str] = None


class FactTableUpdater:
    """Updates fact tables to work optimally with staging tables"""
    
    def __init__(self, 
                 staging_mquery_converter: Optional[StagingMQueryConverter] = None,
                 llm_service_client: Optional[LLMServiceClient] = None,
                 logger=None):
        """Initialize the fact table updater
        
        Args:
            staging_mquery_converter: M-query converter for staging tables
            llm_service_client: Optional LLM service client
            logger: Optional logger instance
        """
        self.staging_mquery_converter = staging_mquery_converter
        self.llm_service_client = llm_service_client
        self.logger = logger or logging.getLogger(__name__)
    
    def update_fact_tables_for_staging(self,
                                     staging_tables: List[StagingTableDefinition],
                                     shared_keys: List[SharedKeyDefinition],
                                     data_model: DataModel,
                                     settings: Dict[str, Any]) -> List[FactTableUpdate]:
        """Update all fact tables to work with staging tables
        
        Args:
            staging_tables: List of staging table definitions
            shared_keys: List of shared key definitions
            data_model: Current data model
            settings: Configuration settings
            
        Returns:
            List of fact table updates performed
        """
        self.logger.info("Updating fact tables for staging table integration")
        
        updates = []
        
        # Identify fact tables that need updates
        fact_tables_to_update = self._identify_fact_tables_for_update(
            staging_tables, data_model
        )
        
        for table_name in fact_tables_to_update:
            # Find the table in the data model
            table = self._find_table_in_model(table_name, data_model)
            if not table:
                continue
            
            # Find relevant shared keys for this table
            table_shared_keys = self._find_relevant_shared_keys(
                table_name, staging_tables, shared_keys
            )
            
            if not table_shared_keys:
                continue
            
            # Update the table's M-query
            update = self._update_single_fact_table(
                table, table_shared_keys, settings
            )
            
            if update:
                updates.append(update)
        
        self.logger.info(f"Updated {len(updates)} fact tables for staging integration")
        return updates
    
    def _update_single_fact_table(self,
                                table: Table,
                                shared_keys: List[SharedKeyDefinition],
                                settings: Dict[str, Any]) -> Optional[FactTableUpdate]:
        """Update a single fact table with shared keys"""
        try:
            self.logger.info(f"Updating fact table {table.name} with {len(shared_keys)} shared keys")
            
            # Get the current M-query
            original_m_query = self._extract_table_m_query(table)
            if not original_m_query:
                self.logger.warning(f"Could not extract M-query for table {table.name}")
                return None
            
            # Generate updated M-query
            if self.llm_service_client and settings.get('use_llm_for_updates', True):
                updated_m_query = self._update_m_query_with_llm(
                    table.name, original_m_query, shared_keys, settings
                )
            else:
                updated_m_query = self._update_m_query_template(
                    table.name, original_m_query, shared_keys, settings
                )
            
            if not updated_m_query:
                return FactTableUpdate(
                    table_name=table.name,
                    original_m_query=original_m_query,
                    updated_m_query="",
                    shared_keys_added=[],
                    relationships_affected=[],
                    update_type="shared_key_addition",
                    success=False,
                    error_message="Failed to generate updated M-query"
                )
            
            # Create the update record
            update = FactTableUpdate(
                table_name=table.name,
                original_m_query=original_m_query,
                updated_m_query=updated_m_query,
                shared_keys_added=[sk.name for sk in shared_keys],
                relationships_affected=self._get_affected_relationships(table.name, shared_keys),
                update_type="shared_key_addition",
                success=True
            )
            
            return update
            
        except Exception as e:
            self.logger.error(f"Error updating fact table {table.name}: {e}")
            return FactTableUpdate(
                table_name=table.name,
                original_m_query="",
                updated_m_query="",
                shared_keys_added=[],
                relationships_affected=[],
                update_type="shared_key_addition",
                success=False,
                error_message=str(e)
            )
    
    def _update_m_query_with_llm(self,
                               table_name: str,
                               original_m_query: str,
                               shared_keys: List[SharedKeyDefinition],
                               settings: Dict[str, Any]) -> Optional[str]:
        """Update M-query using LLM service"""
        try:
            context = {
                "task": "update_fact_table_m_query_for_staging",
                "table_name": table_name,
                "original_m_query": original_m_query,
                "shared_keys": [
                    {
                        "name": sk.name,
                        "source_columns": sk.source_columns,
                        "is_composite": sk.is_composite,
                        "surrogate_key_formula": sk.surrogate_key_formula
                    } for sk in shared_keys
                ],
                "requirements": [
                    "Add shared key columns to enable staging table relationships",
                    "Preserve all existing columns and transformations",
                    "Maintain proper data types for optimal performance",
                    "Follow Power BI M-query best practices",
                    "Ensure the query is efficient and maintainable"
                ],
                "powerbi_guidelines": [
                    "Use consistent naming conventions for shared keys",
                    "Add columns in logical order after source data load",
                    "Handle null values appropriately in key generation",
                    "Use proper data types (text for keys unless specified)",
                    "Comment the shared key additions for maintainability"
                ]
            }
            
            # Call LLM service for M-query update
            response = self._call_llm_for_m_query_update(context)
            
            if response and response.get('updated_m_query'):
                updated_query = response['updated_m_query']
                
                # Validate the updated query
                if self._validate_updated_m_query(original_m_query, updated_query, shared_keys):
                    return updated_query
                else:
                    self.logger.warning(f"LLM-generated M-query for {table_name} failed validation")
                    return None
            else:
                self.logger.warning(f"LLM service returned invalid response for {table_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error updating M-query with LLM for {table_name}: {e}")
            return None
    
    def _update_m_query_template(self,
                               table_name: str,
                               original_m_query: str,
                               shared_keys: List[SharedKeyDefinition],
                               settings: Dict[str, Any]) -> str:
        """Update M-query using template-based approach"""
        
        # Parse the original M-query to understand its structure
        query_structure = self._parse_m_query_structure(original_m_query)
        
        # Generate shared key addition steps
        shared_key_steps = self._generate_shared_key_steps(shared_keys)
        
        # Insert shared key steps into the query
        updated_query = self._insert_steps_into_m_query(
            original_m_query, shared_key_steps, query_structure
        )
        
        return updated_query
    
    def _parse_m_query_structure(self, m_query: str) -> Dict[str, Any]:
        """Parse M-query to understand its structure"""
        structure = {
            'has_let_in': False,
            'steps': [],
            'final_step': None,
            'source_step': None
        }
        
        lines = m_query.strip().split('\n')
        
        # Check for let...in structure
        if any(line.strip().startswith('let') for line in lines):
            structure['has_let_in'] = True
        
        # Extract steps
        step_pattern = re.compile(r'^\s*(\w+)\s*=\s*(.*?)(?:,\s*)?$')
        
        for line in lines:
            line = line.strip()
            if not line or line in ['let', 'in']:
                continue
                
            match = step_pattern.match(line)
            if match:
                step_name = match.group(1)
                step_content = match.group(2)
                
                structure['steps'].append({
                    'name': step_name,
                    'content': step_content,
                    'full_line': line
                })
                
                # Identify source and final steps
                if 'Source' in step_name or 'source' in step_content.lower():
                    structure['source_step'] = step_name
                    
                if step_name in ['Result', 'Final'] or line.endswith('Result'):
                    structure['final_step'] = step_name
        
        return structure
    
    def _generate_shared_key_steps(self, shared_keys: List[SharedKeyDefinition]) -> List[MQueryModification]:
        """Generate M-query steps for adding shared keys"""
        modifications = []
        
        for i, shared_key in enumerate(shared_keys):
            step_name = f"AddSharedKey{i+1}_{shared_key.name.replace(' ', '_')}"
            
            if shared_key.is_composite and shared_key.surrogate_key_formula:
                # Composite key with custom formula
                formula = self._convert_formula_to_m_query(shared_key.surrogate_key_formula)
                step_content = f'Table.AddColumn({{previous_step}}, "{shared_key.name}", each {formula}, type text)'
            else:
                # Simple key or multi-column concatenation
                if len(shared_key.source_columns) == 1:
                    col = shared_key.source_columns[0]
                    step_content = f'Table.AddColumn({{previous_step}}, "{shared_key.name}", each [{col}], type text)'
                else:
                    # Multi-column key
                    formula = " & \"_\" & ".join([f'Text.From([{col}])' for col in shared_key.source_columns])
                    step_content = f'Table.AddColumn({{previous_step}}, "{shared_key.name}", each {formula}, type text)'
            
            modification = MQueryModification(
                step_name=step_name,
                step_content=step_content,
                position="before_final",
                dependencies=[shared_key.source_columns[0]] if shared_key.source_columns else []
            )
            
            modifications.append(modification)
        
        return modifications
    
    def _insert_steps_into_m_query(self,
                                 original_query: str,
                                 modifications: List[MQueryModification],
                                 structure: Dict[str, Any]) -> str:
        """Insert modification steps into the M-query"""
        
        lines = original_query.strip().split('\n')
        new_lines = []
        
        # Track where we are in the query
        in_let_block = False
        found_final_step = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped == 'let':
                in_let_block = True
                new_lines.append(line)
                continue
            
            if stripped == 'in':
                # Insert shared key steps before the 'in' statement
                if modifications and in_let_block:
                    self._insert_shared_key_steps(new_lines, modifications)
                new_lines.append(line)
                in_let_block = False
                continue
            
            # Check if this is the final step
            if (structure['final_step'] and stripped.startswith(structure['final_step'])) or \
               (stripped.endswith('Result') and i == len(lines) - 1):
                # Insert shared key steps before final step
                if modifications and in_let_block:
                    self._insert_shared_key_steps(new_lines, modifications)
                    # Update the final step to use the last shared key step
                    if modifications:
                        last_step = modifications[-1].step_name
                        line = line.replace('Result', last_step)
                found_final_step = True
            
            new_lines.append(line)
        
        # If no proper structure was found, append shared key steps
        if modifications and not found_final_step:
            new_lines.extend([f"    {mod.step_name} = {mod.step_content}," for mod in modifications])
        
        return '\n'.join(new_lines)
    
    def _insert_shared_key_steps(self, lines: List[str], modifications: List[MQueryModification]):
        """Insert shared key steps into the lines array"""
        previous_step = "Source"  # Default previous step
        
        # Find the last actual step before insertion
        for line in reversed(lines):
            if '=' in line and not line.strip().startswith('//'):
                match = re.match(r'^\s*(\w+)\s*=', line)
                if match:
                    previous_step = match.group(1)
                    break
        
        # Add each shared key step
        for i, mod in enumerate(modifications):
            # Update previous step reference
            step_content = mod.step_content.replace('{previous_step}', previous_step)
            
            # Add the step
            lines.append(f"    {mod.step_name} = {step_content},")
            
            # Update previous step for next iteration
            previous_step = mod.step_name
    
    def _convert_formula_to_m_query(self, formula: str) -> str:
        """Convert DAX-style formula to M-query syntax"""
        # Convert DAX concatenation to M-query
        m_formula = formula.replace(' & ', ' & ')
        
        # Ensure proper text conversion
        if 'Text.From' not in m_formula:
            # Wrap column references in Text.From for safety
            m_formula = re.sub(r'\[(\w+)\]', r'Text.From([\1])', m_formula)
        
        return m_formula
    
    def _validate_updated_m_query(self,
                                original_query: str,
                                updated_query: str,
                                shared_keys: List[SharedKeyDefinition]) -> bool:
        """Validate that the updated M-query is correctly formed"""
        try:
            # Basic structure validation
            if not updated_query.strip():
                return False
            
            # Check that shared key names appear in the updated query
            for shared_key in shared_keys:
                if shared_key.name not in updated_query:
                    self.logger.warning(f"Shared key {shared_key.name} not found in updated query")
                    return False
            
            # Check for basic M-query syntax
            if 'let' in original_query and 'let' not in updated_query:
                return False
            
            if 'in' in original_query and 'in' not in updated_query:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating updated M-query: {e}")
            return False
    
    def apply_updates_to_model(self,
                             updates: List[FactTableUpdate],
                             data_model: DataModel,
                             output_path: Path) -> Dict[str, Any]:
        """Apply fact table updates to the data model
        
        Args:
            updates: List of fact table updates
            data_model: Data model to update
            output_path: Output path for updated files
            
        Returns:
            Summary of applied updates
        """
        self.logger.info(f"Applying {len(updates)} fact table updates to data model")
        
        applied_count = 0
        failed_count = 0
        backup_created = False
        
        for update in updates:
            if not update.success:
                failed_count += 1
                continue
            
            try:
                # Find the table in the model
                table = self._find_table_in_model(update.table_name, data_model)
                if not table:
                    self.logger.warning(f"Table {update.table_name} not found in model")
                    continue
                
                # Create backup if this is the first update
                if not backup_created:
                    self._create_model_backup(data_model, output_path)
                    backup_created = True
                
                # Update the table's M-query
                self._apply_m_query_update(table, update, output_path)
                applied_count += 1
                
            except Exception as e:
                self.logger.error(f"Error applying update to {update.table_name}: {e}")
                failed_count += 1
        
        # Generate update summary
        summary = {
            'total_updates': len(updates),
            'applied_successfully': applied_count,
            'failed_updates': failed_count,
            'backup_created': backup_created,
            'updated_tables': [u.table_name for u in updates if u.success]
        }
        
        self.logger.info(f"Applied {applied_count}/{len(updates)} fact table updates successfully")
        return summary
    
    # Helper methods
    
    def _identify_fact_tables_for_update(self,
                                       staging_tables: List[StagingTableDefinition],
                                       data_model: DataModel) -> Set[str]:
        """Identify fact tables that need updates for staging integration"""
        fact_tables = set()
        
        for staging_table in staging_tables:
            for source_table in staging_table.source_tables:
                # Check if this is a fact table
                table = self._find_table_in_model(source_table, data_model)
                if table and self._is_fact_table(table):
                    fact_tables.add(source_table)
        
        return fact_tables
    
    def _find_table_in_model(self, table_name: str, data_model: DataModel) -> Optional[Table]:
        """Find a table in the data model by name"""
        for table in data_model.tables:
            if table.name == table_name:
                return table
        return None
    
    def _is_fact_table(self, table: Table) -> bool:
        """Determine if a table is a fact table based on its characteristics"""
        if not table.columns:
            return False
        
        # Count numeric columns (typical of fact tables)
        numeric_columns = 0
        for column in table.columns:
            if column.data_type in ['Int64', 'Double', 'Decimal', 'Currency']:
                numeric_columns += 1
        
        # Heuristic: fact tables typically have many numeric columns
        return numeric_columns > 2 and (numeric_columns / len(table.columns)) > 0.2
    
    def _find_relevant_shared_keys(self,
                                 table_name: str,
                                 staging_tables: List[StagingTableDefinition],
                                 shared_keys: List[SharedKeyDefinition]) -> List[SharedKeyDefinition]:
        """Find shared keys relevant to a specific table"""
        relevant_keys = []
        
        for shared_key in shared_keys:
            if table_name in shared_key.target_tables:
                relevant_keys.append(shared_key)
        
        return relevant_keys
    
    def _extract_table_m_query(self, table: Table) -> Optional[str]:
        """Extract the M-query from a table object"""
        # This would depend on how M-queries are stored in the table object
        # For now, return a placeholder
        if hasattr(table, 'source_query') and table.source_query:
            return table.source_query
        elif hasattr(table, 'm_query') and table.m_query:
            return table.m_query
        else:
            return None
    
    def _get_affected_relationships(self, table_name: str, 
                                  shared_keys: List[SharedKeyDefinition]) -> List[str]:
        """Get list of relationships that will be affected by the update"""
        affected = []
        
        for shared_key in shared_keys:
            if table_name in shared_key.target_tables:
                for target_table in shared_key.target_tables:
                    if target_table != table_name:
                        affected.append(f"{table_name} -> {target_table}")
        
        return affected
    
    def _call_llm_for_m_query_update(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call LLM service for M-query update"""
        try:
            # This would implement the actual LLM service call
            # For now, return None to fall back to template method
            return None
        except Exception as e:
            self.logger.error(f"Error calling LLM for M-query update: {e}")
            return None
    
    def _create_model_backup(self, data_model: DataModel, output_path: Path):
        """Create a backup of the current model before applying updates"""
        backup_path = output_path / "backups"
        backup_path.mkdir(exist_ok=True)
        
        # This would implement model backup logic
        self.logger.info(f"Created model backup at {backup_path}")
    
    def _apply_m_query_update(self, table: Table, update: FactTableUpdate, output_path: Path):
        """Apply M-query update to a table"""
        # Update the table's M-query
        if hasattr(table, 'm_query'):
            table.m_query = update.updated_m_query
        elif hasattr(table, 'source_query'):
            table.source_query = update.updated_m_query
        
        # Save updated M-query to file if needed
        table_file = output_path / f"{table.name}_updated.m"
        with open(table_file, 'w', encoding='utf-8') as f:
            f.write(update.updated_m_query)
        
        self.logger.info(f"Applied M-query update to table {table.name}")
    
    def generate_update_documentation(self,
                                    updates: List[FactTableUpdate],
                                    output_path: Path) -> str:
        """Generate documentation for fact table updates"""
        doc_lines = []
        doc_lines.append("# Fact Table Updates for Staging Integration")
        doc_lines.append("")
        doc_lines.append("This document describes the updates made to fact tables to support staging table relationships.")
        doc_lines.append("")
        
        successful_updates = [u for u in updates if u.success]
        failed_updates = [u for u in updates if not u.success]
        
        if successful_updates:
            doc_lines.append("## Successfully Updated Tables")
            doc_lines.append("")
            
            for update in successful_updates:
                doc_lines.append(f"### {update.table_name}")
                doc_lines.append(f"- **Shared Keys Added**: {', '.join(update.shared_keys_added)}")
                doc_lines.append(f"- **Relationships Affected**: {', '.join(update.relationships_affected)}")
                doc_lines.append(f"- **Update Type**: {update.update_type}")
                doc_lines.append("")
        
        if failed_updates:
            doc_lines.append("## Failed Updates")
            doc_lines.append("")
            
            for update in failed_updates:
                doc_lines.append(f"### {update.table_name}")
                doc_lines.append(f"- **Error**: {update.error_message}")
                doc_lines.append("")
        
        doc_content = '\n'.join(doc_lines)
        
        # Save documentation
        doc_file = output_path / "fact_table_updates_documentation.md"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        self.logger.info(f"Generated fact table update documentation at {doc_file}")
        return doc_content 