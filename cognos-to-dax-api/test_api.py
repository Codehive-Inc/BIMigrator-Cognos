#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the Tableau to DAX API.
This script sends a sample Tableau formula to the API and prints the DAX result.
"""

import asyncio
import httpx
import json
from pprint import pprint

async def test_conversion():
    """Test the conversion API with a sample Tableau formula."""
    # Sample Tableau formula
    tableau_formula = "{ FIXED [FISCAL_WEEK]:SUM(IF [Calculation_1420604241832890368]=6 or [Calculation_1420604241832890368]=7 THEN [serial_count] END)}"
    table_name = "Custom SQL Query (dlh_nsec_objdb)"
    
    # Prepare the request payload
    payload = {
        "tableau_formula": tableau_formula,
        "table_name": table_name,
        "column_mappings": {
            "[FISCAL_WEEK]": "FISCAL_WEEK",
            "[Calculation_1420604241832890368]": "Weekday",
            "[serial_count]": "serial_count"
        }
    }
    
    # Call the API
    async with httpx.AsyncClient() as client:
        try:
            # First check the health endpoint
            health_response = await client.get("http://localhost:8000/health")
            print("Health check:")
            pprint(health_response.json())
            print("\n")
            
            # Then call the conversion endpoint
            response = await client.post(
                "http://localhost:8000/convert",
                json=payload,
                timeout=30.0
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                print("Conversion result:")
                pprint(result)
                print("\nTableau Formula:")
                print(tableau_formula)
                print("\nDAX Expression:")
                print(result.get("dax_expression", ""))
            else:
                print(f"API request failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling API: {e}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_conversion())
