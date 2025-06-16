"""
CPF Metadata Enhancer for Power BI projects.

This module provides functionality to enhance Power BI projects with metadata from Cognos CPF files.
"""

import logging
from typing import Dict, Any, Optional, List
from cognos_migrator.models import PowerBIProject, Relationship


class CPFMetadataEnhancer:
    """Enhancer for Power BI projects using Cognos CPF metadata."""
    
    def __init__(self, cpf_extractor, logger=None):
        """Initialize the CPF metadata enhancer with a CPF extractor and optional logger."""
        self.cpf_extractor = cpf_extractor
        self.logger = logger or logging.getLogger(__name__)
    
    def enhance_project(self, powerbi_project: PowerBIProject) -> None:
        """Enhance Power BI project with metadata from CPF file"""
        try:
            if not self.cpf_extractor or not powerbi_project or not powerbi_project.data_model:
                return
            
            self.logger.info("Enhancing Power BI project with CPF metadata")
            
            # Enhance tables with CPF metadata
            for table in powerbi_project.data_model.tables:
                table_name = table.name
                
                # Get table schema from CPF metadata
                table_schema = self.cpf_extractor.get_table_schema(table_name)
                if not table_schema or not table_schema.get('columns'):
                    continue
                
                self.logger.info(f"Enhancing table: {table_name} with CPF metadata")
                
                # Update column metadata
                for col in table.columns:
                    # Find matching column in CPF metadata
                    for cpf_col in table_schema.get('columns', []):
                        if cpf_col.get('name') == col.name:
                            # Update column data type if available
                            if cpf_col.get('dataType'):
                                col.data_type = self._map_cpf_data_type(cpf_col.get('dataType'))
                            
                            # Update column description if available
                            if cpf_col.get('expression'):
                                col.description = f"Expression: {cpf_col.get('expression')}"
                            
                            break
                
                # Add relationships if available
                for rel in table_schema.get('relationships', []):
                    target_table = self._find_table_by_name(powerbi_project.data_model, 
                                                      self.cpf_extractor.get_query_subject_by_id(rel.get('targetQuerySubjectId', '')).get('name', ''))
                    
                    if target_table:
                        # Get column names
                        source_cols = [self.cpf_extractor.get_column_name_by_id(col_id) for col_id in rel.get('sourceColumns', [])]
                        target_cols = [self.cpf_extractor.get_column_name_by_id(col_id) for col_id in rel.get('targetColumns', [])]
                        
                        # Create relationship if columns are found
                        if source_cols and target_cols:
                            new_rel = Relationship(
                                from_table=table.name,
                                from_column=source_cols[0],  # Use first column for now
                                to_table=target_table.name,
                                to_column=target_cols[0],    # Use first column for now
                                cardinality=self._map_cpf_cardinality(rel.get('cardinality', ''))
                            )
                            
                            # Add relationship if it doesn't already exist
                            if not self._relationship_exists(powerbi_project.data_model, new_rel):
                                powerbi_project.data_model.relationships.append(new_rel)
                                self.logger.info(f"Added relationship: {table.name}.{source_cols[0]} -> {target_table.name}.{target_cols[0]}")
            
            # Add M-query context to the project for later use
            powerbi_project.metadata['cpf_metadata'] = True
            
            self.logger.info("Successfully enhanced Power BI project with CPF metadata")
            
        except Exception as e:
            self.logger.error(f"Error enhancing with CPF metadata: {e}")
    
    def _map_cpf_data_type(self, cpf_type: str) -> str:
        """Map CPF data type to Power BI data type"""
        type_mapping = {
            'xs:string': 'Text',
            'xs:integer': 'Int64',
            'xs:decimal': 'Decimal',
            'xs:double': 'Double',
            'xs:float': 'Double',
            'xs:boolean': 'Boolean',
            'xs:date': 'Date',
            'xs:time': 'Time',
            'xs:dateTime': 'DateTime',
            'xs:duration': 'Duration'
        }
        
        return type_mapping.get(cpf_type, 'Text')  # Default to Text if unknown
    
    def _map_cpf_cardinality(self, cardinality: str) -> str:
        """Map CPF cardinality to Power BI cardinality"""
        cardinality_mapping = {
            'oneToOne': 'OneToOne',
            'oneToMany': 'OneToMany',
            'manyToOne': 'ManyToOne',
            'manyToMany': 'ManyToMany'
        }
        
        return cardinality_mapping.get(cardinality, 'ManyToOne')  # Default to ManyToOne if unknown
    
    def _find_table_by_name(self, data_model, table_name: str):
        """Find a table in the data model by name"""
        for table in data_model.tables:
            if table.name == table_name:
                return table
        return None
    
    def _relationship_exists(self, data_model, new_rel: Relationship) -> bool:
        """Check if a relationship already exists in the data model"""
        for rel in data_model.relationships:
            if (rel.from_table == new_rel.from_table and 
                rel.from_column == new_rel.from_column and 
                rel.to_table == new_rel.to_table and 
                rel.to_column == new_rel.to_column):
                return True
        return False
