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
            # output_dir should be the pbit directory
            self.pbit_dir = output_dir
            self.output_dir = output_dir.parent
            # extracted directory should be at the same level as pbit
            self.extracted_dir = self.output_dir / 'extracted'
            # Delete any extracted directory under pbit if it exists
            pbit_extracted = self.pbit_dir / 'extracted'
            if pbit_extracted.exists():
                import shutil
                shutil.rmtree(pbit_extracted)
        
        # Create context for all relationships
        relationship_contexts = []
        for relationship in relationships:
            # Use the UUID that's already in the PowerBiRelationship object
            context = relationship.__dict__

            # No need to map cardinality values as they should already be in the correct format
            # The TMDL format expects 'one' or 'many' for fromCardinality

            # No need to map cross filter behavior values as they should already be in the correct format
            # The TMDL format expects 'bothDirections', 'oneWay', or 'automatic'
            
            relationship_contexts.append(context)
        
        # Generate a single file with all relationships
        file_path = self.generate_file('relationship', {'relationships': relationship_contexts})
        return [file_path]
