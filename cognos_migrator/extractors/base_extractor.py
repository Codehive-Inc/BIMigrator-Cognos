"""
Base Extractor for Cognos XML report specifications.

This module provides a base class with common functionality for all extractors.
"""

import logging
import xml.etree.ElementTree as ET


class BaseExtractor:
    """Base class for all Cognos XML extractors."""
    
    def __init__(self, logger=None):
        """Initialize the extractor with optional logger."""
        self.logger = logger or logging.getLogger(__name__)
    
    def register_namespace(self, ns):
        """Register XML namespace for ElementTree."""
        if ns and 'ns' in ns:
            ET.register_namespace('', ns['ns'])
            return {"ns": ns['ns']}
        return None
    
    def find_element(self, parent, element_name, ns=None):
        """Find an element with namespace handling."""
        if ns and 'ns' in ns:
            return parent.find(".//{{{0}}}{1}".format(ns['ns'], element_name))
        return parent.find(".//{0}".format(element_name))
    
    def findall_elements(self, parent, element_name, ns=None):
        """Find all elements with namespace handling."""
        if ns and 'ns' in ns:
            return parent.findall(".//{{{0}}}{1}".format(ns['ns'], element_name))
        return parent.findall(".//{0}".format(element_name))
    
    def find_direct_child(self, parent, element_name, ns=None):
        """Find a direct child element with namespace handling."""
        if ns and 'ns' in ns:
            return parent.find("{{{0}}}{1}".format(ns['ns'], element_name))
        return parent.find(element_name)
    
    def findall_direct_children(self, parent, element_name, ns=None):
        """Find all direct child elements with namespace handling."""
        if ns and 'ns' in ns:
            return parent.findall("{{{0}}}{1}".format(ns['ns'], element_name))
        return parent.findall(element_name)
    
    def get_element_text(self, element):
        """Safely get text from an XML element."""
        if element is None:
            return ""
        return element.text or ""
    
    def get_attribute(self, element, attr_name, default=""):
        """Safely get attribute from an XML element."""
        if element is None:
            return default
        return element.get(attr_name, default)
    
    def get_tag_name(self, element):
        """Get the tag name without namespace."""
        if element is None:
            return ""
        tag = element.tag
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
