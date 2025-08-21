#!/usr/bin/env python3
"""
Test script to verify the expression extraction and conversion fixes.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from cognos_migrator.extractors.expression_extractor import ExpressionExtractor
from cognos_migrator.extractors.data_item_extractor import DataItemExtractor

def test_unified_is_source_column():
    """Test that both extractors use the same is_source_column logic"""
    
    print("Testing unified is_source_column logic...")
    
    # Test cases
    test_cases = [
        # Direct columns (should return True)
        ("[Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]", True, "Direct column reference"),
        ("[Schema].[Table].[Column]", True, "Simple column reference"),
        
        # Calculations (should return False) 
        ("substring(rpad([PRIMARY_LOC], 12, ' '), 1,2) + ' ' +\nsubstring(rpad([PRIMARY_LOC], 12, ' '), 3,2)", False, "Complex calculation with functions"),
        ("[Column1] + [Column2]", False, "Simple arithmetic"),
        ("if([Status] = 'A', 'Active', 'Inactive')", False, "Conditional logic"),
        ("sum([Amount])", False, "Aggregate function"),
        ("([Price] * [Quantity]) + [Tax]", False, "Arithmetic with parentheses"),
    ]
    
    # Initialize extractors
    expr_extractor = ExpressionExtractor()
    data_extractor = DataItemExtractor()
    
    all_passed = True
    
    for expression, expected, description in test_cases:
        expr_result = expr_extractor.is_source_column(expression)
        data_result = data_extractor.is_source_column(expression)
        
        if expr_result == data_result == expected:
            print(f"✅ PASS: {description}")
            print(f"   Expression: {expression[:50]}{'...' if len(expression) > 50 else ''}")
            print(f"   Both extractors returned: {expr_result}")
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Expression: {expression[:50]}{'...' if len(expression) > 50 else ''}")
            print(f"   Expected: {expected}")
            print(f"   ExpressionExtractor: {expr_result}")
            print(f"   DataItemExtractor: {data_result}")
            all_passed = False
        print()
    
    return all_passed

def test_report_queries_processing():
    """Test processing of the actual report_queries.json file"""
    
    print("Testing report queries processing...")
    
    # Load the actual report_queries.json
    queries_path = Path("test_output/report_xml_migration_output_new/extracted/report_queries.json")
    
    if not queries_path.exists():
        print(f"❌ Report queries file not found: {queries_path}")
        return False
    
    with open(queries_path, 'r') as f:
        queries = json.load(f)
    
    expr_extractor = ExpressionExtractor()
    
    print(f"Found {len(queries)} queries in report_queries.json")
    
    for query in queries:
        query_name = query.get('name', 'Unknown')
        data_items = query.get('data_items', [])
        
        print(f"\nProcessing query: {query_name}")
        print(f"  Data items: {len(data_items)}")
        
        calculations_found = 0
        source_columns_found = 0
        
        for item in data_items:
            expression = item.get('expression', '')
            name = item.get('name', '')
            aggregate = item.get('aggregate', '')
            
            is_source = expr_extractor.is_source_column(expression)
            
            if is_source:
                source_columns_found += 1
                print(f"    ✓ Source Column: {name}")
            else:
                calculations_found += 1
                print(f"    🧮 Calculation: {name} (aggregate: {aggregate})")
                print(f"       Expression: {expression[:100]}{'...' if len(expression) > 100 else ''}")
        
        print(f"  Summary: {source_columns_found} source columns, {calculations_found} calculations")
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Expression Extraction Fixes\n")
    print("=" * 60)
    
    # Test 1: Unified is_source_column logic
    test1_passed = test_unified_is_source_column()
    
    print("=" * 60)
    
    # Test 2: Report queries processing
    test2_passed = test_report_queries_processing()
    
    print("=" * 60)
    print("\n📋 Test Summary:")
    
    if test1_passed:
        print("✅ Unified is_source_column logic: PASSED")
    else:
        print("❌ Unified is_source_column logic: FAILED")
    
    if test2_passed:
        print("✅ Report queries processing: PASSED")
    else:
        print("❌ Report queries processing: FAILED")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The fixes look good.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 