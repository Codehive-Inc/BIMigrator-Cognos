"""
Query Extractor for Cognos XML report specifications.

This module provides functionality to extract query information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class QueryExtractor(BaseExtractor):
    """Extractor for queries from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the query extractor with optional logger."""
        super().__init__(logger)
    
    def extract_queries(self, root, ns=None):
        """Extract queries from report specification XML"""
        queries = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find the queries section directly under the root
            queries_section = self.find_element(root, "queries", ns)
                
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return queries
                
            # Find all query elements
            query_elements = self.findall_elements(queries_section, "query", ns)
                
            for i, query_elem in enumerate(query_elements):
                query = {
                    "id": query_elem.get("id", f"query_{i}"),
                    "name": query_elem.get("name", f"Query {i}"),
                }
                
                # Find source element
                source_elem = self.find_element(query_elem, "source", ns)
                if source_elem is not None:
                    model_elem = self.find_element(source_elem, "model", ns)
                    if model_elem is not None:
                        query["source"] = "model"
                    else:
                        query["source"] = self.get_element_text(source_elem)
                        
                # Extract data items
                data_items = []
                selection_elem = self.find_element(query_elem, "selection", ns)
                    
                if selection_elem is not None:
                    item_elements = self.findall_elements(selection_elem, "dataItem", ns)
                        
                    for item in item_elements:
                        data_item = {
                            "name": item.get("name", ""),
                            "aggregate": item.get("aggregate", "none"),
                        }
                        
                        expr_elem = self.find_element(item, "expression", ns)
                        if expr_elem is not None:
                            data_item["expression"] = self.get_element_text(expr_elem)
                        
                        # Extract XML attributes for data type and usage
                        xml_attrs = self.find_element(item, "XMLAttributes", ns)
                            
                        if xml_attrs is not None:
                            data_type_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataType']", ns)
                            data_usage_attr = self.find_element(xml_attrs, "XMLAttribute[@name='RS_dataUsage']", ns)
                                
                            if data_type_attr is not None:
                                data_item["dataType"] = data_type_attr.get("value", "")
                            if data_usage_attr is not None:
                                data_item["dataUsage"] = data_usage_attr.get("value", "")
                                
                        data_items.append(data_item)
                query["data_items"] = data_items
                
                # Extract filters
                filters = []
                
                # Detail filters
                detail_filters = self.find_element(query_elem, "detailFilters", ns)
                    
                if detail_filters is not None:
                    filter_elements = self.findall_elements(detail_filters, "detailFilter", ns)
                        
                    for filter_elem in filter_elements:
                        filter_expr = self.find_element(filter_elem, "filterExpression", ns)
                            
                        if filter_expr is not None:
                            filters.append({
                                "type": "detail",
                                "expression": self.get_element_text(filter_expr)
                            })
                
                # Summary filters
                summary_filters_elem = self.find_element(query_elem, "summaryFilters", ns)
                    
                if summary_filters_elem is not None:
                    filter_elements = self.findall_elements(summary_filters_elem, "summaryFilter", ns)
                        
                    for filter_elem in filter_elements:
                        filter_expr = self.find_element(filter_elem, "filterExpression", ns)
                            
                        if filter_expr is not None:
                            filters.append({
                                "type": "summary",
                                "expression": self.get_element_text(filter_expr)
                            })
                
                query["filters"] = filters
                queries.append(query)
                
            return queries
            
        except Exception as e:
            self.logger.warning(f"Error extracting queries from XML: {e}")
            return queries
