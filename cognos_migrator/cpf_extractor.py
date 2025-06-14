"""
CPF Extractor Module for integrating Framework Manager metadata into the migration process.

This module provides functionality to extract and use metadata from Cognos Framework Manager
.cpf files during the Power BI migration process.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from cognos_migrator.cpf_parser import CPFParser

class CPFExtractor:
    """
    Extracts and processes metadata from Cognos Framework Manager .cpf files
    to enhance the migration process.
    """
    
    def __init__(self, cpf_file_path: Optional[str] = None):
        """
        Initialize the CPF Extractor
        
        Args:
            cpf_file_path: Optional path to a .cpf file
        """
        self.cpf_file_path = cpf_file_path
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.parser = None
        
        if cpf_file_path:
            self.load_cpf(cpf_file_path)
    
    def load_cpf(self, cpf_file_path: str) -> bool:
        """
        Load and parse a CPF file
        
        Args:
            cpf_file_path: Path to the .cpf file
            
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            self.cpf_file_path = cpf_file_path
            self.parser = CPFParser(cpf_file_path)
            
            if self.parser.parse():
                self.metadata = self.parser.extract_all()
                self.logger.info(f"Successfully loaded CPF metadata from: {cpf_file_path}")
                return True
            else:
                self.logger.error(f"Failed to parse CPF file: {cpf_file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading CPF file: {e}")
            return False
    
    def get_data_source_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get data source information by name
        
        Args:
            name: Name of the data source
            
        Returns:
            Dictionary containing data source information or empty dict if not found
        """
        if not self.metadata or 'dataSources' not in self.metadata:
            return {}
        
        for ds in self.metadata['dataSources']:
            if ds.get('name') == name:
                return ds
        
        return {}
    
    def get_query_subject_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get query subject information by name
        
        Args:
            name: Name of the query subject
            
        Returns:
            Dictionary containing query subject information or empty dict if not found
        """
        if not self.metadata or 'querySubjects' not in self.metadata:
            return {}
        
        for qs in self.metadata['querySubjects']:
            if qs.get('name') == name:
                return qs
        
        return {}
    
    def get_related_query_subjects(self, query_subject_id: str) -> List[Dict[str, Any]]:
        """
        Get query subjects related to the specified query subject
        
        Args:
            query_subject_id: ID of the query subject
            
        Returns:
            List of dictionaries containing related query subject information
        """
        related_subjects = []
        
        if not self.metadata or 'querySubjects' not in self.metadata:
            return related_subjects
        
        # Find the query subject by ID
        query_subject = None
        for qs in self.metadata['querySubjects']:
            if qs.get('id') == query_subject_id:
                query_subject = qs
                break
        
        if not query_subject:
            return related_subjects
        
        # Get related query subjects through relationships
        for rel in query_subject.get('relationships', []):
            target_id = rel.get('targetQuerySubjectId')
            if target_id:
                for qs in self.metadata['querySubjects']:
                    if qs.get('id') == target_id:
                        related_subjects.append(qs)
        
        return related_subjects
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get schema information for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table schema information
        """
        schema = {
            'name': table_name,
            'columns': [],
            'relationships': []
        }
        
        # First try to find by query subject name
        query_subject = self.get_query_subject_by_name(table_name)
        
        # If not found, try to find by table name
        if not query_subject and 'querySubjects' in self.metadata:
            for qs in self.metadata['querySubjects']:
                if qs.get('tableName') == table_name:
                    query_subject = qs
                    break
        
        if query_subject:
            schema['name'] = query_subject.get('name', table_name)
            schema['columns'] = query_subject.get('columns', [])
            schema['relationships'] = query_subject.get('relationships', [])
        
        return schema
    
    def generate_m_query_context(self, table_name: str) -> Dict[str, Any]:
        """
        Generate context information for M-query generation based on CPF metadata
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing context information for M-query generation
        """
        context = {
            'table_name': table_name,
            'columns': [],
            'data_source': {},
            'relationships': []
        }
        
        table_schema = self.get_table_schema(table_name)
        
        # Add column information
        for col in table_schema.get('columns', []):
            context['columns'].append({
                'name': col.get('name', ''),
                'dataType': col.get('dataType', ''),
                'nullable': col.get('nullable', True),
                'expression': col.get('expression', '')
            })
        
        # Add relationship information
        for rel in table_schema.get('relationships', []):
            context['relationships'].append({
                'targetTable': self.get_query_subject_by_id(rel.get('targetQuerySubjectId', '')).get('name', ''),
                'cardinality': rel.get('cardinality', ''),
                'sourceColumns': [self.get_column_name_by_id(col_id) for col_id in rel.get('sourceColumns', [])],
                'targetColumns': [self.get_column_name_by_id(col_id) for col_id in rel.get('targetColumns', [])]
            })
        
        # Add data source information if available
        if 'dataSourceId' in table_schema:
            ds_id = table_schema.get('dataSourceId')
            if ds_id and 'dataSources' in self.metadata:
                for ds in self.metadata['dataSources']:
                    if ds.get('id') == ds_id:
                        context['data_source'] = {
                            'name': ds.get('name', ''),
                            'type': ds.get('type', ''),
                            'connectionString': ds.get('connectionString', ''),
                            'catalog': ds.get('catalog', ''),
                            'schema': ds.get('schema', '')
                        }
                        break
        
        return context
    
    def get_query_subject_by_id(self, query_subject_id: str) -> Dict[str, Any]:
        """
        Get query subject information by ID
        
        Args:
            query_subject_id: ID of the query subject
            
        Returns:
            Dictionary containing query subject information or empty dict if not found
        """
        if not self.metadata or 'querySubjects' not in self.metadata:
            return {}
        
        for qs in self.metadata['querySubjects']:
            if qs.get('id') == query_subject_id:
                return qs
        
        return {}
    
    def get_column_name_by_id(self, column_id: str) -> str:
        """
        Get column name by ID
        
        Args:
            column_id: ID of the column
            
        Returns:
            Column name or empty string if not found
        """
        if not self.metadata or 'querySubjects' not in self.metadata:
            return ''
        
        for qs in self.metadata['querySubjects']:
            for col in qs.get('columns', []):
                if col.get('id') == column_id:
                    return col.get('name', '')
        
        return ''
