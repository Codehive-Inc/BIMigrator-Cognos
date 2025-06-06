#!/usr/bin/env python3
"""
Demo script for Cognos Module to Power BI Table migration
Shows how to fetch module data from Cognos Analytics and populate Table.tmdl template
"""

import os
import json
import logging
from pathlib import Path

from cognos_migrator.config import CognosConfig
from cognos_migrator.client import CognosClient
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import TemplateEngine


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config():
    """Load Cognos configuration from environment"""
    return CognosConfig(
        base_url=os.getenv('COGNOS_BASE_URL', 'http://localhost:9300/api/v1'),
        username=os.getenv('COGNOS_USERNAME', ''),
        password=os.getenv('COGNOS_PASSWORD', ''),
        namespace=os.getenv('COGNOS_NAMESPACE', 'LDAP'),
        auth_key=os.getenv('COGNOS_AUTH_KEY', 'IBM-BA-Authorization'),
        auth_value=os.getenv('COGNOS_AUTH_VALUE', '')
    )


def demo_module_parsing():
    """Demo function showing module parsing workflow"""
    
    print("🚀 Cognos Module to Power BI Table Migration Demo")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        print(f"📡 Connecting to Cognos at: {config.base_url}")
        
        # Create client
        client = CognosClient(config)
        
        # Test connection
        if not client.test_connection():
            print("❌ Failed to connect to Cognos Analytics")
            print("Please check your credentials in .env file")
            return
        
        print("✅ Connected to Cognos Analytics successfully")
        
        # Create module parser
        parser = CognosModuleParser(client)
        
        # List available modules
        print("\n📋 Listing available modules...")
        modules = client.list_modules()
        
        if not modules:
            print("⚠️  No modules found. Using demo data instead.")
            demo_with_sample_data(parser)
            return
        
        print(f"Found {len(modules)} modules:")
        for i, module in enumerate(modules[:5]):  # Show first 5
            print(f"  {i+1}. {module.get('name', 'Unknown')} (ID: {module.get('id', 'N/A')})")
        
        # Use the specified module ID or first available module
        target_module_id = "iA1C3A12631D84E428678FE1CC2E69C6B"  # From your example
        
        # Check if target module exists
        target_module = None
        for module in modules:
            if module.get('id') == target_module_id:
                target_module = module
                break
        
        if not target_module:
            print(f"⚠️  Target module {target_module_id} not found. Using first available module.")
            target_module = modules[0]
            target_module_id = target_module['id']
        
        print(f"\n🎯 Processing module: {target_module.get('name', 'Unknown')} (ID: {target_module_id})")
        
        # Fetch and parse module
        module_data = parser.fetch_module(target_module_id)
        module_table = parser.parse_module_to_table(module_data)
        
        print(f"📊 Parsed module into table: {module_table.name}")
        print(f"   - Columns: {len(module_table.columns)}")
        print(f"   - Measures: {len(module_table.measures)}")
        
        # Generate JSON for template
        table_json = parser.generate_table_json(module_table)
        
        # Save JSON to file
        output_dir = Path("output/module_migration")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_file = output_dir / f"{module_table.name}_table.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(table_json, f, indent=2)
        
        print(f"💾 Saved table JSON to: {json_file}")
        
        # Generate TMDL file using template
        generate_tmdl_file(table_json, output_dir, module_table.name)
        
        print("\n✅ Module migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        
        # Fallback to demo data
        print("\n🔄 Falling back to demo data...")
        demo_with_sample_data()


def demo_with_sample_data(parser=None):
    """Demo using sample data when Cognos is not available"""
    
    print("\n🧪 Running demo with sample data...")
    
    # Create sample module data
    sample_module_data = {
        "id": "iA1C3A12631D84E428678FE1CC2E69C6B",
        "name": "Sales_Analysis_Module",
        "defaultName": "Sales Analysis Module",
        "label": "Sales Analysis",
        "columns": [
            {
                "name": "ProductID",
                "defaultName": "Product ID",
                "dataType": "integer",
                "sourceColumn": "ProductID",
                "hidden": False,
                "usage": "identifier"
            },
            {
                "name": "ProductName",
                "defaultName": "Product Name",
                "dataType": "string",
                "sourceColumn": "ProductName",
                "hidden": False,
                "usage": "attribute"
            },
            {
                "name": "CategoryName",
                "defaultName": "Category Name",
                "dataType": "string",
                "sourceColumn": "CategoryName",
                "hidden": False,
                "usage": "attribute"
            },
            {
                "name": "SalesAmount",
                "defaultName": "Sales Amount",
                "dataType": "decimal",
                "sourceColumn": "SalesAmount",
                "format": "Currency",
                "hidden": False,
                "usage": "fact"
            },
            {
                "name": "Quantity",
                "defaultName": "Quantity",
                "dataType": "integer",
                "sourceColumn": "Quantity",
                "hidden": False,
                "usage": "fact"
            },
            {
                "name": "OrderDate",
                "defaultName": "Order Date",
                "dataType": "date",
                "sourceColumn": "OrderDate",
                "hidden": False,
                "usage": "attribute"
            },
            {
                "name": "CustomerName",
                "defaultName": "Customer Name",
                "dataType": "string",
                "sourceColumn": "CustomerName",
                "hidden": False,
                "usage": "attribute"
            }
        ],
        "measures": [
            {
                "name": "Total_Sales",
                "defaultName": "Total Sales",
                "expression": "SUM([SalesAmount])",
                "format": "Currency",
                "hidden": False
            },
            {
                "name": "Average_Sales",
                "defaultName": "Average Sales",
                "expression": "AVERAGE([SalesAmount])",
                "format": "Currency",
                "hidden": False
            },
            {
                "name": "Total_Quantity",
                "defaultName": "Total Quantity",
                "expression": "SUM([Quantity])",
                "format": "#,##0",
                "hidden": False
            },
            {
                "name": "Sales_Count",
                "defaultName": "Sales Count",
                "expression": "COUNT([SalesAmount])",
                "format": "#,##0",
                "hidden": False
            }
        ],
        "query": "SELECT ProductID, ProductName, CategoryName, SalesAmount, Quantity, OrderDate, CustomerName FROM SalesData",
        "modificationTime": "2024-01-15T10:30:00Z"
    }
    
    # Create mock client if parser not provided
    if parser is None:
        class MockClient:
            def get_module_metadata(self, module_id):
                return sample_module_data
        
        from cognos_migrator.module_parser import CognosModuleParser
        parser = CognosModuleParser(MockClient())
    
    # Parse the sample data
    module_table = parser.parse_module_to_table(sample_module_data)
    
    print(f"📊 Parsed sample module: {module_table.name}")
    print(f"   - Columns: {len(module_table.columns)}")
    print(f"   - Measures: {len(module_table.measures)}")
    
    # Show column details
    print("\n📋 Column Details:")
    for col in module_table.columns:
        print(f"   • {col.name} ({col.data_type}) - {col.summarize_by or 'none'}")
    
    # Show measure details
    print("\n📈 Measure Details:")
    for measure in module_table.measures:
        print(f"   • {measure.name}: {measure.expression}")
    
    # Generate JSON for template
    table_json = parser.generate_table_json(module_table)
    
    # Save JSON to file
    output_dir = Path("output/module_migration")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / f"{module_table.name}_table.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(table_json, f, indent=2)
    
    print(f"\n💾 Saved table JSON to: {json_file}")
    
    # Generate TMDL file using template
    generate_tmdl_file(table_json, output_dir, module_table.name)
    
    print("\n✅ Sample data demo completed successfully!")


def generate_tmdl_file(table_json: dict, output_dir: Path, table_name: str):
    """Generate TMDL file using the Table template"""
    
    try:
        # Create template engine
        template_engine = TemplateEngine("bimigrator/templates")
        
        # Render the table template
        tmdl_content = template_engine.render('table', table_json)
        
        # Save TMDL file
        tmdl_file = output_dir / f"{table_name}.tmdl"
        with open(tmdl_file, 'w', encoding='utf-8') as f:
            f.write(tmdl_content)
        
        print(f"📄 Generated TMDL file: {tmdl_file}")
        
        # Show preview of generated content
        print("\n📖 TMDL Preview (first 20 lines):")
        lines = tmdl_content.split('\n')
        for i, line in enumerate(lines[:20]):
            print(f"   {i+1:2d}: {line}")
        
        if len(lines) > 20:
            print(f"   ... ({len(lines) - 20} more lines)")
        
    except Exception as e:
        print(f"❌ Failed to generate TMDL file: {e}")


def show_usage_instructions():
    """Show instructions for using the module parser"""
    
    print("\n" + "=" * 60)
    print("📚 Usage Instructions")
    print("=" * 60)
    
    print("""
To use the Cognos Module Parser in your own code:

1. Setup Configuration:
   ```python
   from cognos_migrator.config import CognosConfig
   from cognos_migrator.client import CognosClient
   from cognos_migrator.module_parser import CognosModuleParser
   
   config = CognosConfig(
       base_url="your_cognos_url/api/v1",
       username="your_username",
       password="your_password",
       namespace="your_namespace"
   )
   ```

2. Create Client and Parser:
   ```python
   client = CognosClient(config)
   parser = CognosModuleParser(client)
   ```

3. Fetch and Parse Module:
   ```python
   module_data = parser.fetch_module("module_id")
   module_table = parser.parse_module_to_table(module_data)
   table_json = parser.generate_table_json(module_table)
   ```

4. Generate TMDL:
   ```python
   from cognos_migrator.generators import TemplateEngine
   
   template_engine = TemplateEngine("bimigrator/templates")
   tmdl_content = template_engine.render('table', table_json)
   ```

Key Features:
• Automatic data type mapping from Cognos to Power BI
• Support for calculated columns and measures
• Intelligent summarization settings
• M expression generation for data sources
• Full template integration with Jinja2

Environment Variables (.env file):
COGNOS_BASE_URL=http://your-cognos-server:9300/api/v1
COGNOS_USERNAME=your_username
COGNOS_PASSWORD=your_password
COGNOS_NAMESPACE=your_namespace
COGNOS_AUTH_KEY=IBM-BA-Authorization
COGNOS_AUTH_VALUE=your_auth_token
""")


if __name__ == "__main__":
    demo_module_parsing()
    show_usage_instructions()
