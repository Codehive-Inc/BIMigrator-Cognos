import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

class BaseParser:
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        """Initialize with TWB file path and configuration."""
        self.tree = ET.parse(twb_path)
        self.root = self.tree.getroot()
        self.config = config
        
        # Initialize namespaces properly for Tableau workbooks
        self.namespaces = {}
        if '}' in self.root.tag:
            # Extract default namespace
            ns = self.root.tag.split('}')[0].strip('{')
            self.namespaces = {
                '': ns,  # Default namespace
                'user': ns,  # Common Tableau namespace
                '_': ns,  # For _.fcp... elements
                'fcp': ns  # For fcp elements
            }
        
        self.twb_file = twb_path
        
    def _get_attribute(self, element: ET.Element, attr_name: str, default: Any = None) -> Any:
        """Get attribute value, handling @ in attribute names."""
        return element.get(attr_name.replace('@', ''), default)
        self.config = config
        self.intermediate_dir = Path(self.config.get('Output', {}).get('intermediate_dir', 'extracted'))
        self.validate_intermediate = self.config.get('Output', {}).get('validate_intermediate', True)
        
        # Create intermediate directory if it doesn't exist
        if not self.intermediate_dir.exists():
            self.intermediate_dir.mkdir(parents=True)
    
    def _find_elements(self, xpath: Optional[str]) -> List[ET.Element]:
        """Find elements in the XML tree using XPath.
        
        Args:
            xpath: XPath expression to find elements
            
        Returns:
            List of matching elements
        """
        if not xpath:
            print("Warning: Empty XPath provided to _find_elements")
            return []
        
        # For complex XPath expressions with predicates, use a simpler approach
        if '[' in xpath and ']' in xpath:
            try:
                # First, try with namespaces
                result = self.root.findall(xpath, self.namespaces)
                return result
            except Exception as e:
                try:
                    # Try without namespaces
                    result = self.root.findall(xpath)
                    return result
                except Exception:
                    # Try a more basic approach - get all datasources and filter manually
                    if "datasource" in xpath:
                        try:
                            # Get all datasources
                            all_datasources = self.root.findall(".//datasource") or self.root.findall("//datasource")
                            
                            # Filter out Parameters datasources
                            if "Parameters" in xpath:
                                filtered = [ds for ds in all_datasources if ds.get("name") != "Parameters"]
                                return filtered
                            return all_datasources
                        except Exception:
                            pass
                    return []
        
        # Make relative XPath if it's absolute
        if xpath.startswith('//'):
            xpath = '.' + xpath
        
        try:
            # Handle attribute queries
            if '@' in xpath and not xpath.endswith('/'):
                base_xpath, attr = xpath.rsplit('@', 1)
                base_xpath = base_xpath.rstrip('/')
                try:
                    elements = self.root.findall(base_xpath, self.namespaces)
                    return [e for e in elements if attr in e.attrib]
                except Exception:
                    return []
            
            # Handle normal XPath queries
            elements = self.root.findall(xpath, self.namespaces)
            return elements
        except Exception:
            # Try without namespaces as a fallback
            try:
                elements = self.root.findall(xpath)
                return elements
            except Exception:
                return []
    
    def _get_element_text(self, element: ET.Element, default: str = None) -> str:
        if element is not None and element.text is not None:
            return element.text
        return default
    
    def _get_attribute(self, element: ET.Element, attribute: str, default: Any = None) -> Any:
        if element is not None and attribute in element.attrib:
            return element.attrib[attribute]
        return default
    
    def _get_mapping_value(self, mapping_config: Dict[str, Any], context_element: ET.Element, default_value: Any = None) -> Any:
        """Get a value from an element based on mapping configuration.
        
        Args:
            mapping_config: Mapping configuration dictionary
            context_element: Element to extract value from
            default_value: Default value if no value is found
            
        Returns:
            Extracted value or default value
        """
        if not mapping_config or context_element is None:
            return default_value

        value = None
        
        # Try source_xpath first if present (can be relative to context_element)
        if 'source_xpath' in mapping_config:
            xpath = mapping_config['source_xpath']
            try:
                # For attribute XPaths like './@name' or nested elements
                if '/@' in xpath:
                    # Handle attribute selection in the path
                    parts = xpath.rsplit('/@', 1)
                    elem_path = parts[0] if parts[0] else '.'
                    attr_name = parts[1]
                    
                    # Find the element relative to context_element
                    target_elem = context_element.find(elem_path, self.namespaces)
                    if target_elem is not None:
                        value = target_elem.get(attr_name)
                else:
                    # Path targets an element, get its text
                    target_elem = context_element.find(xpath, self.namespaces)
                    if target_elem is not None:
                        value = target_elem.text
            except Exception as e:
                print(f"Warning: XPath error for '{xpath}': {e}")
                value = None

        # If XPath didn't yield a value, try source_attribute
        if value is None and 'source_attribute' in mapping_config:
            attr_name = mapping_config['source_attribute']
            value = context_element.get(attr_name)

        # Fallback attribute if primary attribute is not found
        if value is None and 'fallback_attribute' in mapping_config:
            attr_name = mapping_config['fallback_attribute']
            value = context_element.get(attr_name)
        
        # Try alternative_xpath if defined and no value found yet
        if value is None and 'alternative_xpath' in mapping_config:
            xpath = mapping_config['alternative_xpath']
            try:
                if '/@' in xpath:
                    parts = xpath.rsplit('/@', 1)
                    elem_path = parts[0] if parts[0] else '.'
                    attr_name = parts[1]
                    target_elem = context_element.find(elem_path, self.namespaces)
                    if target_elem is not None:
                        value = target_elem.get(attr_name)
                else:
                    target_elem = context_element.find(xpath, self.namespaces)
                    if target_elem is not None:
                        value = target_elem.text
            except Exception as e:
                print(f"Warning: Alternative XPath error for '{xpath}': {e}")
                value = None
        
        # Apply formatting/conversion if a value was found
        if value is not None:
            if mapping_config.get('format') == 'boolean':
                if isinstance(value, str):
                    return value.lower() == 'true'
                return bool(value)  # Basic cast for non-string values
            
            if mapping_config.get('format') == 'identifier' and isinstance(value, str):
                # Clean up identifier if needed
                return value.strip()
                
            # Default string handling: strip whitespace
            return value.strip() if isinstance(value, str) else value

        # If still no value, use default from config, then passed default_value
        return mapping_config.get('default', default_value)
    
    def save_intermediate(self, data: Dict[str, Any], name: str) -> None:
        """Save intermediate data to JSON file.
        
        Args:
            data: Data to save
            name: Name of the intermediate file (without extension)
        """
        if not self.intermediate_dir.exists():
            self.intermediate_dir.mkdir(parents=True)
            
        output_path = self.intermediate_dir / f'{name}.json'
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
