"""Converter for Tableau calculations to Power BI DAX expressions using FastAPI."""
from typing import Dict, Any, Optional
from dataclasses import dataclass
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
    
    def convert_to_dax(self, calc_info: CalculationInfo, table_name: str) -> str:
        """Convert a Tableau calculation to DAX using the FastAPI service.
        
        Args:
            calc_info: Information about the calculation
            table_name: Name of the table containing the calculation
            
        Returns:
            DAX expression string
            
        Raises:
            ValueError: If the calculation cannot be converted
        """
        try:
            # Prepare the request payload
            payload = {
                "tableau_formula": calc_info.formula,
                "table_name": table_name,
                "column_mappings": {}
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
            
            return (
                f"/* ERROR: Could not convert Tableau formula: {calc_info.formula} */\n"
                f"/* Error details: {error_msg} */\n"
                "ERROR(\"Conversion failed\")"  # Return ERROR() function for measures/columns
            )
