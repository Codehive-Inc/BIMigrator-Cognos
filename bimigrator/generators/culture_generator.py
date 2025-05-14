"""Generator for culture TMDL files."""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from bimigrator.config.data_classes import CultureInfo
from .base_template_generator import BaseTemplateGenerator


class CultureGenerator(BaseTemplateGenerator):
    """Generator for creating culture TMDL files."""

    def generate_culture_tmdl(self, culture_info: CultureInfo, output_dir: Optional[Path] = None) -> Path:
        """Generate culture TMDL file.
        
        Args:
            culture_info: Culture configuration data
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if not isinstance(culture_info, CultureInfo):
            raise ValueError("Input must be a CultureInfo object")

        # Use the base output directory
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir  # output_dir is already base_dir/pbit from structure_generator
            self.extracted_dir = self.output_dir / 'extracted'

        try:
            # Prepare context and generate file
            context = self._prepare_context(culture_info)
            return self.generate_file('culture', context)
        except Exception as e:
            raise RuntimeError(f"Failed to generate culture TMDL: {str(e)}")

    def _prepare_context(self, culture_info: CultureInfo) -> Dict[str, Any]:
        """Generate the culture TMDL file."""
        if not culture_info.culture:
            raise ValueError("Culture info must have a culture value")

        if not culture_info.linguistic_metadata:
            raise ValueError("Culture info must have linguistic metadata")

        # Convert entities to JSON format
        entities_dict = {}
        if culture_info.linguistic_metadata and culture_info.linguistic_metadata.entities:
            for key, entity in culture_info.linguistic_metadata.entities.items():
                # Skip entities with @ in their key
                if '@' in key:
                    continue

                entity_data = {
                    "Binding": {
                        "ConceptualEntity": entity.binding.conceptual_entity if entity.binding else None
                    },
                    "State": entity.state or 'Generated',
                    "Terms": []
                }

                # Add ConceptualProperty if present
                if entity.binding and entity.binding.conceptual_property:
                    entity_data["Binding"]["ConceptualProperty"] = entity.binding.conceptual_property
                # Add Hidden if present
                if hasattr(entity, 'hidden') and entity.hidden:
                    entity_data["Hidden"] = entity.hidden

                # Add Terms if present
                if hasattr(entity, 'terms') and entity.terms:
                    for term in entity.terms:
                        term_data = {
                            term.term: {
                                "State": term.state or 'Generated'
                            }
                        }
                        if hasattr(term, 'type') and term.type:
                            term_data[term.term]["Type"] = term.type
                        if hasattr(term, 'weight') and term.weight:
                            term_data[term.term]["Weight"] = term.weight
                        entity_data["Terms"].append(term_data)

                entities_dict[key] = entity_data

        # Convert the data to template context
        # Convert entities to JSON, ensuring proper escaping
        entities_json = json.dumps(entities_dict, indent=2)

        # Escape @ in JSON to prevent template issues
        entities_json = entities_json.replace('@', '\\@')

        return {
            'culture': culture_info.culture,
            'entities_json': entities_json
        }
