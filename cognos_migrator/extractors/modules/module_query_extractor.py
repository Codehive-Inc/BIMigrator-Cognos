"""
Module query extractor for Cognos to Power BI migration
"""

import logging
import json
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

from .module_extractor import ModuleExtractor


class ModuleQueryExtractor(ModuleExtractor):
    """Extracts query subjects and query items from a Cognos module"""
    
    def __init__(self, logger=None):
        """Initialize the module query extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
        
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract query subjects and items and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted query data
        """
        # Extract query subjects and items
        query_subjects = self.extract_query_subjects(module_content)
        query_items = self.extract_query_items(module_content)
        
        # Combine into a single structure
        query_data = {
            'query_subjects': query_subjects,
            'query_items': query_items
        }
        
        # Save to JSON files
        self.save_to_json(query_subjects, output_dir, "query_subjects.json")
        self.save_to_json(query_items, output_dir, "query_items.json")
        self.save_to_json(query_data, output_dir, "query_data.json")
        
        return query_data
    
    def extract_query_subjects(self, module_content: str) -> List[Dict[str, Any]]:
        """Extract query subjects (tables) from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            List of query subjects with their properties
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            query_subjects = []
            
            # Extract query subjects
            if "querySubject" in module_data:
                for query_subject in module_data.get("querySubject", []):
                    subject = {
                        "ref": query_subject.get("ref", []),
                        "identifier": query_subject.get("identifier", ""),
                        "label": query_subject.get("label", ""),
                        "idForExpression": query_subject.get("idForExpression", ""),
                        "properties": {}
                    }
                    
                    # Extract properties
                    for prop in query_subject.get("property", []):
                        subject["properties"][prop.get("name", "")] = prop.get("value", "")
                    
                    # Extract property overrides
                    if "propertyOverride" in query_subject:
                        subject["propertyOverrides"] = query_subject.get("propertyOverride", [])
                    
                    query_subjects.append(subject)
            
            return query_subjects
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error extracting query subjects: {e}")
            return []
    
    def extract_query_items(self, module_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract query items (columns) from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            Dictionary mapping query subject identifiers to lists of query items
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            query_items_by_subject = {}
            
            # Extract query items for each query subject
            if "querySubject" in module_data:
                for query_subject in module_data.get("querySubject", []):
                    subject_id = query_subject.get("identifier", "")
                    query_items = []
                    
                    # Extract query items
                    for item in query_subject.get("item", []):
                        if "queryItem" in item:
                            query_item = item["queryItem"]
                            column = {
                                "identifier": query_item.get("identifier", ""),
                                "label": query_item.get("label", ""),
                                "description": query_item.get("description", ""),
                                "comment": query_item.get("comment", ""),
                                "expression": query_item.get("expression", ""),
                                "datatype": query_item.get("datatype", ""),
                                "usage": query_item.get("usage", ""),
                                "hidden": query_item.get("hidden", False),
                                "nullable": query_item.get("nullable", True),
                                "regularAggregate": query_item.get("regularAggregate", ""),
                                "datatypeCategory": query_item.get("datatypeCategory", ""),
                                "highlevelDatatype": query_item.get("highlevelDatatype", ""),
                                "idForExpression": query_item.get("idForExpression", "")
                            }
                            
                            # Extract facet definition if available
                            if "facetDefinition" in query_item:
                                column["facetDefinition"] = query_item.get("facetDefinition", {})
                            
                            query_items.append(column)
                    
                    if subject_id:
                        query_items_by_subject[subject_id] = query_items
            
            return query_items_by_subject
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error extracting query items: {e}")
            return {}
    
    def map_cognos_to_powerbi_datatypes(self, cognos_datatype: str) -> str:
        """Map Cognos datatypes to Power BI datatypes
        
        Args:
            cognos_datatype: Cognos datatype string
            
        Returns:
            Equivalent Power BI datatype
        """
        datatype_mapping = {
            "BIGINT": "Int64",
            "INTEGER": "Int64",
            "INT": "Int64",
            "SMALLINT": "Int64",
            "TINYINT": "Int64",
            "DECIMAL": "Decimal",
            "NUMERIC": "Decimal",
            "FLOAT": "Double",
            "REAL": "Double",
            "DOUBLE": "Double",
            "CHAR": "String",
            "VARCHAR": "String",
            "NVARCHAR": "String",
            "NVARCHAR(MAX)": "String",
            "TEXT": "String",
            "NTEXT": "String",
            "DATE": "DateTime",
            "TIME": "DateTime",
            "TIMESTAMP": "DateTime",
            "DATETIME": "DateTime",
            "BOOLEAN": "Boolean",
            "BIT": "Boolean"
        }
        
        # Handle parameterized types like VARCHAR(50)
        base_type = cognos_datatype.split('(')[0].upper() if cognos_datatype else ""
        
        return datatype_mapping.get(cognos_datatype.upper(), 
               datatype_mapping.get(base_type, "String"))  # Default to String if no match
