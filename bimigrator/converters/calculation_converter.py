"""Converter for Tableau calculations to Power BI DAX expressions using FastAPI."""
from dataclasses import dataclass
from typing import Dict, Any, Optional
import os

import httpx

import json
from pathlib import Path
import os
import logging

@dataclass
class CalculationInfo:
    """Information about a Tableau calculation."""
    formula: str
    caption: str
    datatype: str
    role: Optional[str] = None
    internal_name: Optional[str] = None  # Internal Tableau calculation name

class CalculationConverter:
    """Converts Tableau calculations to Power BI DAX expressions using FastAPI."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration.
        
        Args:
            config: Configuration dictionary containing API settings
        """
        self.config = config
        # Get API settings from config or use defaults
        api_config = config.get('api_settings', {})
        base_url = os.getenv('DAX_API_URL') or api_config.get('base_url', 'http://localhost:8000')
        
        # Ensure the URL has a protocol
        if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
            base_url = 'http://' + base_url
            
        self.api_base_url = base_url
        self.api_timeout = api_config.get('timeout_seconds', 30)
        
        # Load calculations from the extracted JSON if available
        self.calculations = {}
        output_dir = config.get('output_dir')
        if output_dir:
            self._load_calculations(output_dir)
    
    def _load_calculations(self, output_dir: str):
        """
        Load existing calculations from the output directory
        
        Args:
            output_dir: The output directory where calculations.json is located
        """
        self.calcs_path = os.path.join(output_dir, 'extracted', 'calculations.json')
        self.calculations = {}
        
        if os.path.exists(self.calcs_path):
            try:
                self._reload_calculations()
            except Exception as e:
                print(f"Warning: Could not load calculations from {self.calcs_path}: {e}")
                
    def _reload_calculations(self):
        """
        Reload calculations from the calculations.json file
        """
        if not os.path.exists(self.calcs_path):
            return
            
        try:
            with open(self.calcs_path) as f:
                data = json.load(f)
                self.calculations = {}
                for calc in data.get('calculations', []):
                    # Store by TableauName with brackets
                    self.calculations[calc['TableauName']] = calc
                    # Also store by TableauName without brackets for easier lookup
                    clean_name = calc['TableauName'].strip('[]')
                    self.calculations[clean_name] = calc
        except Exception as e:
            logging.error(f"Error reloading calculations: {e}")
    
    def convert_to_dax(self, calc_info: CalculationInfo, table_name: str) -> str:
        """Convert a Tableau calculation to DAX using the FastAPI service.
        
        Args:
            calc_info: Information about the calculation
            table_name: Name of the table containing the calculation
            
        Returns:
            DAX expression string. If conversion fails, returns an error message
            but does not modify the original formula.
            
        Raises:
            ValueError: If the calculation cannot be converted
        """
        try:
            # Find dependencies in the formula
            import re
            deps = re.findall(r'\[Calculation_\d+\]', calc_info.formula)
            
            # Log found dependencies
            if deps:
                logging.info(f"Found {len(deps)} dependencies in formula: {calc_info.formula}")
                for dep in deps:
                    logging.info(f"Dependency found: {dep}")
            else:
                logging.info(f"No dependencies found in formula: {calc_info.formula}")
            
            # Build dependency information
            dependencies = []
            formula = calc_info.formula
            for dep in deps:
                if dep in self.calculations:
                    dep_info = self.calculations[dep]
                    # Only include dependency info, don't modify formula
                    dependencies.append({
                        "caption": dep_info["FormulaCaptionTableau"],
                        "formula": dep_info["FormulaTableau"],
                        "dax": dep_info["FormulaDax"],
                        "tableau_name": dep_info["TableauName"],
                        "powerbi_name": dep_info["PowerBIName"]
                    })
                    logging.info(f"Resolved dependency {dep} to '{dep_info['PowerBIName']}' (caption: {dep_info['FormulaCaptionTableau']})")
                else:
                    logging.warning(f"Could not resolve dependency {dep} - not found in calculations dictionary")
            
            # Prepare the request payload
            payload = {
                "tableau_formula": formula,  # Use original formula
                "table_name": table_name,
                "column_mappings": {},
                "dependencies": dependencies
            }
            
            # Make API request
            with httpx.Client(timeout=self.api_timeout) as client:
                endpoint = f"{self.api_base_url}/convert"
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                
                result = response.json()
                dax_expression = result['dax_expression']
                
                # Decode any HTML entities in the DAX expression
                from html import unescape
                dax_expression = unescape(dax_expression)
                
                # Replace Calculation_* references with their Power BI column names
                for dep in dependencies:
                    # Replace fully qualified references (with table name)
                    dax_expression = dax_expression.replace(
                        f"'{table_name}'[{dep['tableau_name'].strip('[]')}]",
                        f"'{table_name}'[{dep['powerbi_name']}]"
                    )
                    # Also replace unqualified references (without table name)
                    dax_expression = dax_expression.replace(
                        f"[{dep['tableau_name'].strip('[]')}]",
                        f"[{dep['powerbi_name']}]"
                    )
                    
                    # Log the replacement for debugging
                    logging.debug(f"Replaced dependency: {dep['tableau_name']} -> {dep['powerbi_name']}")
                
                # Ensure table name is properly quoted in DAX expressions
                dax_expression = dax_expression.replace(f"'{table_name}'", f"'{table_name}'")
                # Remove any extra single quotes around table names
                dax_expression = dax_expression.replace("''", "'")

                # Apply recursive dependency resolution to ensure all nested dependencies are resolved
                dax_expression = self._resolve_nested_dependencies(dax_expression, table_name)
                
                # Log the conversion
                logging.info(f"Tableau Formula: {calc_info.formula}")
                logging.info(f"Final DAX Expression: {dax_expression}")

                return dax_expression
                    
        except Exception as e:
            # Create a DAX comment with the error
            error_msg = str(e).replace('*/', '* /')  # Escape any */ in the error message

            # Log the error
            logging.error(f"Failed to convert Tableau formula: {calc_info.formula}")
            logging.error(f"Error: {error_msg}")

            # Return error message without modifying original formula
            return (
                f"/* ERROR: Could not convert Tableau formula */\n"
                f"/* Error details: {error_msg} */\n"
                "ERROR(\"Conversion failed\")"  # Return ERROR() function for measures/columns
            )
            
    def _resolve_nested_dependencies(self, dax_expression: str, table_name: str, depth=0, processed=None) -> str:
        """
        Recursively resolve nested dependencies in a DAX expression.
        
        This method looks for any remaining Calculation_* references in the DAX expression
        and replaces them with their corresponding Power BI column names.
        
        Args:
            dax_expression: The DAX expression to process
            table_name: The name of the table containing the calculation
            depth: Current recursion depth to prevent infinite recursion
            processed: Set of already processed calculation IDs
            
        Returns:
            The DAX expression with all dependencies resolved
        """
        import re
        
        # Initialize processed set if not provided
        if processed is None:
            processed = set()
            
        # Prevent infinite recursion
        if depth > 10:
            logging.warning("Maximum recursion depth reached while resolving dependencies")
            return dax_expression
            
        # If no expression to process, return as is
        if not dax_expression or len(dax_expression.strip()) == 0:
            return dax_expression
            
        # Make sure we have the latest calculations
        if depth == 0:
            self._reload_calculations()
        
        # Find any remaining Calculation_* references in the expression
        pattern = r'\[Calculation_\d+\]'
        qualified_pattern = f"'{table_name}'\[Calculation_\d+\]"
        
        # Find both unqualified and qualified references
        matches = re.findall(pattern, dax_expression)
        qualified_matches = re.findall(qualified_pattern, dax_expression)
        all_matches = matches + qualified_matches
        
        if not all_matches:
            # No more dependencies to resolve
            return dax_expression
            
        logging.info(f"Found {len(all_matches)} unresolved dependencies in DAX expression (depth {depth})")
        
        # Track if we made any changes in this iteration
        original_dax = dax_expression
        
        # Process each unresolved dependency
        for match in all_matches:
            # Extract the calculation ID
            calc_id_match = re.search(r'Calculation_(\d+)', match)
            if not calc_id_match:
                continue
                
            calc_id = f"Calculation_{calc_id_match.group(1)}"
            tableau_name = f"[{calc_id}]"
            
            # Skip if we've already processed this dependency in this call chain
            if tableau_name in processed:
                continue
                
            processed.add(tableau_name)
            
            # Try multiple ways to find the dependency in the calculations dictionary
            dep_info = None
            if tableau_name in self.calculations:
                dep_info = self.calculations[tableau_name]
            elif calc_id in self.calculations:
                dep_info = self.calculations[calc_id]
            
            if dep_info:
                powerbi_name = dep_info["PowerBIName"]
                
                # Replace in the expression
                if "'" in match:  # Fully qualified reference
                    # Extract the actual table name from the match
                    table_match = re.search(r"'([^']+)'\[Calculation_\d+\]", match)
                    if table_match:
                        actual_table = table_match.group(1)
                        dax_expression = dax_expression.replace(
                            match,
                            f"'{actual_table}'[{powerbi_name}]"
                        )
                else:  # Unqualified reference
                    dax_expression = dax_expression.replace(
                        match,
                        f"[{powerbi_name}]"
                    )
                    
                logging.info(f"Resolved nested dependency: {tableau_name} -> {powerbi_name}")
            else:
                logging.warning(f"Could not resolve nested dependency {tableau_name} - not found in calculations dictionary")
        
        # If we made no changes in this iteration, return to prevent infinite recursion
        if dax_expression == original_dax:
            return dax_expression
            
        # Recursively resolve any remaining dependencies with increased depth
        return self._resolve_nested_dependencies(dax_expression, table_name, depth + 1, processed)
