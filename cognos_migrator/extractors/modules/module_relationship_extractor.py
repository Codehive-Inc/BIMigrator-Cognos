"""
Module relationship extractor for Cognos to Power BI migration
"""

import os
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
        
        # Save to JSON files - only save one consolidated file
        self.save_to_json(relationships, output_dir, "cognos_relationships.json")
        self.save_to_json({"relationships": powerbi_relationships}, output_dir, "relationships.json")
        
        # Remove the redundant relationship.json file if it exists
        relationship_file = os.path.join(output_dir, "relationship.json")
        if os.path.exists(relationship_file):
            try:
                os.remove(relationship_file)
                self.logger.info(f"Removed redundant relationship.json file: {relationship_file}")
            except Exception as e:
                self.logger.warning(f"Failed to remove redundant file {relationship_file}: {str(e)}")
        
        return {
            'cognos_relationships': relationships,
            'powerbi_relationships': powerbi_relationships
        }
    
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
        import uuid
        powerbi_relationships = []
        datasource_id = ""  # Default empty datasource ID
        datasource_caption = ""  # Default empty datasource caption
        
        for rel in relationships:
            left_maxcard = rel.get("left", {}).get("maxcard", "")
            right_maxcard = rel.get("right", {}).get("maxcard", "")
            
            # Determine from/to tables and columns based on cardinality rules
            if left_maxcard == "many" and right_maxcard == "one":
                # ManyToOne: from is left, to is right
                from_table = rel.get("left", {}).get("ref", "")
                to_table = rel.get("right", {}).get("ref", "")
                cardinality = "many"
                cross_filter_behavior = "OneDirection"
                # For links, we'll use the first link if there are multiple (composite keys)
                if rel.get("links", []):
                    from_column = rel.get("links", [])[0].get("leftRef", "")
                    to_column = rel.get("links", [])[0].get("rightRef", "")
                else:
                    continue  # Skip if no links
                    
            elif left_maxcard == "one" and right_maxcard == "many":
                # ManyToOne: from is right, to is left (swap direction)
                from_table = rel.get("right", {}).get("ref", "")
                to_table = rel.get("left", {}).get("ref", "")
                cardinality = "many"
                cross_filter_behavior = "OneDirection"
                # For links, we'll use the first link if there are multiple (composite keys)
                if rel.get("links", []):
                    from_column = rel.get("links", [])[0].get("rightRef", "")
                    to_column = rel.get("links", [])[0].get("leftRef", "")
                else:
                    continue  # Skip if no links
                    
            elif left_maxcard == "one" and right_maxcard == "one":
                # OneToOne: from is left, to is right
                from_table = rel.get("left", {}).get("ref", "")
                to_table = rel.get("right", {}).get("ref", "")
                cardinality = "one"
                cross_filter_behavior = "BothDirections"
                # For links, we'll use the first link if there are multiple (composite keys)
                if rel.get("links", []):
                    from_column = rel.get("links", [])[0].get("leftRef", "")
                    to_column = rel.get("links", [])[0].get("rightRef", "")
                else:
                    continue  # Skip if no links
                    
            elif left_maxcard == "many" and right_maxcard == "many":
                # ManyToMany: from is left, to is right
                from_table = rel.get("left", {}).get("ref", "")
                to_table = rel.get("right", {}).get("ref", "")
                cardinality = "many"
                cross_filter_behavior = "BothDirections"
                # For links, we'll use the first link if there are multiple (composite keys)
                if rel.get("links", []):
                    from_column = rel.get("links", [])[0].get("leftRef", "")
                    to_column = rel.get("links", [])[0].get("rightRef", "")
                else:
                    continue  # Skip if no links
            else:
                # Default case if cardinality is not specified
                from_table = rel.get("left", {}).get("ref", "")
                to_table = rel.get("right", {}).get("ref", "")
                cardinality = "one"
                cross_filter_behavior = "OneDirection"
                # For links, we'll use the first link if there are multiple (composite keys)
                if rel.get("links", []):
                    from_column = rel.get("links", [])[0].get("leftRef", "")
                    to_column = rel.get("links", [])[0].get("rightRef", "")
                else:
                    continue  # Skip if no links
            
            # Create Power BI relationship
            powerbi_rel = {
                "id": str(uuid.uuid4()),
                "from_table": from_table,
                "from_column": from_column,
                "to_table": to_table,
                "to_column": to_column,
                "cardinality": cardinality,
                "cross_filter_behavior": cross_filter_behavior,
                "is_active": True,
                "from_datasource_id": datasource_id,
                "from_datasource_caption": datasource_caption,
                "to_datasource_id": datasource_id,
                "to_datasource_caption": datasource_caption
            }
            
            powerbi_relationships.append(powerbi_rel)
        
        # Check for multiple relationships between the same tables and mark all but one as inactive
        table_pairs = {}
        for rel in powerbi_relationships:
            pair_key = f"{rel['from_table']}:{rel['to_table']}"
            if pair_key in table_pairs:
                table_pairs[pair_key].append(rel)
            else:
                table_pairs[pair_key] = [rel]
        
        # For each pair of tables with multiple relationships, keep only the first one active
        for pair, rels in table_pairs.items():
            if len(rels) > 1:
                for i in range(1, len(rels)):
                    rels[i]["is_active"] = False
                    self.logger.warning(f"Multiple relationships found between {pair}, marking relationship {rels[i]['id']} as inactive")
        
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
