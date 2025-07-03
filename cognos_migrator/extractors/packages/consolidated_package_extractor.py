"""
Consolidated package extractor for Cognos Framework Manager packages.

This module provides functionality to coordinate the extraction of data from
Cognos Framework Manager (FM) package files using specialized extractors.
"""

import logging
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from cognos_migrator.models import DataType, DataModel, Table, Column, Relationship

from .base_package_extractor import BasePackageExtractor
from .package_structure_extractor import PackageStructureExtractor
from .package_query_subject_extractor import PackageQuerySubjectExtractor
from .package_relationship_extractor import PackageRelationshipExtractor
from .package_calculation_extractor import PackageCalculationExtractor
from .package_filter_extractor import PackageFilterExtractor


class ConsolidatedPackageExtractor:
    """Coordinates the extraction of data from Cognos Framework Manager packages"""
    
    def __init__(self, logger=None):
        """Initialize the consolidated package extractor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize specialized extractors
        self.structure_extractor = PackageStructureExtractor(logger)
        self.query_subject_extractor = PackageQuerySubjectExtractor(logger)
        self.relationship_extractor = PackageRelationshipExtractor(logger)
        self.calculation_extractor = PackageCalculationExtractor(logger)
        self.filter_extractor = PackageFilterExtractor(logger)
    
    def extract_package(self, package_file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """Extract package information from an FM package file
        
        Args:
            package_file_path: Path to the FM package file
            output_dir: Optional directory to save extracted data as JSON files
            
        Returns:
            Dictionary containing extracted package information
        """
        try:
            self.logger.info(f"Extracting package from {package_file_path}")
            
            # Create output directory if specified
            if output_dir:
                # Use the output_dir directly without adding "extracted" subfolder
                # This avoids creating a nested extracted folder
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = None
            
            # Parse the XML file once
            tree = ET.parse(package_file_path)
            root = tree.getroot()
            
            # Extract package structure
            if output_path:
                structure = self.structure_extractor.extract_and_save(package_file_path, output_path)
            else:
                structure = self.structure_extractor.extract_package_structure(root)
            
            # Extract query subjects
            if output_path:
                query_subjects_result = self.query_subject_extractor.extract_and_save(package_file_path, output_path)
                query_subjects = query_subjects_result.get("query_subjects", [])
            else:
                query_subjects = self.query_subject_extractor.extract_query_subjects(root)
            
            # Extract relationships
            if output_path:
                relationships_result = self.relationship_extractor.extract_and_save(package_file_path, output_path)
                relationships = relationships_result.get("relationships", [])
            else:
                relationships = self.relationship_extractor.extract_relationships(root)
            
            # Extract calculations
            if output_path:
                calculations_result = self.calculation_extractor.extract_and_save(package_file_path, output_path)
                calculations = calculations_result.get("calculations", {})
            else:
                calculations = self.calculation_extractor.extract_calculations(root)
                
            # Extract filters
            if output_path:
                filters_result = self.filter_extractor.extract_and_save(package_file_path, output_path)
                filters = filters_result.get("filters", {})
            else:
                filters = self.filter_extractor.extract_filters(root)
            
            # Combine into package info
            package_info = {
                'name': structure.get('name', 'Unknown Package'),
                'query_subjects': query_subjects,
                'relationships': relationships,
                'calculations': calculations,
                'filters': filters,
                'structure': structure
            }
            
            # Save consolidated package info if output directory is specified
            if output_path:
                self.structure_extractor.save_to_json(package_info, output_path, "package_info.json")
            
            self.logger.info(f"Successfully extracted package: {package_info['name']}")
            return package_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract package from {package_file_path}: {e}")
            raise
    
    def convert_to_data_model(self, package_info: Dict[str, Any]) -> DataModel:
        """Convert extracted package information to a data model
        
        Args:
            package_info: Dictionary containing extracted package information
            
        Returns:
            DataModel instance
        """
        try:
            self.logger.info(f"Converting package {package_info['name']} to data model")
            
            # Create tables list for data model
            tables = []
            
            # Create data model with empty tables list (will add tables later)
            data_model = DataModel(name=package_info['name'], tables=tables)
            
            # Convert query subjects to tables
            for qs in package_info['query_subjects']:
                # Create columns list for table
                columns = []
                
                # Add columns
                for item in qs.get('items', []):
                    # Get the data type from the item
                    cognos_type = item.get('datatype', 'string')
                    
                    # Map Cognos data type to Power BI data type
                    if cognos_type.lower() in ['int32', 'int64']:
                        data_type = DataType.INTEGER
                    elif cognos_type.lower() in ['float', 'double']:
                        data_type = DataType.DOUBLE
                    elif cognos_type.lower() == 'boolean':
                        data_type = DataType.BOOLEAN
                    elif cognos_type.lower() in ['date', 'time', 'timestamp']:
                        data_type = DataType.DATE
                    else:
                        data_type = DataType.STRING
                        
                    column = Column(
                        name=item['name'],
                        data_type=data_type,
                        source_column=item.get('source_column', item['name'])  # Use source_column if available, otherwise use name
                    )
                    columns.append(column)
                
                # Create table with columns
                table = Table(name=qs['name'], columns=columns)
                
                # Add table to data model's tables list
                data_model.tables.append(table)
            
            # Convert relationships
            for rel in package_info['relationships']:
                # Get left and right query subjects
                left_qs = rel.get('left', {}).get('query_subject')
                right_qs = rel.get('right', {}).get('query_subject')
                
                if not left_qs or not right_qs:
                    continue
                
                # Extract simple table names from fully qualified names
                # This doesn't change the Relationship class, just helps us identify tables
                left_table = left_qs.split('.')[-1].strip('[]')
                right_table = right_qs.split('.')[-1].strip('[]')
                
                # Get determinants (join columns)
                determinants = rel.get('determinants', [])
                
                left_col = None
                right_col = None
                
                # If determinants exist, use them
                if determinants:
                    det = determinants[0]  # Use the first determinant
                    left_col = det.get('left_column')
                    right_col = det.get('right_column')
                
                # If no determinants or columns, try to infer from table names
                if not left_col or not right_col:
                    self.logger.warning(f"No explicit join columns found for relationship between {left_table} and {right_table}. Attempting to infer.")
                    
                    # Find tables in the data model by their simple names
                    left_table_obj = None
                    right_table_obj = None
                    
                    for table in data_model.tables:
                        if table.name == left_table:
                            left_table_obj = table
                        if table.name == right_table:
                            right_table_obj = table
                    
                    # If tables exist, try to find matching columns
                    if left_table_obj and right_table_obj:
                        left_cols = [c.name for c in left_table_obj.columns]
                        right_cols = [c.name for c in right_table_obj.columns]
                        
                        # Find common column names
                        common_cols = set(left_cols).intersection(set(right_cols))
                        
                        # Try to find ID columns
                        id_patterns = [f"{left_table}ID", f"{left_table}_ID", "ID"]
                        for pattern in id_patterns:
                            matching_cols = [col for col in common_cols if pattern.lower() in col.lower()]
                            if matching_cols:
                                left_col = right_col = matching_cols[0]
                                self.logger.info(f"Inferred join column {left_col} for relationship between {left_table} and {right_table}")
                                break
                        
                        # If still no match, use any common column as a last resort
                        if not left_col and common_cols:
                            left_col = right_col = list(common_cols)[0]
                            self.logger.info(f"Using common column {left_col} for relationship between {left_table} and {right_table}")
                
                # Skip if we still couldn't determine columns
                if not left_col or not right_col:
                    self.logger.warning(f"Skipping relationship between {left_table} and {right_table}: couldn't determine join columns")
                    continue
                
                # Create relationship with a name - using the simple table names instead of fully qualified names
                relationship = Relationship(
                    name=f"Relationship_{left_table}_{right_table}",
                    from_table=left_table,  # Use simple table name
                    from_column=left_col,
                    to_table=right_table,    # Use simple table name
                    to_column=right_col
                )
                
                # Add relationship to data model's relationships list
                data_model.relationships.append(relationship)
            
            self.logger.info(f"Successfully converted package to data model with {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
            return data_model
            
        except Exception as e:
            self.logger.error(f"Failed to convert package to data model: {e}")
            raise
