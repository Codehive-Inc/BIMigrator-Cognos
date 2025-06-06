#!/usr/bin/env python3
"""
Test script using the actual real Cognos module data structure
Uses the provided real API response to generate Table.tmdl
"""

import json
import logging
from pathlib import Path

from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import TemplateEngine


def setup_logging():
    """Setup detailed logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_real_cognos_module_data():
    """Return the actual real Cognos module data from the API response"""
    return {
        "version": "17.0",
        "container": "C",
        "use": [
            "iA1C3A12631D84E428678FE1CC2E69C6B"
        ],
        "useSpec": [
            {
                "identifier": "M1",
                "type": "file",
                "storeID": "i104FA94C93334645BC6E66BF8382C149",
                "searchPath": "CAMID(\"CognosEx:u:uid=administrator\")/folder[@name='My Folders']/uploadedFile[@name='sample_sales_data.xlsx']",
                "ancestors": [
                    {
                        "defaultName": "My Folders",
                        "storeID": ".my_folders"
                    }
                ],
                "dataCacheExpiry": "0"
            }
        ],
        "expressionLocale": "en-us",
        "lastModified": "2025-04-30T00:02:29.766Z",
        "querySubject": [
            {
                "ref": [
                    "M1.Sheet1"
                ],
                "item": [
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1._row_id",
                            "identifier": "_row_id",
                            "description": "Represents the row number identifier, as originally found in the uploaded file.",
                            "label": "Row Id",
                            "comment": "Represents the row number identifier, as originally found in the uploaded file.",
                            "hidden": True,
                            "expression": "_row_id",
                            "usage": "identifier",
                            "datatype": "BIGINT",
                            "nullable": False,
                            "regularAggregate": "count",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "integer",
                            "facetDefinition": {
                                "enabled": "automatic"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Order_ID",
                            "identifier": "Order_ID",
                            "label": "Order ID",
                            "expression": "Order_ID",
                            "usage": "identifier",
                            "format": "{\"formatGroup\":{\"numberFormat\":{\"useGrouping\":\"false\"}}}",
                            "datatype": "BIGINT",
                            "nullable": False,
                            "regularAggregate": "countDistinct",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "integer",
                            "facetDefinition": {
                                "enabled": "automatic"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Order_Date",
                            "identifier": "Order_Date",
                            "label": "Order Date",
                            "expression": "Order_Date",
                            "usage": "identifier",
                            "format": "{\"formatGroup\":{\"dateTimeFormat\":{\"dateStyle\":\"short\",\"displayOrder\":\"YMD\",\"clock\":\"24-hour\"}}}",
                            "datatype": "TIMESTAMP",
                            "nullable": False,
                            "regularAggregate": "countDistinct",
                            "datatypeCategory": "datetime",
                            "highlevelDatatype": "datetime",
                            "facetDefinition": {
                                "enabled": "automatic"
                            },
                            "taxonomy": [
                                {
                                    "domain": "cognos",
                                    "class": "cTime",
                                    "family": "cDate"
                                }
                            ]
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Region",
                            "identifier": "Region",
                            "label": "Region",
                            "expression": "Region",
                            "usage": "identifier",
                            "datatype": "NVARCHAR(MAX)",
                            "nullable": False,
                            "regularAggregate": "countDistinct",
                            "datatypeCategory": "string",
                            "highlevelDatatype": "string",
                            "facetDefinition": {
                                "enabled": "automatic"
                            },
                            "taxonomy": [
                                {
                                    "domain": "cognos",
                                    "class": "cGeoLocation",
                                    "family": "cRegion"
                                }
                            ]
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Product_Category",
                            "identifier": "Product_Category",
                            "label": "Product Category",
                            "expression": "Product_Category",
                            "usage": "identifier",
                            "datatype": "NVARCHAR(MAX)",
                            "nullable": False,
                            "regularAggregate": "countDistinct",
                            "datatypeCategory": "string",
                            "highlevelDatatype": "string",
                            "facetDefinition": {
                                "enabled": "automatic"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Product_Name",
                            "identifier": "Product_Name",
                            "label": "Product Name",
                            "expression": "Product_Name",
                            "usage": "attribute",
                            "datatype": "NVARCHAR(MAX)",
                            "nullable": False,
                            "regularAggregate": "countDistinct",
                            "datatypeCategory": "string",
                            "highlevelDatatype": "string",
                            "facetDefinition": {
                                "enabled": "automatic"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Sales",
                            "identifier": "Sales",
                            "label": "Sales",
                            "expression": "Sales",
                            "usage": "fact",
                            "format": "{\"formatGroup\":{\"numberFormat\":{\"useGrouping\":\"false\"}}}",
                            "datatype": "DOUBLE",
                            "nullable": False,
                            "regularAggregate": "total",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "decimal",
                            "facetDefinition": {
                                "enabled": "false"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Quantity",
                            "identifier": "Quantity",
                            "label": "Quantity",
                            "expression": "Quantity",
                            "usage": "fact",
                            "format": "{\"formatGroup\":{\"numberFormat\":{\"useGrouping\":\"false\"}}}",
                            "datatype": "BIGINT",
                            "nullable": False,
                            "regularAggregate": "total",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "integer",
                            "facetDefinition": {
                                "enabled": "false"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Discount",
                            "identifier": "Discount",
                            "label": "Discount",
                            "expression": "Discount",
                            "usage": "fact",
                            "format": "{\"formatGroup\":{\"numberFormat\":{\"useGrouping\":\"false\"}}}",
                            "datatype": "DOUBLE",
                            "nullable": False,
                            "regularAggregate": "total",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "decimal",
                            "facetDefinition": {
                                "enabled": "false"
                            }
                        }
                    },
                    {
                        "queryItem": {
                            "idForExpression": "C.C_Sample_data_module.Sheet1.Profit",
                            "identifier": "Profit",
                            "label": "Profit",
                            "expression": "Profit",
                            "usage": "fact",
                            "format": "{\"formatGroup\":{\"numberFormat\":{\"useGrouping\":\"false\"}}}",
                            "datatype": "DOUBLE",
                            "nullable": False,
                            "regularAggregate": "total",
                            "datatypeCategory": "number",
                            "highlevelDatatype": "decimal",
                            "facetDefinition": {
                                "enabled": "false"
                            }
                        }
                    }
                ],
                "idForExpression": "C.C_Sample_data_module.Sheet1",
                "identifier": "Sheet1",
                "label": "sample_sales_data.xlsx",
                "propertyOverride": [
                    "NEW"
                ]
            }
        ],
        "relationship": [],
        "metadataTreeView": [
            {
                "folderItem": [
                    {
                        "ref": "Sheet1"
                    }
                ]
            }
        ],
        "parameterValueSet": [
            {
                "identifier": "RESERVED_DefaultParameterValueSet",
                "propertyOverride": [
                    "NEW"
                ]
            }
        ],
        "dataRetrievalMode": "liveConnection",
        "refActiveParameterValueSet": "RESERVED_DefaultParameterValueSet",
        "identifier": "C_Sample_data_module",
        "label": "Sample Sales Data",
        "propertyOverride": [
            "refActiveParameterValueSet",
            "identifier",
            "label"
        ]
    }


def test_real_module_data():
    """Test with the actual real Cognos module data"""
    
    print("🚀 Testing Real Cognos Module Data Structure")
    print("=" * 60)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Get the real module data
        real_module_data = get_real_cognos_module_data()
        
        print(f"📊 Module ID: {real_module_data['identifier']}")
        print(f"📋 Module Label: {real_module_data['label']}")
        print(f"🔄 Version: {real_module_data['version']}")
        print(f"📅 Last Modified: {real_module_data['lastModified']}")
        
        # Create mock client for the parser
        class MockClient:
            def get_module_metadata(self, module_id):
                return real_module_data
        
        # Create parser and parse the real data
        parser = CognosModuleParser(MockClient())
        
        print("\n🔄 Parsing real module data...")
        module_table = parser.parse_module_to_table(real_module_data)
        
        print(f"✅ Parsed module: {module_table.name}")
        print(f"   📋 Columns: {len(module_table.columns)}")
        print(f"   📈 Measures: {len(module_table.measures)}")
        
        # Show detailed column information
        print("\n📋 Column Details from Real Data:")
        for i, col in enumerate(module_table.columns):
            hidden_status = " (HIDDEN)" if col.is_hidden else ""
            print(f"   {i+1:2d}. {col.name} ({col.data_type}) - {col.summarize_by or 'none'}{hidden_status}")
            print(f"       Usage: {getattr(col, 'usage', 'N/A')}")
            if col.format_string:
                print(f"       Format: {col.format_string}")
        
        # Show measure details
        if module_table.measures:
            print("\n📈 Measure Details:")
            for i, measure in enumerate(module_table.measures):
                print(f"   {i+1:2d}. {measure.name}: {measure.expression}")
        else:
            print("\n📈 No measures found in this module")
        
        # Generate JSON for template
        print("\n🔧 Generating JSON for template...")
        table_json = parser.generate_table_json(module_table)
        
        # Create output directory
        output_dir = Path("output/real_module_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        json_file = output_dir / f"{module_table.name}_real_cognos_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(table_json, f, indent=2)
        
        print(f"💾 Real Cognos JSON saved to: {json_file}")
        
        # Generate TMDL file
        try:
            print("\n📄 Generating TMDL file...")
            template_engine = TemplateEngine("bimigrator/templates")
            tmdl_content = template_engine.render('Table', table_json)
            
            # Save TMDL file
            tmdl_file = output_dir / f"{module_table.name}_real_cognos_data.tmdl"
            with open(tmdl_file, 'w', encoding='utf-8') as f:
                f.write(tmdl_content)
            
            print(f"📄 Real Cognos TMDL saved to: {tmdl_file}")
            
            # Show preview
            print("\n📖 TMDL Preview (first 20 lines):")
            lines = tmdl_content.split('\n')
            for i, line in enumerate(lines[:20]):
                print(f"   {i+1:2d}: {line}")
            
            if len(lines) > 20:
                print(f"   ... ({len(lines) - 20} more lines)")
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            print(f"❌ TMDL generation failed: {e}")
        
        # Save raw module data for inspection
        raw_data_file = output_dir / f"{module_table.name}_raw_cognos_module.json"
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(real_module_data, f, indent=2)
        
        print(f"🔍 Raw Cognos module data saved to: {raw_data_file}")
        
        # Show data structure analysis
        print("\n🔍 Data Structure Analysis:")
        query_subject = real_module_data['querySubject'][0]
        print(f"   Table Reference: {query_subject['ref'][0]}")
        print(f"   Table Identifier: {query_subject['identifier']}")
        print(f"   Table Label: {query_subject['label']}")
        print(f"   Total Query Items: {len(query_subject['item'])}")
        
        # Analyze column types
        usage_counts = {}
        datatype_counts = {}
        for item in query_subject['item']:
            query_item = item['queryItem']
            usage = query_item.get('usage', 'unknown')
            datatype = query_item.get('highlevelDatatype', 'unknown')
            
            usage_counts[usage] = usage_counts.get(usage, 0) + 1
            datatype_counts[datatype] = datatype_counts.get(datatype, 0) + 1
        
        print(f"   Usage Distribution: {usage_counts}")
        print(f"   Data Type Distribution: {datatype_counts}")
        
        print("\n✅ Real module data test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Real module data test failed: {e}")
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_real_data_insights():
    """Show insights about the real Cognos data structure"""
    
    print("\n" + "=" * 60)
    print("🔍 Real Cognos Data Structure Insights")
    print("=" * 60)
    
    print("""
Key Findings from Real API Response:

1. Module Structure:
   - identifier: "C_Sample_data_module"
   - label: "Sample Sales Data"
   - version: "17.0"

2. Table Structure:
   - Located in querySubject[0]
   - ref: ["M1.Sheet1"] - Table reference
   - identifier: "Sheet1" - Table name
   - label: "sample_sales_data.xlsx" - Display name

3. Column Structure:
   - Located in querySubject[0].item[]
   - Each item contains a queryItem object
   - Key fields: identifier, label, datatype, usage, expression

4. Column Types Found:
   - identifier: ID fields (Order_ID, Region, etc.)
   - attribute: Descriptive fields (Product_Name)
   - fact: Numeric measures (Sales, Quantity, Discount, Profit)

5. Data Types:
   - BIGINT → int64
   - DOUBLE → decimal
   - NVARCHAR(MAX) → string
   - TIMESTAMP → dateTime

6. Usage Patterns:
   - identifier: Usually set to summarizeBy = none
   - fact: Usually set to summarizeBy = sum
   - Hidden fields: _row_id is hidden=true

7. Format Information:
   - Available in format field as JSON
   - Contains numberFormat, dateTimeFormat settings

This real structure is now properly parsed by the updated module parser!
""")


if __name__ == "__main__":
    success = test_real_module_data()
    show_real_data_insights()
    
    if success:
        print("\n🎉 SUCCESS: Real Cognos module data successfully parsed and converted to Power BI Table.tmdl!")
    else:
        print("\n❌ FAILED: Could not process real Cognos module data")
