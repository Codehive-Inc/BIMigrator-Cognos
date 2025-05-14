from pathlib import Path
import sys
from typing import Dict, Any, List, Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.data_classes import PowerBiModel, DataAccessOptions
from .base_parser import BaseParser
from .table_parser import TableParser

class ModelParser(BaseParser):
    """Parser for extracting model information from Tableau workbooks."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
        self.table_parser = TableParser(twb_path, config)
    
    def extract_model_info(self) -> (PowerBiModel, List[Any]):
        """Extract model information from the workbook.
        
        Returns:
            PowerBiModel: The extracted model information
            List[Any]: The extracted tables
        """
        mapping = self.config['PowerBiModel']
        
        # Extract model name
        name = self._get_mapping_value(mapping.get('model_name', {}), None, 'Model')
        
        # Extract culture
        culture = self._get_mapping_value(mapping.get('culture', {}), None, 'en-US')
        
        # Get data access options
        data_access = mapping.get('data_access', {})
        data_access_options = DataAccessOptions(
            legacy_redirects=data_access.get('legacy_redirects', True),
            return_error_values_as_null=data_access.get('return_null_errors', True)
        )
        
        # Extract query order
        query_order = []
        query_order_mapping = mapping.get('query_order', {})
        if query_order_mapping:
            query_order_elements = self._find_elements(query_order_mapping.get('source_xpath', ''))
            query_order = [elem.get('name') for elem in query_order_elements if elem.get('name')]
        
        # Check for time intelligence
        time_intelligence_enabled = False
        time_intelligence_mapping = mapping.get('time_intelligence', {})
        if time_intelligence_mapping:
            time_intelligence_elements = self._find_elements(time_intelligence_mapping.get('source_xpath', ''))
            time_intelligence_enabled = bool(time_intelligence_elements)
        
        # Extract annotations
        annotations = {}
        annotations_mapping = mapping.get('annotations', {})
        if annotations_mapping:
            annotations_elements = self._find_elements(annotations_mapping.get('source_xpath', ''))
            if annotations_elements:
                try:
                    annotations = self._parse_annotations(annotations_elements[0])
                except Exception:
                    pass  # Ignore annotation parsing errors
        
        # Extract desktop version from annotations
        desktop_version = None
        if 'PBIDesktopVersion' in annotations:
            desktop_version = annotations['PBIDesktopVersion']
        
        # Extract tables using table parser
        tables = self.table_parser.extract_all_tables()
        # Deduplicate table names while preserving order
        seen = set()
        table_names = [x for x in (table.source_name for table in tables) if not (x in seen or seen.add(x))]
        
        return PowerBiModel(
            model_name=name,
            culture=culture,
            data_access_options=data_access_options,
            query_order=query_order,
            time_intelligence_enabled=time_intelligence_enabled,
            tables=table_names,
            desktop_version=desktop_version
        ), tables
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all model information.
        
        Returns:
            Dict containing PowerBiModel information
        """
        model, tables = self.extract_model_info()
        return {
            'PowerBiModel': model,
            'PowerBiTables': tables
        }
    
    def _parse_annotations(self, element: Any) -> Dict[str, Any]:
        """Parse annotations from XML element.
        
        Args:
            element: XML element containing annotations
            
        Returns:
            Dictionary of parsed annotations
        """
        annotations = {}
        for annotation in element.findall('.//annotation'):
            name = annotation.get('name')
            value = annotation.text
            if name and value:
                annotations[name] = value
        return annotations


def parse_workbook(twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a Tableau workbook file.
    
    Args:
        twb_path: Path to the TWB file
        config: Configuration dictionary
        
    Returns:
        Dict containing extracted model information
    """
    parser = ModelParser(twb_path, config)
    return parser.extract_all()
