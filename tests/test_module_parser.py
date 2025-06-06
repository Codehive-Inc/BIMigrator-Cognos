#!/usr/bin/env python3
"""
Simple test script for the module parser
"""

import json
import os
from pathlib import Path

# Create output directory
output_dir = Path("output/module_migration")
output_dir.mkdir(parents=True, exist_ok=True)

# Sample module data that would come from Cognos API
sample_module_data = {
    "id": "iA1C3A12631D84E428678FE1CC2E69C6B",
    "name": "Sales_Analysis_Module",
    "defaultName": "Sales Analysis Module",
    "columns": [
        {
            "name": "ProductID",
            "dataType": "integer",
            "sourceColumn": "ProductID",
            "hidden": False
        },
        {
            "name": "ProductName",
            "dataType": "string",
            "sourceColumn": "ProductName",
            "hidden": False
        },
        {
            "name": "SalesAmount",
            "dataType": "decimal",
            "sourceColumn": "SalesAmount",
            "format": "Currency",
            "hidden": False
        },
        {
            "name": "OrderDate",
            "dataType": "date",
            "sourceColumn": "OrderDate",
            "hidden": False
        }
    ],
    "measures": [
        {
            "name": "Total_Sales",
            "expression": "SUM([SalesAmount])",
            "format": "Currency"
        },
        {
            "name": "Average_Sales",
            "expression": "AVERAGE([SalesAmount])",
            "format": "Currency"
        }
    ],
    "query": "SELECT ProductID, ProductName, SalesAmount, OrderDate FROM Sales"
}

# Create mock client
class MockClient:
    def get_module_metadata(self, module_id):
        return sample_module_data

# Import and test the module parser
try:
    from cognos_migrator.module_parser import CognosModuleParser
    
    parser = CognosModuleParser(MockClient())
    module_table = parser.parse_module_to_table(sample_module_data)
    table_json = parser.generate_table_json(module_table)
    
    # Save the generated JSON
    json_file = output_dir / "Sales_Analysis_Module_table.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(table_json, f, indent=2)
    
    print(f"✅ Module parser test successful!")
    print(f"📊 Generated table: {module_table.name}")
    print(f"📋 Columns: {len(module_table.columns)}")
    print(f"📈 Measures: {len(module_table.measures)}")
    print(f"💾 JSON saved to: {json_file}")
    
    # Test template rendering
    try:
        from cognos_migrator.generators import TemplateEngine
        
        template_engine = TemplateEngine("bimigrator/templates")
        tmdl_content = template_engine.render('Table', table_json)
        
        # Save TMDL file
        tmdl_file = output_dir / "Sales_Analysis_Module.tmdl"
        with open(tmdl_file, 'w', encoding='utf-8') as f:
            f.write(tmdl_content)
        
        print(f"📄 TMDL file generated: {tmdl_file}")
        print("✅ Template rendering successful!")
        
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
    
except Exception as e:
    print(f"❌ Module parser test failed: {e}")
    import traceback
    traceback.print_exc()
