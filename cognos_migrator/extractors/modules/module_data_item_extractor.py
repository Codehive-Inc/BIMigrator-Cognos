"""
Module data item extractor for Cognos to Power BI migration
"""

import logging
import json
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
import os

from .module_extractor import ModuleExtractor


class ModuleDataItemExtractor(ModuleExtractor):
    """Extracts data items and their properties from a Cognos module"""
    
    def __init__(self, logger=None):
        """Initialize the module data item extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract data items and calculated items and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted data items
        """
        # Extract data items and calculated items
        data_items = self.extract_data_items(module_content)
        calculated_items = self.extract_calculated_items(module_content)
        
        # Combine into a single structure
        all_items = {
            'data_items': data_items,
            'calculated_items': calculated_items
        }
        
        # Save to JSON files
        self.save_to_json(data_items, output_dir, "data_items.json")
        self.save_to_json(calculated_items, output_dir, "calculated_items.json")
        self.save_to_json(all_items, output_dir, "all_items.json")
        
        return all_items
    
    def extract_data_items(self, module_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract data items from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            Dictionary mapping query subject identifiers to lists of data items
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            data_items_by_subject = {}
            
            # Extract data items for each query subject
            if "querySubject" in module_data:
                for query_subject in module_data.get("querySubject", []):
                    subject_id = query_subject.get("identifier", "")
                    data_items = []
                    
                    # Extract query items
                    for item in query_subject.get("item", []):
                        if "queryItem" in item:
                            query_item = item["queryItem"]
                            data_item = {
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
                                "idForExpression": query_item.get("idForExpression", ""),
                                "powerbi_datatype": self.map_cognos_to_powerbi_datatypes(query_item.get("datatype", "")),
                                "powerbi_format": self.determine_powerbi_format(query_item)
                            }
                            
                            # Extract facet definition if available
                            if "facetDefinition" in query_item:
                                data_item["facetDefinition"] = query_item.get("facetDefinition", {})
                            
                            data_items.append(data_item)
                    
                    if subject_id:
                        data_items_by_subject[subject_id] = data_items
            
            return data_items_by_subject
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error extracting data items: {e}")
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
    
    def determine_powerbi_format(self, query_item: Dict[str, Any]) -> str:
        """Determine the appropriate Power BI format based on the query item properties
        
        Args:
            query_item: Query item dictionary
            
        Returns:
            Power BI format string
        """
        datatype = query_item.get("datatype", "").upper()
        highlevel_datatype = query_item.get("highlevelDatatype", "").lower()
        datatype_category = query_item.get("datatypeCategory", "").lower()
        
        # Handle date/time formats
        if "DATE" in datatype or highlevel_datatype == "date":
            return "dd/MM/yyyy"
        elif "TIME" in datatype and "DATE" not in datatype:
            return "HH:mm:ss"
        elif "TIMESTAMP" in datatype or "DATETIME" in datatype:
            return "dd/MM/yyyy HH:mm:ss"
        
        # Handle numeric formats
        elif "DECIMAL" in datatype or "NUMERIC" in datatype:
            # Check if it's a percentage
            if query_item.get("expression", "").lower().find("percent") >= 0:
                return "0.00%;-0.00%;0.00%"
            else:
                return "#,0.00;-#,0.00;0.00"
        elif "INT" in datatype:
            return "#,0;-#,0;0"
        elif "FLOAT" in datatype or "DOUBLE" in datatype or "REAL" in datatype:
            return "#,0.00;-#,0.00;0.00"
        
        # Handle currency
        elif query_item.get("expression", "").lower().find("price") >= 0 or \
             query_item.get("expression", "").lower().find("cost") >= 0 or \
             query_item.get("expression", "").lower().find("amount") >= 0 or \
             query_item.get("identifier", "").lower().find("price") >= 0 or \
             query_item.get("identifier", "").lower().find("cost") >= 0 or \
             query_item.get("identifier", "").lower().find("amount") >= 0:
            return "$#,0.00;-$#,0.00;$0.00"
        
        # Default format based on datatype category
        elif datatype_category == "number":
            return "#,0.00;-#,0.00;0.00"
        
        # No specific format for strings and other types
        return ""
    
    def extract_calculated_items(self, module_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract calculated items from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            Dictionary mapping query subject identifiers to lists of calculated items
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            calculated_items_by_subject = {}
            
            # Extract calculated items for each query subject
            if "querySubject" in module_data:
                for query_subject in module_data.get("querySubject", []):
                    subject_id = query_subject.get("identifier", "")
                    calculated_items = []
                    
                    # Extract query items that have expressions different from their identifiers
                    for item in query_subject.get("item", []):
                        if "queryItem" in item:
                            query_item = item["queryItem"]
                            identifier = query_item.get("identifier", "")
                            expression = query_item.get("expression", "")
                            
                            # If expression is different from identifier, it's likely a calculated item
                            if expression and expression != identifier:
                                calculated_item = {
                                    "identifier": identifier,
                                    "label": query_item.get("label", ""),
                                    "expression": expression,
                                    "datatype": query_item.get("datatype", ""),
                                    "usage": query_item.get("usage", ""),
                                    "regularAggregate": query_item.get("regularAggregate", ""),
                                    "idForExpression": query_item.get("idForExpression", "")
                                }
                                
                                calculated_items.append(calculated_item)
                    
                    if subject_id and calculated_items:
                        calculated_items_by_subject[subject_id] = calculated_items
            
            return calculated_items_by_subject
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error extracting calculated items: {e}")
            return {}
