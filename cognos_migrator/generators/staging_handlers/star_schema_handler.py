"""
Star Schema handler for creating dimension tables in a star schema design.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
import uuid

from cognos_migrator.models import DataModel, Table, Column, Relationship, DataType
from .base_handler import BaseHandler


class StarSchemaHandler(BaseHandler):
    """Handler for star schema approach with dimension tables."""
    
    def process_import_mode(self, data_model: DataModel) -> DataModel:
        """
        Process data model using star schema approach with import mode.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with star schema dimension tables
        """
        self.logger.info("Processing data model with 'star_schema' + 'import' approach")
        
        # Use SQL relationships if available, otherwise fall back to basic relationships
        if self.sql_relationships:
            self.logger.info(f"Using {len(self.sql_relationships)} SQL relationships for staging tables")
            complex_relationships = self._identify_complex_sql_relationships(self.sql_relationships)
        else:
            self.logger.info("Using basic data model relationships for staging tables")
            complex_relationships = self._identify_complex_relationships(data_model.relationships)
        
        self.logger.info(f"Identified {len(complex_relationships)} complex relationships that need staging tables")
        
        if not complex_relationships:
            self.logger.info("No complex relationships found, returning original model")
            return data_model
        
        # Group relationships by tables they connect
        if self.sql_relationships:
            relationship_groups = self._group_sql_relationships_by_tables(complex_relationships)
        else:
            relationship_groups = self._group_relationships_by_tables(complex_relationships)
        
        self.logger.info(f"Grouped complex relationships into {len(relationship_groups)} groups")
        
        # Create dimension tables from relationship groups
        new_tables = list(data_model.tables)  # Start with all original tables
        dimension_tables = []
        dimension_table_map = {}  # Maps original table pairs to dimension tables
        
        for group_key, relationships in relationship_groups.items():
            # Extract table names from the group key
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            
            # Find the actual table objects
            from_table = next((t for t in data_model.tables if t.name == from_table_name), None)
            to_table = next((t for t in data_model.tables if t.name == to_table_name), None)
            
            if not from_table or not to_table:
                self.logger.warning(f"Could not find tables for relationship group: {group_key}")
                continue
            
            if self.sql_relationships:
                # Extract columns from SQL relationships
                columns_info = self._extract_columns_for_staging_table_from_sql(
                    relationships, from_table, to_table)
                
                # Create dimension table with composite key
                dimension_table = self._create_dimension_table_with_composite_key(
                    from_table_name, to_table_name, columns_info, relationships)
            else:
                # Use basic relationship approach
                dimension_table = self._create_staging_table(from_table, to_table, relationships)
            
            dimension_tables.append(dimension_table)
            dimension_table_map[group_key] = dimension_table
            new_tables.append(dimension_table)
        
        # Create relationships between dimension tables and fact tables
        new_relationships = []
        
        if self.sql_relationships:
            for group_key, relationships in relationship_groups.items():
                table_names = group_key.split(':')
                if len(table_names) != 2:
                    continue
                    
                from_table_name, to_table_name = table_names
                dimension_table = dimension_table_map[group_key]
                
                # Create relationships from dimension table to fact tables
                self._create_dimension_relationships_from_sql(
                    relationships, dimension_table.name, from_table_name, to_table_name, new_relationships)
        else:
            # Create relationships using basic approach
            for group_key, relationships in relationship_groups.items():
                dimension_table = dimension_table_map[group_key]
                for rel in relationships:
                    # Create relationship from staging table to original tables
                    new_rel = Relationship(
                        from_table=dimension_table.name,
                        from_column=rel.from_column,
                        to_table=rel.to_table,
                        to_column=rel.to_column,
                        id=f"stg_{rel.id}",
                        from_cardinality='one',
                        to_cardinality='many'
                    )
                    new_relationships.append(new_rel)
        
        # Filter relationships to keep only dimension relationships
        if self.sql_relationships:
            new_relationships = self._filter_dimension_relationships(new_relationships, relationship_groups)
        
        # Add composite keys to fact tables
        if self.sql_relationships:
            new_data_model = DataModel(
                name=data_model.name,
                tables=new_tables,
                relationships=new_relationships,
                compatibility_level=data_model.compatibility_level
            )
            new_data_model = self._add_composite_keys_to_fact_tables(new_data_model, relationship_groups)
        else:
            new_data_model = DataModel(
                name=data_model.name,
                tables=new_tables,
                relationships=new_relationships,
                compatibility_level=data_model.compatibility_level
            )
        
        # Copy any additional attributes from the original data model
        for attr, value in vars(data_model).items():
            if attr not in ['name', 'tables', 'relationships', 'compatibility_level']:
                setattr(new_data_model, attr, value)
        
        # Save dimension tables as JSON files
        if self.extracted_dir:
            self._save_updated_tables_as_json(dimension_tables, new_data_model.tables, self.extracted_dir)
        
        self.logger.info(f"Processed data model with 'star_schema' approach: "
                         f"{len(new_data_model.tables)} tables, {len(new_data_model.relationships)} relationships")
        return new_data_model
    
    def process_direct_query_mode(self, data_model: DataModel) -> DataModel:
        """
        Process data model using star schema approach with DirectQuery mode.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with star schema dimension tables for DirectQuery
        """
        self.logger.info("Processing data model with 'star_schema' + 'direct_query' approach")
        
        # TODO: Future M-query optimizations for DirectQuery mode:
        # - Dimension table M-queries should use native SQL JOINs where possible
        # - Composite key creation should be done in SQL (CONCAT or ||)
        # - Table.Combine operations should be replaced with UNION ALL SQL
        # - Minimize Power Query transformations to maintain query folding
        # - Consider using SQL CTEs for complex dimension table logic
        # - Optimize relationship handling for better query performance
        
        # Use the same logic as import mode but with directQuery partition mode
        processed_model = self.process_import_mode(data_model)
        
        # Update all generated dimension tables to use directQuery partition mode
        for table in processed_model.tables:
            if table.name.startswith(self.naming_prefix):
                table.partition_mode = "directQuery"
                self.logger.info(f"Set dimension table {table.name} to directQuery mode")
        
        return processed_model
    
    def _group_sql_relationships_by_tables(self, sql_relationships: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group SQL relationships by the tables they connect."""
        relationship_groups = {}
        
        for rel in sql_relationships:
            table_a = rel.get('table_a_one_side', '')
            table_b = rel.get('table_b_many_side', '')
            
            # Create a consistent key for the table pair
            group_key = f"{table_a}:{table_b}"
            
            if group_key not in relationship_groups:
                relationship_groups[group_key] = []
            relationship_groups[group_key].append(rel)
        
        return relationship_groups
    
    def _group_relationships_by_tables(self, relationships: List[Relationship]) -> Dict[str, List[Relationship]]:
        """Group relationships by the tables they connect."""
        relationship_groups = {}
        
        for rel in relationships:
            # Create a consistent key for the table pair
            group_key = f"{rel.from_table}:{rel.to_table}"
            
            if group_key not in relationship_groups:
                relationship_groups[group_key] = []
            relationship_groups[group_key].append(rel)
        
        return relationship_groups
    
    def _extract_columns_for_staging_table_from_sql(self, sql_relationships: List[Dict[str, Any]], 
                                                   from_table: Table, to_table: Table) -> List[Dict[str, str]]:
        """Extract all columns involved in SQL relationships for dimension tables."""
        columns_info = []
        unique_columns = set()
        
        for rel in sql_relationships:
            keys_a = rel.get('keys_a', [])
            keys_b = rel.get('keys_b', [])
            
            # Add all keys from both sides
            for key in keys_a + keys_b:
                if key not in unique_columns:
                    columns_info.append({
                        'name': key,
                        'source_column': key,
                        'data_type': 'string'  # Default to string, could be enhanced
                    })
                    unique_columns.add(key)
        
        self.logger.info(f"Extracted {len(columns_info)} columns from SQL relationships: {list(unique_columns)}")
        return columns_info
    
    def _create_dimension_table_with_composite_key(self, from_table_name: str, to_table_name: str, 
                                                  columns_info: List[Dict[str, str]], 
                                                  relationships: List[Dict[str, Any]]) -> Table:
        """Create a dimension table with composite key from SQL relationships."""
        # Generate dimension table name
        dimension_table_name = f"{self.naming_prefix}{from_table_name}_{to_table_name}"
        
        # Create columns for the dimension table
        columns = []
        for col_info in columns_info:
            column = Column(
                name=col_info['name'],
                data_type=DataType.STRING,  # Default to string
                source_column=col_info['source_column'],
                summarize_by="none"
            )
            columns.append(column)
        
        # Generate composite key name and add composite key column
        composite_key_name = self._get_composite_key_name(relationships)
        composite_key_column = Column(
            name=composite_key_name,
            data_type=DataType.STRING,
            source_column=composite_key_name,
            summarize_by="none",
            is_key=True
        )
        columns.append(composite_key_column)
        
        # Generate M-query for the dimension table
        m_query = self._generate_dimension_table_m_query(
            dimension_table_name, from_table_name, to_table_name, 
            columns_info, relationships)
        
        # Create the dimension table
        dimension_table = Table(
            name=dimension_table_name,
            columns=columns,
            m_query=m_query,
            source_query=m_query
        )
        
        self.logger.info(f"Created dimension table {dimension_table_name} with {len(columns)} columns plus composite key")
        return dimension_table
    
    def _get_composite_key_name(self, relationships: List[Any]) -> str:
        """Generate a composite key name from relationships."""
        if isinstance(relationships[0], dict):
            # SQL relationships
            unique_keys = set()
            for rel in relationships:
                keys_a = rel.get('keys_a', [])
                keys_b = rel.get('keys_b', [])
                unique_keys.update(keys_a)
                unique_keys.update(keys_b)
            return "_".join(sorted(unique_keys)) + "_Key"
        else:
            # Basic relationships
            unique_keys = set()
            for rel in relationships:
                if rel.from_column:
                    unique_keys.update(rel.from_column.split(','))
                if rel.to_column:
                    unique_keys.update(rel.to_column.split(','))
            return "_".join(sorted(unique_keys)) + "_Key"
    
    def _generate_dimension_table_m_query(self, dimension_table_name: str, from_table_name: str, 
                                         to_table_name: str, columns_info: List[Dict[str, str]], 
                                         relationships: List[Dict[str, Any]]) -> str:
        """Generate M-query for dimension table."""
        # Extract column names
        column_names = [col['name'] for col in columns_info]
        columns_str = '", "'.join(column_names)
        
        # Generate composite key logic
        composite_key_logic = self._get_composite_key_logic(relationships)
        composite_key_name = self._get_composite_key_name(relationships)
        
        # Build M-query with proper indentation for TMDL
        m_query = f"""let
                // Get data from {from_table_name}
                Data_From_{from_table_name} = Table.SelectColumns({from_table_name}, {{"{columns_str}"}}),
                // Get data from {to_table_name}
                Data_From_{to_table_name} = Table.SelectColumns({to_table_name}, {{"{columns_str}"}}),
                // Combine data from all source tables
                CombinedData = Table.Combine({{Data_From_{from_table_name}, Data_From_{to_table_name}}}),
                // Get unique combinations of dimension keys
                UniqueRows = Table.Distinct(CombinedData, {{"{columns_str}"}}),
                // Create composite key for relationships
                AddCompositeKey = Table.AddColumn(UniqueRows, "{composite_key_name}", {composite_key_logic}, type text),
                // Filter out rows with null or empty composite keys
                FilteredRows = Table.SelectRows(AddCompositeKey, each [{composite_key_name}] <> null and [{composite_key_name}] <> "")
            in
                FilteredRows"""
        
        return m_query
    
    def _get_composite_key_logic(self, relationships: List[Any]) -> str:
        """Generate the M-query logic for creating composite keys."""
        if isinstance(relationships[0], dict):
            # SQL relationships
            unique_keys = set()
            for rel in relationships:
                keys_a = rel.get('keys_a', [])
                keys_b = rel.get('keys_b', [])
                unique_keys.update(keys_a)
                unique_keys.update(keys_b)
            
            unique_keys = sorted(unique_keys)
            if len(unique_keys) == 1:
                return f"each [{unique_keys[0]}]"
            elif len(unique_keys) > 1:
                key_parts = [f"[{key}]" for key in unique_keys]
                return f"each Text.Combine({{{', '.join(key_parts)}}}, \"|\")"
        
        # Fallback for basic relationships
        return 'each "CompositeKey"'
    
    def _create_dimension_relationships_from_sql(self, sql_relationships: List[Dict[str, Any]], 
                                              dimension_table_name: str, from_table_name: str, 
                                              to_table_name: str, new_relationships: List[Relationship]) -> None:
        """Create dimension relationships from SQL relationship data using composite keys."""
        # Get the composite key name for this dimension table
        composite_key_name = self._get_composite_key_name(sql_relationships)
        
        # Create one relationship per fact table, not per key column
        related_tables = set()
        for rel in sql_relationships:
            table_a = rel.get('table_a_one_side', '')
            table_b = rel.get('table_b_many_side', '')
            
            if table_a in [from_table_name, to_table_name]:
                related_tables.add(table_a)
            if table_b in [from_table_name, to_table_name]:
                related_tables.add(table_b)
        
        # Create one relationship per related table using the composite key
        for i, table_name in enumerate(related_tables):
            rel_id_base = f"{dimension_table_name}_to_{table_name}".replace(' ', '_')
            
            new_rel = Relationship(
                from_table=dimension_table_name,
                from_column=composite_key_name,
                to_table=table_name,
                to_column=composite_key_name,
                id=rel_id_base,
                from_cardinality='one',
                to_cardinality='many'
            )
            new_relationships.append(new_rel)
            
            self.logger.info(f"Created dimension relationship: {dimension_table_name}[{composite_key_name}] -> "
                             f"{table_name}[{composite_key_name}]")
    
    def _create_staging_table(self, from_table: Table, to_table: Table, 
                             relationships: List[Relationship]) -> Table:
        """Create a staging table from basic relationships (fallback method)."""
        # This is a simplified version for basic relationships
        staging_table_name = f"{self.naming_prefix}{from_table.name}_{to_table.name}"
        
        # Extract unique columns from relationships
        unique_columns = set()
        for rel in relationships:
            if rel.from_column:
                unique_columns.update(rel.from_column.split(','))
            if rel.to_column:
                unique_columns.update(rel.to_column.split(','))
        
        # Create columns for staging table
        columns = []
        for col_name in unique_columns:
            col_name = col_name.strip()
            column = Column(
                name=col_name,
                data_type=DataType.STRING,
                source_column=col_name,
                summarize_by="none"
            )
            columns.append(column)
        
        return Table(
            name=staging_table_name,
            columns=columns
        )
    
    def _add_composite_keys_to_fact_tables(self, data_model: DataModel, 
                                          relationship_groups: Dict[str, List[Dict[str, Any]]]) -> DataModel:
        """Add composite key columns to fact tables and update their M-queries."""
        self.logger.info("Adding composite keys to fact tables")
        
        # Collect all composite keys needed for each table
        table_composite_keys = {}  # table_name -> [(composite_key_name, composite_key_logic, relationships)]
        
        for group_key, relationships in relationship_groups.items():
            table_names = group_key.split(':')
            if len(table_names) != 2:
                continue
                
            from_table_name, to_table_name = table_names
            composite_key_name = self._get_composite_key_name(relationships)
            composite_key_logic = self._get_composite_key_logic(relationships)
            
            # Add to both tables involved in the relationship
            for table_name in [from_table_name, to_table_name]:
                if table_name not in table_composite_keys:
                    table_composite_keys[table_name] = []
                
                # Check if this composite key already exists for this table
                existing_keys = [key[0] for key in table_composite_keys[table_name]]
                if composite_key_name not in existing_keys:
                    table_composite_keys[table_name].append((composite_key_name, composite_key_logic, relationships))
        
        # Update tables with composite keys
        updated_tables = []
        for table in data_model.tables:
            if table.name in table_composite_keys and not table.name.startswith(self.naming_prefix):
                # This is a fact table that needs composite keys
                composite_keys = table_composite_keys[table.name]
                updated_table = self._add_composite_keys_to_table(table, composite_keys)
                updated_tables.append(updated_table)
                self.logger.info(f"Added {len(composite_keys)} composite keys to fact table {table.name}")
            else:
                # Keep table as is
                updated_tables.append(table)
        
        # Create updated data model
        updated_data_model = DataModel(
            name=data_model.name,
            tables=updated_tables,
            relationships=data_model.relationships,
            compatibility_level=data_model.compatibility_level
        )
        
        # Copy any additional attributes
        for attr, value in vars(data_model).items():
            if attr not in ['name', 'tables', 'relationships', 'compatibility_level']:
                setattr(updated_data_model, attr, value)
        
        return updated_data_model
    
    def _add_composite_keys_to_table(self, table: Table, composite_keys: List[Tuple[str, str, List]]) -> Table:
        """Add composite key columns to a table and update its M-query."""
        # Get existing column names to avoid duplicates
        existing_column_names = {col.name for col in table.columns}
        
        # Create new columns list with composite keys
        new_columns = list(table.columns)
        
        for composite_key_name, composite_key_logic, relationships in composite_keys:
            if composite_key_name in existing_column_names:
                continue  # Skip if column already exists
                
            composite_key_column = Column(
                name=composite_key_name,
                data_type=DataType.STRING,
                source_column=composite_key_name,
                summarize_by="none",
                is_key=True
            )
            new_columns.append(composite_key_column)
        
        # Get the original M-query
        baseline_m_query = table.m_query or table.source_query
        if not baseline_m_query and self.extracted_dir:
            baseline_m_query = self._get_original_m_query_from_json(table.name)
        
        # Update M-query with composite key generation
        updated_m_query = baseline_m_query
        if baseline_m_query and composite_keys:
            updated_m_query = self._update_fact_table_m_query(baseline_m_query, composite_keys)
        
        if updated_m_query != baseline_m_query:
            self.logger.info(f"Successfully updated M-query for {table.name} with {len(composite_keys)} composite keys")
        else:
            self.logger.warning(f"M-query for {table.name} was not updated (returned same as baseline)")
        
        # Create updated table with explicit attribute copying
        # This approach is more maintainable than using exclusion lists
        updated_table = Table(
            name=table.name,
            columns=new_columns,
            measures=table.measures,
            source_query=updated_m_query,  # Keep source_query for compatibility
            m_query=updated_m_query,  # Also set m_query so package migration uses it
            partition_mode=table.partition_mode,
            description=table.description,
            annotations=table.annotations,
            metadata=table.metadata
        )
        
        return updated_table
    
    def _update_fact_table_m_query(self, original_m_query: str, composite_keys: List[Tuple[str, str, List]]) -> str:
        """Update a fact table's M-query to include composite key generation."""
        lines = original_m_query.split('\n')
        
        # Find the 'in' clause and the step before it
        in_line_index = -1
        final_step = "Source"  # Default fallback
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "in":
                in_line_index = i
                # Find the final step name from the line before 'in'
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    # Extract step name from a line like: #"Step Name" = Table.Something(...)
                    if '=' in prev_line:
                        final_step = prev_line.split('=')[0].strip()
                    else:
                        # Fallback: use the line after 'in' (the result reference)
                        if i + 1 < len(lines):
                            final_step = lines[i + 1].strip()
                break
        
        if in_line_index == -1:
            # No 'in' clause found, append to the end
            new_lines = lines[:]
        else:
            # Insert before the 'in' clause
            new_lines = lines[:in_line_index]
            
            # Ensure the last step before 'in' has a comma (since it won't be the final step anymore)
            if new_lines and not new_lines[-1].strip().endswith(',') and '=' in new_lines[-1]:
                # Add comma to the last step that will no longer be final
                new_lines[-1] = new_lines[-1] + ','

        
        # Add composite key generation steps
        for i, (composite_key_name, composite_key_logic, relationships) in enumerate(composite_keys):
            step_name = f"AddCompositeKey_{i + 1}"
            if i == 0:
                previous_step = final_step
            else:
                previous_step = f"AddCompositeKey_{i}"
            
            new_lines.append(f"                    // Add composite key: {composite_key_name}")
            new_lines.append(f"                    {step_name} = Table.AddColumn({previous_step}, \"{composite_key_name}\", {composite_key_logic}, type text),")
        
        # Update the final step name
        if composite_keys:
            final_step = f"AddCompositeKey_{len(composite_keys)}"
            # Remove trailing comma from last step
            if new_lines and new_lines[-1].endswith(','):
                new_lines[-1] = new_lines[-1][:-1]
        
        # Add the 'in' clause back
        new_lines.append("                in")
        new_lines.append(f"                    {final_step}")
        
        return '\n'.join(new_lines)
    
    def _save_updated_tables_as_json(self, dimension_tables: List[Table], all_tables: List[Table], 
                                    extracted_dir: Path) -> None:
        """Save dimension tables as JSON files."""
        for table in dimension_tables:
            self._save_table_as_json(table, extracted_dir)
            self.logger.info(f"Saved dimension table JSON: {table.name}")
    
    def _filter_dimension_relationships(self, new_relationships: List[Relationship], 
                                       relationship_groups: Dict[str, List[Dict[str, Any]]]) -> List[Relationship]:
        """Filter relationships to keep only dimension relationships."""
        # Filter to keep only dimension relationships (those starting with naming prefix)
        dimension_relationships = [
            rel for rel in new_relationships 
            if rel.id.startswith(self.naming_prefix)
        ]
        
        # Log what we're keeping
        self.logger.info(f"Keeping {len(dimension_relationships)} dimension relationships")
        for rel in dimension_relationships:
            self.logger.info(f"Keeping dimension relationship: {rel.from_table}[{rel.from_column}] -> {rel.to_table}[{rel.to_column}]")
        
        return dimension_relationships
