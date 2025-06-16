"""
Module relationship extractor for Cognos to Power BI migration
"""

import logging
import json
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

from .module_extractor import ModuleExtractor


class ModuleRelationshipExtractor(ModuleExtractor):
    """Extracts relationships between tables from a Cognos module"""
    
    def __init__(self, logger=None):
        """Initialize the module relationship extractor
        
        Args:
            logger: Optional logger instance
        """
        super().__init__(logger)
        
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract relationships and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted relationships
        """
        # Extract relationships
        relationships = self.extract_relationships(module_content)
        powerbi_relationships = self.convert_to_powerbi_relationships(relationships)
        
        # Combine into a single structure
        relationship_data = {
            'cognos_relationships': relationships,
            'powerbi_relationships': powerbi_relationships
        }
        
        # Save to JSON files
        self.save_to_json(relationships, output_dir, "cognos_relationships.json")
        self.save_to_json(powerbi_relationships, output_dir, "powerbi_relationships.json")
        self.save_to_json(relationship_data, output_dir, "relationship_data.json")
        
        return relationship_data
    
    def extract_relationships(self, module_content: str) -> List[Dict[str, Any]]:
        """Extract relationships from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            List of relationships with their properties
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            relationships = []
            
            # Extract relationships
            if "relationship" in module_data:
                for rel in module_data.get("relationship", []):
                    relationship = {
                        "identifier": rel.get("identifier", ""),
                        "label": rel.get("label", ""),
                        "description": rel.get("description", ""),
                        "idForExpression": rel.get("idForExpression", ""),
                        "joinFilterType": rel.get("joinFilterType", ""),
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
                        "links": [],
                        "properties": {}
                    }
                    
                    # Extract join links
                    for link in rel.get("link", []):
                        join_link = {
                            "leftRef": link.get("leftRef", ""),
                            "rightRef": link.get("rightRef", ""),
                            "comparisonOperator": link.get("comparisonOperator", "")
                        }
                        relationship["links"].append(join_link)
                    
                    # Extract properties
                    for prop in rel.get("property", []):
                        relationship["properties"][prop.get("name", "")] = prop.get("value", "")
                    
                    # Extract property overrides
                    if "propertyOverride" in rel:
                        relationship["propertyOverrides"] = rel.get("propertyOverride", [])
                    
                    relationships.append(relationship)
            
            return relationships
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error extracting relationships: {e}")
            return []
    
    def convert_to_powerbi_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Cognos relationships to Power BI relationship format
        
        Args:
            relationships: List of Cognos relationships
            
        Returns:
            List of relationships in Power BI format
        """
        powerbi_relationships = []
        
        for rel in relationships:
            # Map cardinality
            cardinality = self._map_cardinality(
                rel.get("left", {}).get("mincard", ""),
                rel.get("left", {}).get("maxcard", ""),
                rel.get("right", {}).get("mincard", ""),
                rel.get("right", {}).get("maxcard", "")
            )
            
            # Create Power BI relationship for each link
            for link in rel.get("links", []):
                powerbi_rel = {
                    "name": rel.get("identifier", ""),
                    "fromTable": rel.get("left", {}).get("ref", ""),
                    "fromColumn": link.get("leftRef", ""),
                    "toTable": rel.get("right", {}).get("ref", ""),
                    "toColumn": link.get("rightRef", ""),
                    "cardinality": cardinality,
                    "crossFilteringBehavior": "automatic"
                }
                
                # Check if this is a system-discovered relationship
                if rel.get("properties", {}).get("SystemDiscovered") == "true":
                    powerbi_rel["isSystemGenerated"] = True
                
                powerbi_relationships.append(powerbi_rel)
        
        return powerbi_relationships
    
    def _map_cardinality(self, left_min: str, left_max: str, right_min: str, right_max: str) -> str:
        """Map Cognos cardinality to Power BI cardinality
        
        Args:
            left_min: Left side minimum cardinality
            left_max: Left side maximum cardinality
            right_min: Right side minimum cardinality
            right_max: Right side maximum cardinality
            
        Returns:
            Power BI cardinality type
        """
        # Power BI cardinality types: OneToOne, OneToMany, ManyToOne, ManyToMany
        
        if left_max == "one" and right_max == "one":
            return "OneToOne"
        elif left_max == "many" and right_max == "one":
            return "ManyToOne"
        elif left_max == "one" and right_max == "many":
            return "OneToMany"
        elif left_max == "many" and right_max == "many":
            return "ManyToMany"
        else:
            # Default to OneToMany if can't determine
            self.logger.warning(f"Could not determine cardinality for {left_min}/{left_max} to {right_min}/{right_max}, defaulting to OneToMany")
            return "OneToMany"
