"""
CPF Parser Module for extracting metadata from Cognos Framework Manager .cpf files.

This module provides functionality to parse and extract metadata from Cognos Framework Manager
.cpf files, which are XML-based files containing data model definitions.
"""

import os
import logging
import xml.etree.ElementTree as ET
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class CPFParser:
    """Parser for Cognos Framework Manager .cpf files"""
    
    def __init__(self, cpf_file_path: str):
        """
        Initialize the CPF Parser with a .cpf file path
        
        Args:
            cpf_file_path: Path to the .cpf file
        """
        self.cpf_file_path = cpf_file_path
        self.logger = logging.getLogger(__name__)
        self.namespaces = {
            'fm': 'http://developer.cognos.com/schemas/fmx/1/',
            'xs': 'http://www.w3.org/2001/XMLSchema',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        self.tree = None
        self.root = None
        
    def parse(self) -> bool:
        """
        Parse the CPF file
        
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            self.logger.info(f"Parsing CPF file: {self.cpf_file_path}")
            self.tree = ET.parse(self.cpf_file_path)
            self.root = self.tree.getroot()
            return True
        except Exception as e:
            self.logger.error(f"Error parsing CPF file: {e}")
            return False
    
    def extract_data_sources(self) -> List[Dict[str, Any]]:
        """
        Extract data source information from the CPF file
        
        Returns:
            List of dictionaries containing data source information
        """
        data_sources = []
        
        try:
            # Find all data source nodes in the CPF file
            ds_nodes = self.root.findall('.//fm:dataSource', self.namespaces)
            
            for ds_node in ds_nodes:
                ds_info = {
                    'id': ds_node.get('id', ''),
                    'name': ds_node.get('name', ''),
                    'type': ds_node.get('type', ''),
                    'connectionString': '',
                    'catalog': '',
                    'schema': '',
                    'parameters': {}
                }
                
                # Extract connection string
                conn_string = ds_node.find('.//fm:connectionString', self.namespaces)
                if conn_string is not None:
                    ds_info['connectionString'] = conn_string.text
                
                # Extract catalog
                catalog = ds_node.find('.//fm:catalog', self.namespaces)
                if catalog is not None:
                    ds_info['catalog'] = catalog.text
                
                # Extract schema
                schema = ds_node.find('.//fm:schema', self.namespaces)
                if schema is not None:
                    ds_info['schema'] = schema.text
                
                # Extract parameters
                params = ds_node.findall('.//fm:parameter', self.namespaces)
                for param in params:
                    name = param.get('name', '')
                    value = param.get('value', '')
                    ds_info['parameters'][name] = value
                
                data_sources.append(ds_info)
            
            self.logger.info(f"Extracted {len(data_sources)} data sources from CPF file")
            return data_sources
        
        except Exception as e:
            self.logger.error(f"Error extracting data sources: {e}")
            return []
    
    def extract_query_subjects(self) -> List[Dict[str, Any]]:
        """
        Extract query subjects (tables) from the CPF file
        
        Returns:
            List of dictionaries containing query subject information
        """
        query_subjects = []
        
        try:
            # Find all query subject nodes in the CPF file
            qs_nodes = self.root.findall('.//fm:querySubject', self.namespaces)
            
            for qs_node in qs_nodes:
                qs_info = {
                    'id': qs_node.get('id', ''),
                    'name': qs_node.get('name', ''),
                    'type': qs_node.get('type', ''),
                    'dataSourceId': '',
                    'tableName': '',
                    'columns': [],
                    'relationships': []
                }
                
                # Extract data source ID
                ds_ref = qs_node.find('.//fm:dataSourceRef', self.namespaces)
                if ds_ref is not None:
                    qs_info['dataSourceId'] = ds_ref.get('refId', '')
                
                # Extract table name
                table = qs_node.find('.//fm:table', self.namespaces)
                if table is not None:
                    qs_info['tableName'] = table.text
                
                # Extract columns
                columns = qs_node.findall('.//fm:queryItem', self.namespaces)
                for col in columns:
                    col_info = {
                        'id': col.get('id', ''),
                        'name': col.get('name', ''),
                        'dataType': col.get('dataType', ''),
                        'nullable': col.get('nullable', 'true') == 'true',
                        'expression': ''
                    }
                    
                    # Extract expression
                    expr = col.find('.//fm:expression', self.namespaces)
                    if expr is not None:
                        col_info['expression'] = expr.text
                    
                    qs_info['columns'].append(col_info)
                
                query_subjects.append(qs_info)
            
            # Extract relationships separately
            self._extract_relationships(query_subjects)
            
            self.logger.info(f"Extracted {len(query_subjects)} query subjects from CPF file")
            return query_subjects
        
        except Exception as e:
            self.logger.error(f"Error extracting query subjects: {e}")
            return []
    
    def _extract_relationships(self, query_subjects: List[Dict[str, Any]]) -> None:
        """
        Extract relationships between query subjects
        
        Args:
            query_subjects: List of query subjects to update with relationship information
        """
        try:
            # Find all relationship nodes in the CPF file
            rel_nodes = self.root.findall('.//fm:relationship', self.namespaces)
            
            # Create a lookup dictionary for query subjects by ID
            qs_lookup = {qs['id']: qs for qs in query_subjects}
            
            for rel_node in rel_nodes:
                rel_info = {
                    'id': rel_node.get('id', ''),
                    'name': rel_node.get('name', ''),
                    'cardinality': rel_node.get('cardinality', ''),
                    'sourceQuerySubjectId': '',
                    'targetQuerySubjectId': '',
                    'sourceColumns': [],
                    'targetColumns': []
                }
                
                # Extract source query subject
                source_ref = rel_node.find('.//fm:source/fm:querySubjectRef', self.namespaces)
                if source_ref is not None:
                    rel_info['sourceQuerySubjectId'] = source_ref.get('refId', '')
                
                # Extract target query subject
                target_ref = rel_node.find('.//fm:target/fm:querySubjectRef', self.namespaces)
                if target_ref is not None:
                    rel_info['targetQuerySubjectId'] = target_ref.get('refId', '')
                
                # Extract source columns
                source_cols = rel_node.findall('.//fm:source/fm:queryItemRef', self.namespaces)
                for col_ref in source_cols:
                    rel_info['sourceColumns'].append(col_ref.get('refId', ''))
                
                # Extract target columns
                target_cols = rel_node.findall('.//fm:target/fm:queryItemRef', self.namespaces)
                for col_ref in target_cols:
                    rel_info['targetColumns'].append(col_ref.get('refId', ''))
                
                # Add relationship to the appropriate query subject
                if rel_info['sourceQuerySubjectId'] in qs_lookup:
                    qs_lookup[rel_info['sourceQuerySubjectId']]['relationships'].append(rel_info)
        
        except Exception as e:
            self.logger.error(f"Error extracting relationships: {e}")
    
    def extract_namespaces(self) -> List[Dict[str, Any]]:
        """
        Extract namespace information from the CPF file
        
        Returns:
            List of dictionaries containing namespace information
        """
        namespaces = []
        
        try:
            # Find all namespace nodes in the CPF file
            ns_nodes = self.root.findall('.//fm:namespace', self.namespaces)
            
            for ns_node in ns_nodes:
                ns_info = {
                    'id': ns_node.get('id', ''),
                    'name': ns_node.get('name', ''),
                    'querySubjects': []
                }
                
                # Extract query subject references
                qs_refs = ns_node.findall('.//fm:querySubjectRef', self.namespaces)
                for qs_ref in qs_refs:
                    ns_info['querySubjects'].append(qs_ref.get('refId', ''))
                
                namespaces.append(ns_info)
            
            self.logger.info(f"Extracted {len(namespaces)} namespaces from CPF file")
            return namespaces
        
        except Exception as e:
            self.logger.error(f"Error extracting namespaces: {e}")
            return []
    
    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all metadata from the CPF file
        
        Returns:
            Dictionary containing all extracted metadata
        """
        if not self.root:
            if not self.parse():
                return {}
        
        metadata = {
            'dataSources': self.extract_data_sources(),
            'querySubjects': self.extract_query_subjects(),
            'namespaces': self.extract_namespaces(),
            'metadata': {
                'fileName': os.path.basename(self.cpf_file_path),
                'filePath': self.cpf_file_path,
                'extractionTime': str(datetime.datetime.now())
            }
        }
        
        return metadata
    
    def save_metadata_to_json(self, output_path: str) -> bool:
        """
        Save extracted metadata to a JSON file
        
        Args:
            output_path: Path to save the JSON file
        
        Returns:
            bool: True if saving was successful, False otherwise
        """
        try:
            metadata = self.extract_all()
            
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Saved CPF metadata to: {output_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving CPF metadata to JSON: {e}")
            return False


# Add missing import
import datetime
