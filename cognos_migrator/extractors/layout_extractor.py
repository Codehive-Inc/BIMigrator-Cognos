"""
Layout Extractor for Cognos XML report specifications.

This module provides functionality to extract layout information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class LayoutExtractor(BaseExtractor):
    """Extractor for layout information from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the layout extractor with optional logger."""
        super().__init__(logger)
    
    def extract_layout(self, root, ns=None):
        """Extract layout information from report specification XML"""
        layout = {
            "pages": [],
            "containers": [],
            "visualizations": []
        }
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find layout section
            layout_section = self.find_element(root, "layout", ns)
            if layout_section is None:
                # Try to find layout in other locations
                layouts_section = self.find_element(root, "layouts", ns)
                if layouts_section is not None:
                    layout_section = self.find_element(layouts_section, "layout", ns)
                    
            if layout_section is None:
                self.logger.warning("No layout section found in report specification")
                return layout
            
            # Extract page information
            pages = []
            page_elements = self.findall_elements(layout_section, "page", ns)
                
            for page_elem in page_elements:
                page = {
                    "id": page_elem.get("id", ""),
                    "name": page_elem.get("name", ""),
                    "style": page_elem.get("style", "")
                }
                pages.append(page)
            layout["pages"] = pages
            
            # Extract container information (blocks, tables, etc.)
            containers = []
            block_elements = self.findall_elements(layout_section, "block", ns)
            table_elements = self.findall_elements(layout_section, "table", ns)
                
            for container_elem in block_elements + table_elements:
                container = {
                    "id": container_elem.get("id", ""),
                    "type": container_elem.tag.split('}')[-1] if '}' in container_elem.tag else container_elem.tag,
                    "style": container_elem.get("style", "")
                }
                containers.append(container)
            layout["containers"] = containers
            
            # Extract visualization information (charts, crosstabs, lists, etc.)
            visualizations = []
            chart_elements = self.findall_elements(layout_section, "chart", ns)
            crosstab_elements = self.findall_elements(layout_section, "crosstab", ns)
            list_elements = self.findall_elements(layout_section, "list", ns)
            
            for viz_elem in chart_elements + crosstab_elements + list_elements:
                viz = {
                    "id": viz_elem.get("id", ""),
                    "type": viz_elem.tag.split('}')[-1] if '}' in viz_elem.tag else viz_elem.tag,
                    "style": viz_elem.get("style", "")
                }
                visualizations.append(viz)
            layout["visualizations"] = visualizations
            
        except Exception as e:
            self.logger.warning(f"Error extracting layout: {e}")
        
        return layout
