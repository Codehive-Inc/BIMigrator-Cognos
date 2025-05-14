"""Test the calculation converter using FastAPI."""
import pytest
from src.converters import CalculationConverter, CalculationInfo
import yaml
from pathlib import Path

def load_config():
    """Load the YAML configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'twb-to-pbi.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_calculation_converter():
    """Test converting different types of calculations."""
    config = load_config()
    converter = CalculationConverter(config)
    
    # Test cases
    test_cases = [
        {
            "name": "Simple SUM measure",
            "info": CalculationInfo(
                formula="SUM([Sales])",
                caption="Total Sales",
                datatype="double",
                role="measure"
            ),
            "table_name": "Sales"
        },
        {
            "name": "Calculated column",
            "info": CalculationInfo(
                formula="[Price] * [Quantity]",
                caption="Line Total",
                datatype="double",
                role=None
            ),
            "table_name": "Sales"
        }
    ]
    
    # Run test cases
    for case in test_cases:
        print(f"\nTesting {case['name']}...")
        try:
            result = converter.convert_to_dax(case['info'], case['table_name'])
            print(f"Input: {case['info'].formula}")
            print(f"Output: {result}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == '__main__':
    test_calculation_converter()
