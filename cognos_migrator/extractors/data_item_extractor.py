"""
Data Item Extractor for Cognos XML report specifications.

This module provides functionality to extract data item information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class DataItemExtractor(BaseExtractor):
    """Extractor for data items from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the data item extractor with optional logger."""
        super().__init__(logger)
    
    def extract_data_items(self, root, ns=None):
        """Extract data items from report specification XML"""
        data_items = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find all data items in the report
            data_item_elements = self.findall_elements(root, "dataItem", ns)
                
            for item_elem in data_item_elements:
                data_item = {
                    "name": item_elem.get("name", ""),
                    "id": item_elem.get("id", ""),
                    "aggregate": item_elem.get("aggregate", "none"),
                }
                
                # Extract expression
                expr_elem = self.find_element(item_elem, "expression", ns)
                if expr_elem is not None:
                    data_item["expression"] = self.get_element_text(expr_elem)
                
                # Extract XML attributes for data type and usage
                xml_attrs = self.find_element(item_elem, "XMLAttributes", ns)
                    
                if xml_attrs is not None:
                    data_type_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataType']", ns)
                    data_usage_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataUsage']", ns)
                    format_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_formatProperties']", ns)
                        
                    if data_type_attr is not None:
                        data_item["dataType"] = data_type_attr.get("value", "")
                    if data_usage_attr is not None:
                        data_item["dataUsage"] = data_usage_attr.get("value", "")
                    if format_attr is not None:
                        data_item["formatProperties"] = format_attr.get("value", "")
                
                # Try to determine the source query by looking at the context
                # Since ElementTree doesn't have parent navigation, we'll use a different approach
                # Look for data items within query selections
                query_elements = self.findall_elements(root, "query", ns)
                    
                for query_elem in query_elements:
                    query_name = query_elem.get("name", "")
                    
                    # Look for this data item in the query's selection
                    selection_elem = self.find_element(query_elem, "selection", ns)
                        
                    if selection_elem is not None:
                        query_data_items = self.findall_elements(
                            selection_elem, 
                            f"dataItem[@name='{data_item['name']}']", 
                            ns
                        )
                            
                        if query_data_items:
                            data_item["queryName"] = query_name
                            break
                
                data_items.append(data_item)
                
        except Exception as e:
            self.logger.warning(f"Error extracting data items: {e}")
            
        return data_items
