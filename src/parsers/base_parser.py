import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from pathlib import Path

class BaseParser:
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        self.tree = ET.parse(twb_path)
        self.root = self.tree.getroot()
        self.namespaces = {'': self.root.tag.split('}')[0].strip('{')} if '}' in self.root.tag else {}
        self.twb_file = twb_path
        self.config = config
    
    def _find_elements(self, xpath: Optional[str]) -> List[ET.Element]:
        if not xpath:
            return []
        
        if xpath.startswith('//'):
            xpath = '.' + xpath
            
        # Handle attribute queries
        if '@' in xpath:
            base_xpath, attr = xpath.rsplit('@', 1)
            base_xpath = base_xpath.rstrip('/')
            elements = self.root.findall(base_xpath, self.namespaces)
            return [e for e in elements if attr in e.attrib]
            
        return self.root.findall(xpath, self.namespaces)
    
    def _get_element_text(self, element: ET.Element, default: str = None) -> str:
        if element is not None and element.text is not None:
            return element.text
        return default
    
    def _get_attribute(self, element: ET.Element, attribute: str, default: Any = None) -> Any:
        if element is not None and attribute in element.attrib:
            return element.attrib[attribute]
        return default
    
    def _get_mapping_value(self, mapping: Dict[str, Any], element: ET.Element, default: Any = None) -> Any:
        if 'source_attribute' in mapping:
            return self._get_attribute(element, mapping['source_attribute'], default)
            
        if 'source_xpath' in mapping:
            xpath = mapping['source_xpath']
            if '@' in xpath:
                base_xpath, attr = xpath.rsplit('@', 1)
                base_xpath = base_xpath.rstrip('/')
                elements = self.root.findall(base_xpath, self.namespaces)
                if elements:
                    return elements[0].get(attr, default)
            else:
                elements = self._find_elements(xpath)
                if elements:
                    return self._get_element_text(elements[0], default)
                
        if 'alternative_xpath' in mapping:
            xpath = mapping['alternative_xpath']
            if '@' in xpath:
                base_xpath, attr = xpath.rsplit('@', 1)
                base_xpath = base_xpath.rstrip('/')
                elements = self.root.findall(base_xpath, self.namespaces)
                if elements:
                    return elements[0].get(attr, default)
            else:
                elements = self._find_elements(xpath)
                if elements:
                    return self._get_element_text(elements[0], default)
                
        return mapping.get('default', default)
