#!/usr/bin/env python3
"""
Dynamic test script for real Cognos Analytics API
Fetches actual module data from any provided module ID and generates Table.tmdl
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from cognos_migrator.config import CognosConfig
from cognos_migrator.client import CognosClient
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import TemplateEngine


def setup_logging():
    """Setup detailed logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_real_config():
    """Load real Cognos configuration from environment"""
    config = CognosConfig(
        base_url=os.getenv('COGNOS_BASE_URL'),
        username=os.getenv('COGNOS_USERNAME'),
        password=os.getenv('COGNOS_PASSWORD'),
        namespace=os.getenv('COGNOS_NAMESPACE', 'LDAP'),
        auth_key=os.getenv('COGNOS_AUTH_KEY', 'IBM-BA-Authorization'),
        auth_value=os.getenv('COGNOS_AUTH_VALUE')
    )
    
    # Validate required configuration
    if not config.base_url:
        raise ValueError("COGNOS_BASE_URL environment variable is required")
    if not config.auth_value and not (config.username and config.password):
        raise ValueError("Either COGNOS_AUTH_VALUE or COGNOS_USERNAME/PASSWORD is required")
    
    return config


def test_module_with_real_api(module_id: str, use_real_api: bool = True) -> bool:
    """Test a specific module with real API or fallback data"""
    
    print(f"\n🎯 Testing Module: {module_id}")
    print("=" * 80)
    
    logger = logging.getLogger(__name__)
    
    try:
        if use_real_api:
            # Use real Cognos API
            config = load_real_config()
            client = CognosClient(config)
            
            print(f"📡 Connecting to: {config.base_url}")
            
            # Test connection
            if not client.test_connection():
                print("❌ Failed to connect to Cognos Analytics")
                print("🔄 Falling back to demo data...")
                return test_module_with_real_api(module_id, use_real_api=False)
            
            print("✅ Connected to Cognos Analytics successfully")
            
            # Create parser with real client
            parser = CognosModuleParser(client)
            
            # Fetch real module data
            print(f"📥 Fetching module metadata for: {module_id}")
            try:
                module_data = parser.fetch_module(module_id)
                print("✅ Real module data fetched successfully")
                
            except Exception as e:
                print(f"❌ Failed to fetch module {module_id}: {e}")
                print("🔄 Falling back to demo data...")
                return test_module_with_real_api(module_id, use_real_api=False)
        
        else:
            # Use fallback demo data (for the original module ID)
            if module_id == "iA1C3A12631D84E428678FE1CC2E69C6B":
                module_data = get_fallback_module_data()
                print("📋 Using fallback demo data")
            else:
                print(f"❌ No fallback data available for module: {module_id}")
                return False
            
            # Create mock client for demo
            class MockClient:
                def get_module_metadata(self, mid):
                    return module_data
            
            parser = CognosModuleParser(MockClient())
        
        # Display module information
        print(f"📊 Module ID: {module_data.get('identifier', 'Unknown')}")
        print(f"📋 Module Label: {module_data.get('label', 'Unknown')}")
        print(f"🔄 Version: {module_data.get('version', 'Unknown')}")
        print(f"📅 Last Modified: {module_data.get('lastModified', 'Unknown')}")
        
        # Parse the module data
        print("\n🔄 Parsing module data...")
        module_table = parser.parse_module_to_table(module_data)
        
        print(f"✅ Parsed module: {module_table.name}")
        print(f"   📋 Columns: {len(module_table.columns)}")
        print(f"   📈 Measures: {len(module_table.measures)}")
        
        # Show detailed column information
        print(f"\n📋 Column Details for {module_id}:")
        for i, col in enumerate(module_table.columns[:15]):  # Show first 15
            hidden_status = " (HIDDEN)" if col.is_hidden else ""
            usage_info = f" [{getattr(col, 'annotations', {}).get('CognosUsage', 'N/A')}]"
            print(f"   {i+1:2d}. {col.name} ({col.data_type}) - {col.summarize_by or 'none'}{hidden_status}{usage_info}")
        
        if len(module_table.columns) > 15:
            print(f"   ... and {len(module_table.columns) - 15} more columns")
        
        # Show measure details
        if module_table.measures:
            print(f"\n📈 Measure Details for {module_id}:")
            for i, measure in enumerate(module_table.measures):
                print(f"   {i+1:2d}. {measure.name}: {measure.expression}")
        else:
            print(f"\n📈 No measures found in module {module_id}")
        
        # Generate JSON for template
        print(f"\n🔧 Generating JSON for {module_id}...")
        table_json = parser.generate_table_json(module_table)
        
        # Create output directory
        output_dir = Path(f"output/module_{module_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        json_file = output_dir / f"{module_table.name}_module_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(table_json, f, indent=2)
        
        print(f"💾 Module JSON saved to: {json_file}")
        
        # Generate TMDL file manually (since template might have issues)
        try:
            tmdl_content = generate_manual_tmdl(table_json)
            
            # Save TMDL file
            tmdl_file = output_dir / f"{module_table.name}_module.tmdl"
            with open(tmdl_file, 'w', encoding='utf-8') as f:
                f.write(tmdl_content)
            
            print(f"📄 Module TMDL saved to: {tmdl_file}")
            
            # Show preview
            print(f"\n📖 TMDL Preview for {module_id} (first 15 lines):")
            lines = tmdl_content.split('\n')
            for i, line in enumerate(lines[:15]):
                print(f"   {i+1:2d}: {line}")
            
            if len(lines) > 15:
                print(f"   ... ({len(lines) - 15} more lines)")
            
        except Exception as e:
            logger.error(f"TMDL generation failed for {module_id}: {e}")
            print(f"❌ TMDL generation failed: {e}")
        
        # Save raw module data for inspection
        raw_data_file = output_dir / f"{module_table.name}_raw_data.json"
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(module_data, f, indent=2)
        
        print(f"🔍 Raw module data saved to: {raw_data_file}")
        
        # Analyze data structure
        if 'querySubject' in module_data and module_data['querySubject']:
            query_subject = module_data['querySubject'][0]
            print(f"\n🔍 Data Structure Analysis for {module_id}:")
            print(f"   Table Reference: {query_subject.get('ref', ['N/A'])[0]}")
            print(f"   Table Identifier: {query_subject.get('identifier', 'N/A')}")
            print(f"   Table Label: {query_subject.get('label', 'N/A')}")
            print(f"   Total Query Items: {len(query_subject.get('item', []))}")
            
            # Analyze column types
            usage_counts = {}
            datatype_counts = {}
            for item in query_subject.get('item', []):
                query_item = item.get('queryItem', {})
                usage = query_item.get('usage', 'unknown')
                datatype = query_item.get('highlevelDatatype', 'unknown')
                
                usage_counts[usage] = usage_counts.get(usage, 0) + 1
                datatype_counts[datatype] = datatype_counts.get(datatype, 0) + 1
            
            print(f"   Usage Distribution: {usage_counts}")
            print(f"   Data Type Distribution: {datatype_counts}")
        
        print(f"\n✅ Module {module_id} processed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Module {module_id} processing failed: {e}")
        print(f"❌ Module {module_id} failed: {e}")
        return False
    
    finally:
        # Close client connection if using real API
        if use_real_api:
            try:
                client.close()
            except:
                pass


def generate_manual_tmdl(table_json: dict) -> str:
    """Generate TMDL content manually from table JSON"""
    
    table_name = table_json.get('source_name', 'Unknown_Table')
    columns = table_json.get('columns', [])
    measures = table_json.get('measures', [])
    
    tmdl_lines = [f"table '{table_name}'", ""]
    
    # Add columns
    for col in columns:
        col_name = col.get('source_name', 'Unknown')
        datatype = col.get('datatype', 'string')
        is_hidden = col.get('is_hidden', False)
        summarize_by = col.get('summarize_by', 'none')
        source_column = col.get('source_column', col_name)
        format_string = col.get('format_string')
        annotations = col.get('annotations', {})
        
        tmdl_lines.append(f"\tcolumn '{col_name}'")
        tmdl_lines.append(f"\t\tdataType: {datatype}")
        
        if is_hidden:
            tmdl_lines.append(f"\t\tisHidden")
        
        if summarize_by and summarize_by != 'none':
            tmdl_lines.append(f"\t\tsummarizeBy: {summarize_by}")
        else:
            tmdl_lines.append(f"\t\tsummarizeBy: none")
        
        tmdl_lines.append(f"\t\tsourceColumn: {source_column}")
        
        if format_string:
            tmdl_lines.append(f"\t\tformatString: {format_string}")
        
        tmdl_lines.append("")
        tmdl_lines.append(f"\t\tisDataTypeInferred: True")
        
        # Add annotations
        for key, value in annotations.items():
            if isinstance(value, str) and value.startswith('{'):
                tmdl_lines.append(f"\t\tannotation {key} = {value}")
            else:
                tmdl_lines.append(f"\t\tannotation {key} = {value}")
        
        tmdl_lines.append("")
    
    # Add measures
    for measure in measures:
        measure_name = measure.get('source_name', 'Unknown')
        expression = measure.get('expression', 'SUM([Value])')
        format_string = measure.get('format_string')
        is_hidden = measure.get('is_hidden', False)
        
        tmdl_lines.append(f"\tmeasure '{measure_name}' = ```")
        tmdl_lines.append(f"\t\t{expression}")
        tmdl_lines.append(f"\t```")
        
        if format_string:
            tmdl_lines.append(f"\t\tformatString: {format_string}")
        
        if is_hidden:
            tmdl_lines.append(f"\t\tisHidden")
        
        tmdl_lines.append("")
    
    # Add partition
    tmdl_lines.extend([
        f"\tpartition '{table_name}-partition' = m",
        f"\t\tmode: import",
        f"\t\tsource = ",
        f"\t\t\tlet",
        f"\t\t\t\tSource = Excel.Workbook(File.Contents(\"{table_name}.xlsx\"), null, true),",
        f"\t\t\t\tSheet1_Sheet = Source{{[Item=\"Sheet1\",Kind=\"Sheet\"]}}[Data],",
        f"\t\t\t\t#\"Promoted Headers\" = Table.PromoteHeaders(Sheet1_Sheet, [PromoteAllScalars=true])",
        f"\t\t\tin",
        f"\t\t\t\t#\"Promoted Headers\"",
        "",
        f"\tannotation PBI_ResultType = Table",
        ""
    ])
    
    return '\n'.join(tmdl_lines)


def get_fallback_module_data():
    """Return fallback data for the original module ID"""
    return {
        "version": "17.0",
        "container": "C",
        "use": ["iA1C3A12631D84E428678FE1CC2E69C6B"],
        "identifier": "C_Sample_data_module",
        "label": "Sample Sales Data",
        "querySubject": [{
            "ref": ["M1.Sheet1"],
            "identifier": "Sheet1",
            "label": "sample_sales_data.xlsx",
            "item": [
                {"queryItem": {"identifier": "Order_ID", "label": "Order ID", "datatype": "BIGINT", "highlevelDatatype": "integer", "usage": "identifier", "hidden": False}},
                {"queryItem": {"identifier": "Sales", "label": "Sales", "datatype": "DOUBLE", "highlevelDatatype": "decimal", "usage": "fact", "hidden": False}},
                {"queryItem": {"identifier": "Region", "label": "Region", "datatype": "NVARCHAR(MAX)", "highlevelDatatype": "string", "usage": "identifier", "hidden": False}}
            ]
        }]
    }


def test_multiple_modules(module_ids: List[str], use_real_api: bool = True):
    """Test multiple modules"""
    
    print("🚀 Testing Multiple Cognos Modules with Real API")
    print("=" * 80)
    
    setup_logging()
    
    results = {}
    
    for i, module_id in enumerate(module_ids, 1):
        print(f"\n📋 Processing Module {i}/{len(module_ids)}: {module_id}")
        success = test_module_with_real_api(module_id, use_real_api)
        results[module_id] = success
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY RESULTS")
    print("=" * 80)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    for module_id, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {module_id}: {status}")
    
    return results


def show_usage():
    """Show usage instructions"""
    print("""
🔧 Dynamic Real API Module Tester

Usage:
    python test_dynamic_real_api.py [module_id1] [module_id2] ...

Examples:
    # Test single module
    python test_dynamic_real_api.py iA1C3A12631D84E428678FE1CC2E69C6B
    
    # Test multiple modules
    python test_dynamic_real_api.py iA1C3A12631D84E428678FE1CC2E69C6B i3217A0EE48A7412B9DD2966A92FEE22C
    
    # Test all provided modules
    python test_dynamic_real_api.py

Environment Setup:
    Set these variables in your .env file:
    COGNOS_BASE_URL=https://your-cognos-server.com/api/v1
    COGNOS_USERNAME=your_username
    COGNOS_PASSWORD=your_password
    COGNOS_NAMESPACE=your_namespace

The script will:
1. Connect to your real Cognos Analytics server
2. Fetch actual module metadata for each ID
3. Parse the real module structure
4. Generate JSON mapping for Table.tmdl template
5. Create TMDL files with real data
6. Save all outputs to output/module_{id}/ directories
""")


if __name__ == "__main__":
    # Default module IDs to test
    default_module_ids = [
        "iA1C3A12631D84E428678FE1CC2E69C6B",  # Original
        "i3217A0EE48A7412B9DD2966A92FEE22C",  # New 1
        "i6AD7B8C2951F49438BCAC626F84A09FD",  # New 2
        "i7E09F8F1E6C24E3097D59D1A3CE68685"   # New 3
    ]
    
    # Get module IDs from command line or use defaults
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_usage()
            sys.exit(0)
        module_ids = sys.argv[1:]
    else:
        module_ids = default_module_ids
        print("📋 No module IDs provided, testing all default modules:")
        for mid in module_ids:
            print(f"   - {mid}")
    
    # Check environment
    use_real_api = bool(os.getenv('COGNOS_BASE_URL'))
    if not use_real_api:
        print("⚠️  COGNOS_BASE_URL not found in environment")
        print("🔄 Will use fallback demo data where available")
    
    # Run tests
    results = test_multiple_modules(module_ids, use_real_api)
    
    # Final status
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    if successful == total:
        print(f"\n🎉 ALL MODULES PROCESSED SUCCESSFULLY! ({successful}/{total})")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {successful}/{total} modules processed")
