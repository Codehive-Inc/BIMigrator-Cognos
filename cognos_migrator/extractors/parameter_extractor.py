"""
Parameter Extractor for Cognos XML report specifications.

This module provides functionality to extract parameter information from Cognos XML report specifications.
"""

import logging
from .base_extractor import BaseExtractor


class ParameterExtractor(BaseExtractor):
    """Extractor for parameters from Cognos XML report specifications."""
    
    def __init__(self, logger=None):
        """Initialize the parameter extractor with optional logger."""
        super().__init__(logger)
    
    def extract_parameters(self, root, ns=None):
        """Extract parameters from report specification XML"""
        parameters = []
        try:
            # Register namespace if present
            namespace = self.register_namespace(ns)
            
            # Find the parameters section
            params_section = self.find_element(root, "parameters", ns)
            if params_section is None:
                # Try to find parameters in other locations
                params_section = self.find_element(root, "parameterList", ns)
                    
            if params_section is None:
                self.logger.warning("No parameters section found in report specification")
                return parameters
            
            # Process each parameter
            param_elements = self.findall_elements(params_section, "parameter", ns)
                
            for i, param_elem in enumerate(param_elements):
                param = {
                    "id": param_elem.get("id", f"param_{i}"),
                    "name": param_elem.get("name", f"Parameter {i}"),
                    "type": param_elem.get("type", ""),
                    "required": param_elem.get("required", "false"),
                    "multiValue": param_elem.get("multiValue", "false"),
                }
                
                # Extract default values if present
                default_elem = self.find_element(param_elem, "defaultValues", ns)
                if default_elem is not None:
                    default_values = []
                    value_elements = self.findall_elements(default_elem, "item", ns)
                    for value_elem in value_elements:
                        value = self.get_element_text(value_elem)
                        if value:
                            default_values.append(value)
                    
                    if default_values:
                        param["defaultValues"] = default_values
                
                # Extract parameter properties
                properties_elem = self.find_element(param_elem, "parameterProperties", ns)
                if properties_elem is not None:
                    properties = {}
                    
                    # Extract prompt text
                    prompt_elem = self.find_element(properties_elem, "promptText", ns)
                    if prompt_elem is not None:
                        properties["promptText"] = self.get_element_text(prompt_elem)
                    
                    # Extract other properties
                    for prop_name in ["hidden", "selectAll", "selectAllTitle", "autoSubmit"]:
                        prop_elem = self.find_element(properties_elem, prop_name, ns)
                        if prop_elem is not None:
                            properties[prop_name] = self.get_element_text(prop_elem)
                    
                    if properties:
                        param["properties"] = properties
                
                parameters.append(param)
                
        except Exception as e:
            self.logger.warning(f"Error extracting parameters: {e}")
            
        return parameters
