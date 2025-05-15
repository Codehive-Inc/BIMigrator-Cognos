import io
from typing import Dict, Any

from bimigrator.config.data_classes import CultureInfo, LinguisticMetadata, EntityBinding, LinguisticTerm
from .base_parser import BaseParser


class CultureParser(BaseParser):
    """Parser for extracting culture information from Tableau workbooks."""

    def __init__(self, twb_file: str | io.BytesIO, config: Dict[str, Any]):
        super().__init__(twb_file, config)
        self.culture_config = config.get('PowerBiCulture', {})

    def extract_culture_info(self) -> CultureInfo:
        """Extract culture information from the workbook."""
        # Get locale from preferences
        locale_xpath = self.culture_config.get('locale', {}).get('source_xpath')
        locale_attr = self.culture_config.get('locale', {}).get('source_attribute')
        default_locale = self.culture_config.get('locale', {}).get('default', 'en-US')

        culture = default_locale
        if locale_xpath and locale_attr:
            locale_elem = self.tree.find(locale_xpath)
            if locale_elem is not None:
                # Handle @ in attribute names
                culture = self._get_attribute(locale_elem, locale_attr, default_locale)

        # Create linguistic metadata
        metadata = LinguisticMetadata()
        metadata.language = culture

        # Extract entities from tables and columns
        entities = self._extract_entities()
        if entities:
            metadata.entities = entities

        return CultureInfo(
            culture=culture,
            linguistic_metadata=metadata
        )

    def _extract_entities(self) -> Dict[str, Any]:
        """Extract linguistic entities from tables and columns."""
        entities = {}

        # Extract table entities
        tables_config = self.culture_config.get('entities', {}).get('tables', {})
        if tables_config:
            table_xpath = tables_config.get('source_xpath')
            name_attr = tables_config.get('name_attribute')
            binding_template = tables_config.get('binding_template', {})

            if table_xpath and name_attr:
                for table in self.tree.findall(table_xpath):
                    # Handle @ in attribute names
                    # Try primary attribute first, then fallback
                    table_name = self._get_attribute(table, name_attr)
                    if not table_name and tables_config.get('fallback_attribute'):
                        table_name = self._get_attribute(table, tables_config['fallback_attribute'])
                    if table_name:
                        entity_key = f"Table_{table_name}"
                        binding = EntityBinding(conceptual_entity=table_name)
                        terms = []
                        if binding_template.get('Terms'):
                            for term_template in binding_template['Terms']:
                                terms.append(LinguisticTerm(
                                    term=table_name,
                                    state=term_template.get('State', 'Generated')
                                ))
                        entities[entity_key] = {
                            'binding': binding,
                            'state': binding_template.get('State', 'Generated'),
                            'terms': terms
                        }

        # Extract column entities
        columns_config = self.culture_config.get('entities', {}).get('columns', {})
        if columns_config:
            col_xpath = columns_config.get('source_xpath')
            name_attr = columns_config.get('name_attribute')
            parent_ref = columns_config.get('parent_ref')
            binding_template = columns_config.get('binding_template', {})

            if col_xpath and name_attr:
                for col in self.tree.findall(col_xpath):
                    # Handle @ in attribute names
                    # Try primary attribute first, then fallback
                    col_name = self._get_attribute(col, name_attr)
                    if not col_name and columns_config.get('fallback_attribute'):
                        col_name = self._get_attribute(col, columns_config['fallback_attribute'])
                    if col_name:
                        # Get parent table name if parent_ref is specified
                        parent_name = None
                        if parent_ref:
                            parent = col.find(parent_ref)
                            if parent is not None:
                                parent_name = parent.text

                        entity_key = f"Column_{parent_name}_{col_name}" if parent_name else f"Column_{col_name}"
                        binding = EntityBinding(
                            conceptual_entity=col_name,
                            conceptual_property=parent_name if parent_name else None
                        )
                        terms = []
                        if binding_template.get('Terms'):
                            for term_template in binding_template['Terms']:
                                terms.append(LinguisticTerm(
                                    term=col_name,
                                    state=term_template.get('State', 'Generated')
                                ))
                        entities[entity_key] = {
                            'binding': binding,
                            'state': binding_template.get('State', 'Generated'),
                            'hidden': binding_template.get('Hidden', False),
                            'terms': terms
                        }

        return entities

    def extract_all(self) -> Dict[str, Any]:
        """Extract all culture information."""
        return {
            "culture_info": self.extract_culture_info()
        }
