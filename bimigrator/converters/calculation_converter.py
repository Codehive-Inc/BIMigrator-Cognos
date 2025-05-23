"""Converter for Tableau calculations to Power BI DAX expressions using FastAPI."""
from dataclasses import dataclass
from typing import Dict, Any, Optional

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
        self.api_base_url = api_config.get('base_url', 'http://localhost:8000')
        self.api_timeout = api_config.get('timeout_seconds', 30)
        
        # Load calculations from the extracted JSON if available
        self.calculations = {}
        output_dir = config.get('output_dir')
        if output_dir:
            calcs_path = f"{output_dir}/extracted/calculations.json"
            try:
                import json
                with open(calcs_path) as f:
                    data = json.load(f)
                    for calc in data.get('calculations', []):
                        self.calculations[calc['TableauName']] = calc
            except Exception as e:
                print(f"Warning: Could not load calculations from {calcs_path}: {e}")
    
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
            
            # Build dependency information
            dependencies = []
            for dep in deps:
                if dep in self.calculations:
                    dep_info = self.calculations[dep]
                    dependencies.append({
                        "caption": dep_info["FormulaCaptionTableau"],
                        "formula": dep_info["FormulaTableau"],
                        "dax": dep_info["FormulaDax"],
                        "tableau_name": dep_info["TableauName"]
                    })
            
            # Prepare the request payload
            payload = {
                "tableau_formula": calc_info.formula,
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
                    dax_expression = dax_expression.replace(
                        f"[{dep['tableau_name'].strip('[]')}]",
                        f"[{dep['caption']}]"
                    )
                
                # Replace table name in expression with the actual table name
                dax_expression = dax_expression.replace(f"'{table_name} (sample_sales_data)'", table_name)

                # Log the conversion
                logging.info(f"Tableau Formula: {calc_info.formula}")
                logging.info(f"DAX Expression: {dax_expression}")

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
