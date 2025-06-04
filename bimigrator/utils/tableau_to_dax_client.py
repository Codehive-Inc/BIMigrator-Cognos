"""
Client for the Tableau to DAX API service.
This module provides functions to call the FastAPI service for converting Tableau formulas to DAX.
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Default API endpoint (can be overridden with environment variable)
base_url = os.getenv("DAX_API_URL") or os.getenv("TABLEAU_TO_DAX_API_ENDPOINT") or "http://localhost:8000"

# Ensure the URL has a protocol
if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
    base_url = 'http://' + base_url
    
API_ENDPOINT = base_url

# Check if the API service is available
try:
    response = httpx.get(f"{API_ENDPOINT}/health", timeout=2.0)
    API_AVAILABLE = response.status_code == 200
    if API_AVAILABLE:
        logger.info(f"Tableau to DAX API service is available at {API_ENDPOINT}")
    else:
        logger.warning(f"Tableau to DAX API service returned status code {response.status_code}")
        API_AVAILABLE = False
except Exception as e:
    logger.warning(f"Tableau to DAX API service is not available: {str(e)}")
    API_AVAILABLE = False


def convert_tableau_formula_to_dax(
    tableau_formula: str,
    table_name: str,
    column_mappings: Optional[Dict[str, str]] = None
) -> str:
    """
    Convert a Tableau formula to a DAX expression using the API service.
    
    Args:
        tableau_formula: The Tableau formula to convert
        table_name: The name of the table containing the formula
        column_mappings: Optional mapping of column names to their display names
        
    Returns:
        A DAX expression equivalent to the Tableau formula
        
    Raises:
        Exception: If the API service is not available or returns an error
    """
    # If the API is not available, raise an exception
    if not API_AVAILABLE:
        error_msg = "Tableau to DAX API service is not available"
        logger.error(error_msg)
        raise Exception(error_msg)
        
    try:
        # Make a synchronous HTTP request to the API
        payload = {
            "tableau_formula": tableau_formula,
            "table_name": table_name,
            "column_mappings": column_mappings or {}
        }
        
        response = httpx.post(
            f"{API_ENDPOINT}/convert",
            json=payload,
            timeout=30.0  # 30 second timeout
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("dax_expression", "")
        else:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Error calling Tableau to DAX API: {str(e)}")
        raise


def convert_tableau_calculation_to_dax_measure(
    tableau_calc: Dict[str, Any],
    table_name: str,
    column_mappings: Optional[Dict[str, str]] = None
) -> str:
    """
    Convert a Tableau calculation to a DAX measure expression using the API service.
    
    Args:
        tableau_calc: Dictionary containing Tableau calculation attributes
        table_name: The name of the table containing the calculation
        column_mappings: Optional mapping of column names to their display names
        
    Returns:
        A DAX measure expression
    """
    formula = tableau_calc.get('formula', '')
    caption = tableau_calc.get('caption', '')
    
    # Add debug information
    logger.info(f"Converting Tableau measure: {caption or 'Unnamed'} with formula: {formula}")
    
    # Call the API service
    return convert_tableau_formula_to_dax(formula, table_name, column_mappings)


def convert_tableau_calculation_to_dax_column(
    tableau_calc: Dict[str, Any],
    table_name: str,
    column_mappings: Optional[Dict[str, str]] = None
) -> str:
    """
    Convert a Tableau calculation to a DAX calculated column expression using the API service.
    
    Args:
        tableau_calc: Dictionary containing Tableau calculation attributes
        table_name: The name of the table containing the calculation
        column_mappings: Optional mapping of column names to their display names
        
    Returns:
        A DAX calculated column expression
    """
    formula = tableau_calc.get('formula', '')
    caption = tableau_calc.get('caption', '')
    
    # Add debug information
    logger.info(f"Converting Tableau calculated column: {caption or 'Unnamed'} with formula: {formula}")
    
    # Call the API service
    return convert_tableau_formula_to_dax(formula, table_name, column_mappings)
