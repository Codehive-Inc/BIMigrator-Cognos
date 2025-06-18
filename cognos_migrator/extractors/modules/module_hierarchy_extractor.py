"""
Module hierarchy extractor for Cognos to Power BI migration
"""

import logging
import json
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
import os

from .module_extractor import ModuleExtractor


class ModuleHierarchyExtractor(ModuleExtractor):
    """Extracts hierarchies and drill groups from a Cognos module"""
    
    def __init__(self, logger=None):
        """Initialize the module hierarchy extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
    
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract hierarchies and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted hierarchies
        """
        # Extract hierarchies
        hierarchies = self.extract_hierarchies(module_content)
        powerbi_hierarchies = self.convert_to_powerbi_hierarchies(hierarchies)
        
        # Combine into a single structure
        hierarchy_data = {
            'cognos_hierarchies': hierarchies,
            'powerbi_hierarchies': powerbi_hierarchies
        }
        
        # Save to JSON files
        self.save_to_json(hierarchies, output_dir, "cognos_hierarchies.json")
        self.save_to_json(powerbi_hierarchies, output_dir, "powerbi_hierarchies.json")
        self.save_to_json(hierarchy_data, output_dir, "hierarchy_data.json")
        
        return hierarchy_data
    
    def extract_hierarchies(self, module_content: str) -> List[Dict[str, Any]]:
        """Extract hierarchies (drill groups) from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            List of hierarchies with their properties
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            hierarchies = []
            
            # Extract drill groups (hierarchies)
            if "drillGroup" in module_data:
                for drill_group in module_data.get("drillGroup", []):
                    hierarchy = {
                        "identifier": drill_group.get("identifier", ""),
                        "label": drill_group.get("label", ""),
                        "idForExpression": drill_group.get("idForExpression", ""),
                        "levels": [],
                        "properties": {}
                    }
                    
                    # Extract hierarchy levels
                    for segment in drill_group.get("segment", []):
                        level = {
                            "ref": segment.get("ref", ""),
                            "identifier": segment.get("identifier", ""),
                            "label": segment.get("label", "")
                        }
                        hierarchy["levels"].append(level)
                    
                    # Extract property overrides
                    if "propertyOverride" in drill_group:
                        hierarchy["propertyOverrides"] = drill_group.get("propertyOverride", [])
                    
                    hierarchies.append(hierarchy)
            
            return hierarchies
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error extracting hierarchies: {e}")
            return []
    
    def convert_to_powerbi_hierarchies(self, hierarchies: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert Cognos hierarchies to Power BI hierarchy format
        
        Args:
            hierarchies: List of Cognos hierarchies
            
        Returns:
            Dictionary mapping table names to lists of hierarchies in Power BI format
        """
        powerbi_hierarchies = {}
        
        for hierarchy in hierarchies:
            # Group levels by table
            table_levels = {}
            
            for level in hierarchy.get("levels", []):
                # Extract table name from ref (format: "Table.Column")
                ref = level.get("ref", "")
                if "." in ref:
                    table_name = ref.split(".")[0]
                    column_name = ref.split(".")[1]
                    
                    if table_name not in table_levels:
                        table_levels[table_name] = []
                    
                    table_levels[table_name].append({
                        "column": column_name,
                        "name": level.get("label", level.get("identifier", column_name))
                    })
            
            # Create hierarchies for each table
            for table_name, levels in table_levels.items():
                if table_name not in powerbi_hierarchies:
                    powerbi_hierarchies[table_name] = []
                
                powerbi_hierarchy = {
                    "name": hierarchy.get("label", hierarchy.get("identifier", "")),
                    "levels": levels
                }
                
                powerbi_hierarchies[table_name].append(powerbi_hierarchy)
        
        return powerbi_hierarchies
    
    def extract_metadata_tree(self, module_content: str) -> List[Dict[str, Any]]:
        """Extract metadata tree view from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            List of metadata tree items
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            tree_items = []
            
            # Extract metadata tree view
            if "metadataTreeView" in module_data:
                for tree_view in module_data.get("metadataTreeView", []):
                    if "folderItem" in tree_view:
                        for folder_item in tree_view.get("folderItem", []):
                            tree_items.append({
                                "ref": folder_item.get("ref", "")
                            })
            
            return tree_items
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error extracting metadata tree: {e}")
            return []
