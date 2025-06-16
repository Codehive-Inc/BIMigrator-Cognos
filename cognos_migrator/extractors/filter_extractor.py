"""
Filter Extractor for Cognos XML report specifications.

This module provides functionality to extract filter information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class FilterExtractor(BaseExtractor):
    """Extractor for filters from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the filter extractor with optional logger."""
        super().__init__(logger)
    
    def extract_filters(self, root, ns=None):
        """Extract filters from report specification XML"""
        filters = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find the queries section
            queries_section = self.find_element(root, "queries", ns)
                
            if queries_section is None:
                self.logger.warning("No queries section found in report specification")
                return filters
                
            # Process each query
            query_elements = self.findall_elements(queries_section, "query", ns)
                
            for query_idx, query_elem in enumerate(query_elements):
                query_name = query_elem.get("name", f"Query {query_idx}")
                
                # Extract detail filters
                detail_filters_elem = self.find_element(query_elem, "detailFilters", ns)
                    
                if detail_filters_elem is not None:
                    filter_elements = self.findall_elements(detail_filters_elem, "detailFilter", ns)
                        
                    for i, filter_elem in enumerate(filter_elements):
                        filter_data = {
                            "id": filter_elem.get("id", f"detail_filter_{query_idx}_{i}"),
                            "type": "detail",
                            "queryName": query_name,
                        }
                        
                        # Extract filter expression
                        expr_elem = self.find_element(filter_elem, "filterExpression", ns)
                            
                        if expr_elem is not None:
                            filter_data["expression"] = self.get_element_text(expr_elem)
                        
                        filters.append(filter_data)
                
                # Extract summary filters
                summary_filters_elem = self.find_element(query_elem, "summaryFilters", ns)
                    
                if summary_filters_elem is not None:
                    filter_elements = self.findall_elements(summary_filters_elem, "summaryFilter", ns)
                        
                    for i, filter_elem in enumerate(filter_elements):
                        filter_data = {
                            "id": filter_elem.get("id", f"summary_filter_{query_idx}_{i}"),
                            "type": "summary",
                            "queryName": query_name,
                        }
                        
                        # Extract filter expression
                        expr_elem = self.find_element(filter_elem, "filterExpression", ns)
                            
                        if expr_elem is not None:
                            filter_data["expression"] = self.get_element_text(expr_elem)
                        
                        filters.append(filter_data)
        except Exception as e:
            self.logger.warning(f"Error extracting filters: {e}")
        
        return filters
