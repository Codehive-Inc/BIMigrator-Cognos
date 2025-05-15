"""Generator for relationship TMDL files."""
from pathlib import Path
from typing import Optional, List

from bimigrator.config.data_classes import PowerBiRelationship
from .base_template_generator import BaseTemplateGenerator


class RelationshipTemplateGenerator(BaseTemplateGenerator):
    """Generator for relationship TMDL files."""

    def generate_relationships(self, relationships: List[PowerBiRelationship], output_dir: Optional[Path] = None) -> \
            List[Path]:
        """Generate a single relationships TMDL file containing all relationships.
        
        Args:
            relationships: List of PowerBiRelationship instances
            output_dir: Optional output directory override
            
        Returns:
            List containing the path to the generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Create context for all relationships
        relationship_contexts = []
        for relationship in relationships:
            # Generate a unique ID for the relationship based on tables and columns
            relationship_id = f"{relationship.from_table}_{relationship.from_column}_to_{relationship.to_table}_{relationship.to_column}"

            # Create context with ID
            context = {**relationship.__dict__, 'id': relationship_id}

            # Map cardinality values from PowerBI format to TMDL format
            cardinality_map = {
                'oneToOne': 'one_to_one',
                'oneToMany': 'one_to_many',
                'manyToOne': 'many_to_one',
                'manyToMany': 'many_to_many'
            }
            context['cardinality'] = cardinality_map.get(relationship.cardinality, relationship.cardinality)

            # Map cross filter behavior values from PowerBI format to TMDL format
            cross_filter_map = {
                'oneWay': 'one',
                'bothDirections': 'both',
                'automatic': 'both'  # Default to both for automatic
            }
            context['cross_filter_behavior'] = cross_filter_map.get(relationship.cross_filter_behavior, 'both')

            relationship_contexts.append(context)

        # Generate a single file with all relationships
        file_path = self.generate_file('relationship', {'relationships': relationship_contexts})
        return [file_path]
