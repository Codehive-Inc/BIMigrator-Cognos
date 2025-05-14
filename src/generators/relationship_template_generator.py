"""Generator for relationship TMDL files."""
from pathlib import Path
from typing import Dict, Any, Optional, List
from config.data_classes import PowerBiRelationship
from .base_template_generator import BaseTemplateGenerator

class RelationshipTemplateGenerator(BaseTemplateGenerator):
    """Generator for relationship TMDL files."""
    
    def __init__(self, config_path: str, input_path: str, output_dir: Path):
        """Initialize with configuration file path.
        
        Args:
            config_path: Path to YAML configuration file
            input_path: Path to input file
            output_dir: Output directory override
        """
        super().__init__(config_path, input_path, output_dir)
    
    def generate_relationships(self, relationships: List[PowerBiRelationship], output_dir: Optional[Path] = None) -> List[Path]:
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
