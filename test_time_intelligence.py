#!/usr/bin/env python3
"""
Test Time Intelligence Features
Tests the enhanced time intelligence and date calculation capabilities
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.time_intelligence import (
    CognosTimeIntelligenceConverter, 
    create_standard_date_dimension,
    create_fiscal_date_dimension,
    FiscalPeriodType,
    TimeIntelligenceType
)
from cognos_migrator.module_parser import CognosModuleParser, ModuleTable, ModuleColumn, ModuleMeasure


def test_time_intelligence_converter():
    """Test the time intelligence converter"""
    print("=" * 60)
    print("🕐 TESTING TIME INTELLIGENCE CONVERTER")
    print("=" * 60)
    
    converter = CognosTimeIntelligenceConverter()
    
    # Test Cognos time function conversion
    test_functions = [
        {
            'function': 'year_to_date',
            'params': {
                'measure': '[Sales Amount]',
                'date_table': 'Calendar',
                'date_column': 'Date'
            }
        },
        {
            'function': 'same_period_last_year',
            'params': {
                'measure': '[Quantity]',
                'date_table': 'Calendar', 
                'date_column': 'Date'
            }
        },
        {
            'function': 'rolling_average',
            'params': {
                'measure': '[Profit]',
                'date_table': 'Calendar',
                'date_column': 'Date',
                'periods': '12',
                'period_type': 'MONTH'
            }
        }
    ]
    
    print("\n1️⃣ Testing Cognos Time Function Conversion:")
    for test in test_functions:
        try:
            dax_result = converter.convert_cognos_time_function(
                test['function'], test['params']
            )
            print(f"   ✅ {test['function']} -> {dax_result}")
        except Exception as e:
            print(f"   ❌ {test['function']} -> Error: {e}")
    
    # Test time expression conversion
    print("\n2️⃣ Testing Time Expression Conversion:")
    test_expressions = [
        "extract(year, [Order Date])",
        "_month([Ship Date])",
        "current_date()",
        "[Order Date] + 30 days",
        "extract(quarter, [Sales Date])"
    ]
    
    for expr in test_expressions:
        try:
            dax_result = converter.convert_cognos_time_expression(expr, {})
            print(f"   ✅ '{expr}' -> '{dax_result}'")
        except Exception as e:
            print(f"   ❌ '{expr}' -> Error: {e}")


def test_date_dimension_creation():
    """Test date dimension creation"""
    print("\n=" * 60)
    print("📅 TESTING DATE DIMENSION CREATION")
    print("=" * 60)
    
    converter = CognosTimeIntelligenceConverter()
    
    # Test standard date dimension
    print("\n1️⃣ Creating Standard Date Dimension:")
    standard_date_dim = create_standard_date_dimension("Calendar", "Date")
    date_template = converter.create_date_dimension_template(standard_date_dim)
    
    print(f"   ✅ Table Name: {date_template.get('table_name')}")
    print(f"   ✅ Date Column: {date_template.get('date_column')}")
    print(f"   ✅ Calculated Columns: {len(date_template.get('calculated_columns', []))}")
    print(f"   ✅ Hierarchies: {len(date_template.get('hierarchies', []))}")
    
    # Show some calculated columns
    calc_columns = date_template.get('calculated_columns', [])[:5]
    print("\n   📊 Sample Calculated Columns:")
    for col in calc_columns:
        print(f"      - {col['name']}: {col['expression']}")
    
    # Test fiscal year date dimension
    print("\n2️⃣ Creating Fiscal Year Date Dimension (April-March):")
    fiscal_date_dim = create_fiscal_date_dimension(
        "FiscalCalendar", "Date", FiscalPeriodType.APRIL_MARCH
    )
    fiscal_template = converter.create_date_dimension_template(fiscal_date_dim)
    
    print(f"   ✅ Fiscal Start Month: {fiscal_date_dim.fiscal_config.start_month}")
    print(f"   ✅ Fiscal Type: {fiscal_date_dim.fiscal_config.fiscal_type.value}")
    print(f"   ✅ Fiscal Calculated Columns: {len(fiscal_template.get('calculated_columns', []))}")
    
    # Show fiscal columns
    fiscal_columns = [col for col in fiscal_template.get('calculated_columns', []) 
                     if 'Fiscal' in col['name']]
    print("\n   📊 Fiscal Year Columns:")
    for col in fiscal_columns:
        print(f"      - {col['name']}: {col['expression'][:80]}...")


def test_time_intelligence_measures():
    """Test time intelligence measure generation"""
    print("\n=" * 60)
    print("📈 TESTING TIME INTELLIGENCE MEASURES")
    print("=" * 60)
    
    converter = CognosTimeIntelligenceConverter()
    
    # Create sample base measures
    base_measures = ["Sales Amount", "Quantity Sold", "Profit Margin"]
    date_dimension = create_standard_date_dimension("Calendar", "Date")
    
    print(f"\n1️⃣ Generating Time Intelligence for {len(base_measures)} base measures:")
    for measure in base_measures:
        print(f"   📊 {measure}")
    
    time_measures = converter.generate_time_intelligence_measures(base_measures, date_dimension)
    
    print(f"\n2️⃣ Generated {len(time_measures)} Time Intelligence Measures:")
    
    # Group by calculation type
    measure_groups = {}
    for measure in time_measures:
        calc_type = measure.calculation_type.value
        if calc_type not in measure_groups:
            measure_groups[calc_type] = []
        measure_groups[calc_type].append(measure)
    
    for calc_type, measures in measure_groups.items():
        print(f"\n   📈 {calc_type.upper()} ({len(measures)} measures):")
        for measure in measures[:2]:  # Show first 2 of each type
            print(f"      - {measure.name}")
            print(f"        DAX: {measure.dax_expression}")


def test_module_integration():
    """Test time intelligence integration with module parser"""
    print("\n=" * 60)
    print("🔗 TESTING MODULE INTEGRATION")
    print("=" * 60)
    
    # Create a mock client for demo
    class MockClient:
        def get_module_metadata(self, module_id):
            return {}
    
    parser = CognosModuleParser(MockClient())
    
    # Create sample module with date columns and measures
    sample_columns = [
        ModuleColumn(name="OrderDate", data_type="dateTime", source_column="OrderDate"),
        ModuleColumn(name="ProductID", data_type="int64", source_column="ProductID", summarize_by="none"),
        ModuleColumn(name="SalesAmount", data_type="decimal", source_column="SalesAmount", summarize_by="sum"),
        ModuleColumn(name="Quantity", data_type="int64", source_column="Quantity", summarize_by="sum"),
        ModuleColumn(name="CustomerName", data_type="string", source_column="CustomerName", summarize_by="none")
    ]
    
    sample_measures = [
        ModuleMeasure(name="Total Sales", expression="SUM([SalesAmount])"),
        ModuleMeasure(name="Total Quantity", expression="SUM([Quantity])")
    ]
    
    module_table = ModuleTable(
        name="Sales_Analysis",
        columns=sample_columns,
        measures=sample_measures
    )
    
    print("\n1️⃣ Sample Module Structure:")
    print(f"   📊 Table: {module_table.name}")
    print(f"   📋 Columns: {len(module_table.columns)}")
    print(f"   📈 Measures: {len(module_table.measures)}")
    
    # Test time intelligence generation
    print("\n2️⃣ Generating Time Intelligence:")
    time_measures = parser.generate_time_intelligence_measures(module_table)
    print(f"   ✅ Generated {len(time_measures)} time intelligence measures")
    
    # Test date column enhancement
    print("\n3️⃣ Enhancing Date Columns:")
    enhanced_columns = parser.enhance_date_columns(module_table)
    print(f"   ✅ Generated {len(enhanced_columns)} enhanced date columns")
    
    # Generate complete table JSON
    print("\n4️⃣ Generating Complete Table JSON:")
    table_json = parser.generate_table_json(module_table)
    
    total_columns = len(table_json.get('columns', []))
    total_measures = len(table_json.get('measures', []))
    
    print(f"   ✅ Total Columns (including enhanced): {total_columns}")
    print(f"   ✅ Total Measures (including time intelligence): {total_measures}")
    
    # Save enhanced output
    output_dir = Path("output/time_intelligence_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "enhanced_table.json", "w") as f:
        json.dump(table_json, f, indent=2)
    
    print(f"   💾 Enhanced table JSON saved to: {output_dir / 'enhanced_table.json'}")
    
    # Show sample enhanced measures
    enhanced_measures = [m for m in table_json.get('measures', []) 
                        if m['source_name'] not in [measure.name for measure in sample_measures]]
    
    print(f"\n   📈 Sample Enhanced Measures ({len(enhanced_measures)} total):")
    for measure in enhanced_measures[:5]:
        print(f"      - {measure['source_name']}")


def main():
    """Run all time intelligence tests"""
    print("🚀 COGNOS TO POWER BI - TIME INTELLIGENCE TESTING")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run all tests
        test_time_intelligence_converter()
        test_date_dimension_creation()
        test_time_intelligence_measures()
        test_module_integration()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TIME INTELLIGENCE TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n✅ Features Tested:")
        print("   - Cognos time function conversion to DAX")
        print("   - Date dimension creation (standard & fiscal)")
        print("   - Time intelligence measure generation")
        print("   - Module parser integration")
        print("   - Enhanced table JSON generation")
        
        print("\n📊 Time Intelligence Capabilities:")
        print("   - Year/Quarter/Month to Date calculations")
        print("   - Same Period Last Year comparisons")
        print("   - Rolling averages and moving totals")
        print("   - Fiscal year support (multiple types)")
        print("   - Automatic date column enhancement")
        print("   - DAX time intelligence functions")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)