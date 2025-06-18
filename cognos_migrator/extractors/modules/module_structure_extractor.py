"""
Module structure extractor for Cognos to Power BI migration
"""

import logging
import json
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

from .module_extractor import ModuleExtractor


class ModuleStructureExtractor(ModuleExtractor):
    """Extracts the overall structure of a Cognos module"""
    
    def __init__(self, logger=None):
        """Initialize the module structure extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
        
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract module structure and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted module structure
        """
        # Extract the module structure
        structure = self.extract_module_structure(module_content)
        
        # Save to JSON file
        self.save_to_json(structure, output_dir, "module_structure.json")
        
        return structure
    
    def extract_module_structure(self, module_content: str) -> Dict[str, Any]:
        """Extract the overall structure from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            Dictionary with extracted module structure
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            # Extract basic module information
            structure = {
                "version": module_data.get("version", ""),
                "container": module_data.get("container", ""),
                "expressionLocale": module_data.get("expressionLocale", ""),
                "lastModified": module_data.get("lastModified", ""),
                "tables": [],
                "relationships": [],
                "hierarchies": []
            }
            
            # Extract data sources
            if "use" in module_data and "useSpec" in module_data:
                data_sources = []
                for i, use_id in enumerate(module_data.get("use", [])):
                    if i < len(module_data.get("useSpec", [])):
                        use_spec = module_data["useSpec"][i]
                        data_source = {
                            "id": use_id,
                            "identifier": use_spec.get("identifier", ""),
                            "type": use_spec.get("type", ""),
                            "storeID": use_spec.get("storeID", ""),
                            "searchPath": use_spec.get("searchPath", "")
                        }
                        data_sources.append(data_source)
                
                structure["dataSources"] = data_sources
            
            # Extract query subjects (tables)
            if "querySubject" in module_data:
                tables = []
                for query_subject in module_data.get("querySubject", []):
                    table = {
                        "ref": query_subject.get("ref", []),
                        "identifier": query_subject.get("identifier", ""),
                        "label": query_subject.get("label", ""),
                        "idForExpression": query_subject.get("idForExpression", ""),
                        "columns": []
                    }
                    
                    # Extract columns (query items)
                    for item in query_subject.get("item", []):
                        if "queryItem" in item:
                            query_item = item["queryItem"]
                            column = {
                                "identifier": query_item.get("identifier", ""),
                                "label": query_item.get("label", ""),
                                "expression": query_item.get("expression", ""),
                                "datatype": query_item.get("datatype", ""),
                                "usage": query_item.get("usage", ""),
                                "hidden": query_item.get("hidden", False)
                            }
                            table["columns"].append(column)
                    
                    tables.append(table)
                
                structure["tables"] = tables
            
            # Extract relationships
            if "relationship" in module_data:
                relationships = []
                for rel in module_data.get("relationship", []):
                    relationship = {
                        "identifier": rel.get("identifier", ""),
                        "label": rel.get("label", ""),
                        "left": {
                            "ref": rel.get("left", {}).get("ref", ""),
                            "mincard": rel.get("left", {}).get("mincard", ""),
                            "maxcard": rel.get("left", {}).get("maxcard", "")
                        },
                        "right": {
                            "ref": rel.get("right", {}).get("ref", ""),
                            "mincard": rel.get("right", {}).get("mincard", ""),
                            "maxcard": rel.get("right", {}).get("maxcard", "")
                        },
                        "links": []
                    }
                    
                    # Extract join links
                    for link in rel.get("link", []):
                        join_link = {
                            "leftRef": link.get("leftRef", ""),
                            "rightRef": link.get("rightRef", ""),
                            "comparisonOperator": link.get("comparisonOperator", "")
                        }
                        relationship["links"].append(join_link)
                    
                    relationships.append(relationship)
                
                structure["relationships"] = relationships
            
            # Extract hierarchies (drill groups)
            if "drillGroup" in module_data:
                hierarchies = []
                for drill_group in module_data.get("drillGroup", []):
                    hierarchy = {
                        "identifier": drill_group.get("identifier", ""),
                        "label": drill_group.get("label", ""),
                        "levels": []
                    }
                    
                    # Extract hierarchy levels
                    for segment in drill_group.get("segment", []):
                        level = {
                            "ref": segment.get("ref", ""),
                            "identifier": segment.get("identifier", ""),
                            "label": segment.get("label", "")
                        }
                        hierarchy["levels"].append(level)
                    
                    hierarchies.append(hierarchy)
                
                structure["hierarchies"] = hierarchies
            
            return structure
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return {"error": f"Invalid JSON format: {e}"}
        except Exception as e:
            self.logger.error(f"Error extracting module structure: {e}")
            return {"error": f"Extraction error: {e}"}
