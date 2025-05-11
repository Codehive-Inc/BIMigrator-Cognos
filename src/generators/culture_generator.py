import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, Any

from config.dataclasses import (
    CultureInfo,
    LinguisticMetadata,
    LinguisticEntity,
    EntityBinding
)

class CultureGenerator:
    """Generates culture TMDL files from Tableau workbook."""
    
    def __init__(self, yaml_mappings: Dict[str, Any]):
        """Initialize with YAML mappings."""
        self.mappings = yaml_mappings['PowerBiCulture']  # Get culture-specific mappings
    
    def generate_culture_tmdl(self, twb_path: str, output_dir: Path) -> None:
        """Generate culture TMDL file from TWB."""
        # Parse TWB
        tree = ET.parse(twb_path)
        root = tree.getroot()
        
        # Get culture from TWB or use default
        locale_xpath = self.mappings['locale']['source_xpath']
        locale_elem = root.find(locale_xpath)
        culture = locale_elem.get(
            self.mappings['locale']['source_attribute']
        ) if locale_elem is not None else self.mappings['locale']['default']
        
        # Create culture info structure
        culture_info = CultureInfo(
            culture=culture,
            linguistic_metadata=LinguisticMetadata(
                language=culture
            )
        )
        
        # Extract entities from tables
        table_xpath = self.mappings['entities']['tables']['source_xpath']
        for table in root.findall(table_xpath):
            table_name = table.get(self.mappings['entities']['tables']['name_attribute'])
            if not table_name:
                continue
                
            # Add table entity
            table_entity = LinguisticEntity(
                binding=EntityBinding(
                    conceptual_entity=table_name
                ),
                terms=[{
                    table_name.lower(): {"State": "Generated"}
                }]
            )
            culture_info.linguistic_metadata.entities[table_name.lower()] = table_entity
            
            # Add column entities
            column_xpath = self.mappings['entities']['columns']['source_xpath']
            for column in table.findall(column_xpath):
                column_name = column.get(self.mappings['entities']['columns']['name_attribute'])
                if not column_name:
                    continue
                    
                entity_key = f"{table_name.lower()}.{column_name.lower()}"
                column_entity = LinguisticEntity(
                    binding=EntityBinding(
                        conceptual_entity=table_name,
                        conceptual_property=column_name
                    ),
                    hidden=True,
                    terms=[{
                        column_name.lower().replace('_', ' '): {"State": "Generated"}
                    }]
                )
                culture_info.linguistic_metadata.entities[entity_key] = column_entity
        
        # Generate TMDL content
        tmdl_content = self._generate_tmdl(culture_info)
        
        # Write to file
        output_path = output_dir / 'Model' / 'cultures' / f"{culture}.tmdl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tmdl_content)
    
    def _generate_tmdl(self, culture_info: CultureInfo) -> str:
        """Generate TMDL content from CultureInfo."""
        metadata_dict = {
            'Version': culture_info.linguistic_metadata.version,
            'Language': culture_info.linguistic_metadata.language,
            'DynamicImprovement': culture_info.linguistic_metadata.dynamic_improvement,
            'Entities': {}
        }
        
        # Convert entities
        for entity_name, entity in culture_info.linguistic_metadata.entities.items():
            metadata_dict['Entities'][entity_name] = {
                'Binding': {
                    'ConceptualEntity': entity.binding.conceptual_entity,
                    **(
                        {'ConceptualProperty': entity.binding.conceptual_property}
                        if entity.binding.conceptual_property else {}
                    )
                },
                'State': entity.state,
                'Terms': entity.terms
            }
            if entity.hidden:
                metadata_dict['Entities'][entity_name]['Hidden'] = True
        
        # Generate TMDL content
        lines = [
            f'cultureInfo {culture_info.culture}\n',
            '\tlinguisticMetadata =',
            '\t\t' + json.dumps(metadata_dict, indent=2).replace('\n', '\n\t\t')
        ]
        
        return '\n'.join(lines)
