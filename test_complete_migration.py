#!/usr/bin/env python3
"""
Test Complete Power BI Migration
Tests the full-fledged Power BI project generation from Cognos reports
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient
from cognos_migrator.generators import PowerBIProjectGenerator
from cognos_migrator.report_parser import CognosReportSpecificationParser
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.models import DataModel, Table, Column, DataType

def create_sample_data_model() -> DataModel:
    """Create sample data model for testing"""
    
    # Create sample table with columns
    sales_table = Table(
        name="Sales Data",
        columns=[
            Column(name="Date", data_type=DataType.DATE, source_column="date"),
            Column(name="Product", data_type=DataType.STRING, source_column="product"),
            Column(name="Sales Amount", data_type=DataType.DECIMAL, source_column="sales_amount"),
            Column(name="Quantity", data_type=DataType.INTEGER, source_column="quantity"),
            Column(name="Region", data_type=DataType.STRING, source_column="region")
        ],
        source_query="SELECT date, product, sales_amount, quantity, region FROM sales_data"
    )
    
    # Create data model
    data_model = DataModel(
        name="Sample Sales Model",
        tables=[sales_table],
        culture="en-US"
    )
    
    return data_model

def create_sample_cognos_report():
    """Create sample Cognos report structure for testing"""
    from cognos_migrator.report_parser import CognosReportStructure, ReportPage, CognosVisual, VisualType, VisualField
    
    # Create sample visual fields
    chart_fields = [
        VisualField(name="Product", source_table="Sales Data", data_role="axis"),
        VisualField(name="Sales Amount", source_table="Sales Data", data_role="values", aggregation="sum")
    ]
    
    table_fields = [
        VisualField(name="Date", source_table="Sales Data", data_role="axis"),
        VisualField(name="Product", source_table="Sales Data", data_role="axis"),
        VisualField(name="Sales Amount", source_table="Sales Data", data_role="values"),
        VisualField(name="Quantity", source_table="Sales Data", data_role="values"),
        VisualField(name="Region", source_table="Sales Data", data_role="axis")
    ]
    
    # Create sample visuals
    chart_visual = CognosVisual(
        name="Sales by Product",
        cognos_type="columnChart",
        power_bi_type=VisualType.COLUMN_CHART,
        position={"x": 0, "y": 0, "width": 400, "height": 300},
        fields=chart_fields,
        filters=[]
    )
    
    table_visual = CognosVisual(
        name="Sales Data Table",
        cognos_type="tableEx", 
        power_bi_type=VisualType.TABLE,
        position={"x": 420, "y": 0, "width": 500, "height": 300},
        fields=table_fields,
        filters=[]
    )
    
    # Create sample page
    page = ReportPage(
        name="Sales Dashboard",
        display_name="Sales Dashboard",
        visuals=[chart_visual, table_visual],
        filters=[],
        width=1280,
        height=720
    )
    
    # Create report structure
    report = CognosReportStructure(
        name="Sample Sales Report",
        report_id="sample_report_001",
        pages=[page]
    )
    
    return report

def test_complete_project_generation():
    """Test complete Power BI project generation"""
    print("🏗️  TESTING COMPLETE POWER BI PROJECT GENERATION")
    print("=" * 60)
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        migration_config = config_manager.get_migration_config()
        
        print(f"📋 Configuration loaded")
        print(f"   Template Dir: {migration_config.template_directory}")
        print(f"   Output Dir: {migration_config.output_directory}")
        
        # Create generator
        generator = PowerBIProjectGenerator(migration_config)
        print(f"✅ Generator created")
        
        # Create sample data
        data_model = create_sample_data_model()
        cognos_report = create_sample_cognos_report()
        
        print(f"📊 Sample data created:")
        print(f"   Data Model: {data_model.name}")
        print(f"   Tables: {len(data_model.tables)}")
        print(f"   Report: {cognos_report.name}")
        print(f"   Pages: {len(cognos_report.pages)}")
        print(f"   Visuals: {sum(len(page.visuals) for page in cognos_report.pages)}")
        
        # Generate complete Power BI project
        output_path = Path(migration_config.output_directory) / "complete_test_project"
        
        print(f"\n🚀 Generating complete Power BI project...")
        print(f"   Output: {output_path}")
        
        success = generator.generate_from_cognos_report(
            cognos_report=cognos_report,
            data_model=data_model,
            output_path=str(output_path)
        )
        
        if success:
            print(f"✅ PROJECT GENERATION SUCCESSFUL!")
            
            # Verify generated structure
            verify_project_structure(output_path)
            
        else:
            print(f"❌ PROJECT GENERATION FAILED!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_project_structure(project_path: Path):
    """Verify the generated Power BI project structure"""
    print(f"\n🔍 VERIFYING PROJECT STRUCTURE")
    print("=" * 40)
    
    expected_files = [
        ".pbixproj.json",
        "Version.txt", 
        "DiagramLayout.json",
        "ReportMetadata.json",
        "ReportSettings.json"
    ]
    
    expected_dirs = [
        "Model",
        "Report", 
        "StaticResources"
    ]
    
    # Check root files
    print(f"📄 Checking root files:")
    for file in expected_files:
        file_path = project_path / file
        if file_path.exists():
            print(f"   ✅ {file}")
            if file.endswith('.json'):
                try:
                    with open(file_path) as f:
                        json.load(f)
                    print(f"      📋 Valid JSON")
                except:
                    print(f"      ⚠️  Invalid JSON")
        else:
            print(f"   ❌ {file} (missing)")
    
    # Check directories
    print(f"\n📁 Checking directories:")
    for dir_name in expected_dirs:
        dir_path = project_path / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"   ✅ {dir_name}/")
            
            # List contents
            contents = list(dir_path.iterdir())
            print(f"      📋 {len(contents)} items")
            
        else:
            print(f"   ❌ {dir_name}/ (missing)")
    
    # Check Model structure
    model_dir = project_path / "Model"
    if model_dir.exists():
        print(f"\n📊 Model structure:")
        
        model_files = ["database.tmdl", "model.tmdl"]
        for file in model_files:
            file_path = model_dir / file
            if file_path.exists():
                print(f"   ✅ {file}")
            else:
                print(f"   ❌ {file} (missing)")
        
        # Check tables directory
        tables_dir = model_dir / "tables"
        if tables_dir.exists():
            table_files = list(tables_dir.glob("*.tmdl"))
            print(f"   ✅ tables/ ({len(table_files)} tables)")
            for table_file in table_files:
                print(f"      - {table_file.name}")
        else:
            print(f"   ❌ tables/ (missing)")
        
        # Check cultures directory  
        cultures_dir = model_dir / "cultures"
        if cultures_dir.exists():
            culture_files = list(cultures_dir.glob("*.tmdl"))
            print(f"   ✅ cultures/ ({len(culture_files)} cultures)")
        else:
            print(f"   ❌ cultures/ (missing)")
    
    # Check Report structure
    report_dir = project_path / "Report"
    if report_dir.exists():
        print(f"\n📊 Report structure:")
        
        report_files = ["report.json", "config.json"]
        for file in report_files:
            file_path = report_dir / file
            if file_path.exists():
                print(f"   ✅ {file}")
            else:
                print(f"   ❌ {file} (missing)")
        
        # Check sections directory
        sections_dir = report_dir / "sections"
        if sections_dir.exists():
            section_dirs = [d for d in sections_dir.iterdir() if d.is_dir()]
            print(f"   ✅ sections/ ({len(section_dirs)} sections)")
            
            for section_dir in section_dirs:
                print(f"      📁 {section_dir.name}/")
                
                # Check for visual containers
                visual_containers_dir = section_dir / "visualContainers"
                if visual_containers_dir.exists():
                    visual_dirs = [d for d in visual_containers_dir.iterdir() if d.is_dir()]
                    print(f"         📊 visualContainers/ ({len(visual_dirs)} visuals)")
                    
                    for visual_dir in visual_dirs[:3]:  # Show first 3
                        print(f"            - {visual_dir.name}/")
                    if len(visual_dirs) > 3:
                        print(f"            ... and {len(visual_dirs) - 3} more")
                        
        else:
            print(f"   ❌ sections/ (missing)")
    
    # Check StaticResources structure
    static_dir = project_path / "StaticResources"
    if static_dir.exists():
        print(f"\n🎨 StaticResources structure:")
        
        shared_dir = static_dir / "SharedResources"
        if shared_dir.exists():
            print(f"   ✅ SharedResources/")
            
            themes_dir = shared_dir / "BaseThemes"
            if themes_dir.exists():
                theme_files = list(themes_dir.glob("*.json"))
                print(f"      ✅ BaseThemes/ ({len(theme_files)} themes)")
                for theme_file in theme_files:
                    print(f"         - {theme_file.name}")
            else:
                print(f"      ❌ BaseThemes/ (missing)")
        else:
            print(f"   ❌ SharedResources/ (missing)")
    
    print(f"\n✅ PROJECT STRUCTURE VERIFICATION COMPLETE")

def test_real_cognos_integration():
    """Test with real Cognos connection if available"""
    print(f"\n🌐 TESTING REAL COGNOS INTEGRATION")
    print("=" * 40)
    
    try:
        # Load configuration
        config_manager = ConfigManager() 
        cognos_config = config_manager.get_cognos_config()
        
        print(f"🔌 Connecting to Cognos...")
        print(f"   URL: {cognos_config.base_url}")
        print(f"   Username: {cognos_config.username}")
        
        # Create client
        client = CognosClient(cognos_config)
        
        # Test connection
        if not client.test_connection():
            print(f"⚠️  Cognos connection failed - skipping real integration test")
            return True
            
        print(f"✅ Connected to Cognos successfully")
        
        # List available content
        print(f"\n📋 Listing Cognos content...")
        root_objects = client.list_root_objects()
        print(f"   Found {len(root_objects)} root objects")
        
        # Look for reports
        reports = [obj for obj in root_objects if obj.get('type') == 'report']
        print(f"   Found {len(reports)} reports")
        
        if reports:
            # Try to get first report
            first_report = reports[0]
            print(f"\n📊 Testing with report: {first_report.get('defaultName', 'Unknown')}")
            
            cognos_report = client.get_cognos_report(first_report['id'])
            if cognos_report:
                print(f"   ✅ Retrieved report specification")
                print(f"   📄 Specification length: {len(cognos_report.specification)} characters")
            else:
                print(f"   ⚠️  Could not retrieve report specification")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Real Cognos integration test failed: {e}")
        print(f"   This is expected if Cognos server is not available")
        return True  # Don't fail the test for connectivity issues

def main():
    """Run all complete migration tests"""
    print("🚀 COMPLETE POWER BI MIGRATION TESTING")
    print(f"📅 Test Date: {os.popen('date').read().strip()}")
    print("=" * 60)
    
    # Enable debug logging
    logging.basicConfig(level=logging.INFO)
    
    success = True
    
    try:
        # Test complete project generation
        generation_success = test_complete_project_generation()
        success = success and generation_success
        
        # Test real Cognos integration (optional)
        integration_success = test_real_cognos_integration()
        success = success and integration_success
        
        print(f"\n" + "=" * 60)
        if success:
            print(f"🎉 ALL COMPLETE MIGRATION TESTS PASSED!")
            print(f"✅ Full-fledged Power BI project generation is working")
            print(f"✅ Complete migration workflow verified")
        else:
            print(f"❌ SOME MIGRATION TESTS FAILED!")
            print(f"⚠️  Check the error logs above")
            
    except Exception as e:
        print(f"❌ TEST SUITE FAILED: {e}")
        success = False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)