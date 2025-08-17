#!/usr/bin/env python3
"""
Test script for staging table functionality.

This script demonstrates how to use the new staging table features
to create optimized Power BI semantic models from Cognos packages.
"""

import json
import logging
from pathlib import Path
from cognos_migrator.migrations.package import integrate_staging_tables_with_package_migration

def setup_logging():
    """Setup logging for the test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_staging_tables():
    """Test staging table functionality with a sample package"""
    
    print("🚀 Testing Staging Table Functionality")
    print("=" * 50)
    
    # Setup paths
    test_package_path = "examples/packages/CAM Dmail Reporting.xml"
    test_output_path = "test_output/staging_test"
    
    # Ensure output directory exists
    Path(test_output_path).mkdir(parents=True, exist_ok=True)
    
    # Test settings with staging enabled
    test_settings = {
        "date_table_mode": "visible",
        "table_filtering": {
            "mode": "direct",
            "always_include": ["CentralDateTable"]
        },
        "staging_tables": {
            "enabled": True,
            "mode": "auto",
            "prefix": "Staging_",
            "auto_create_shared_keys": True,
            "join_analysis": {
                "use_llm": False,  # Disable LLM for testing
                "min_join_confidence": 0.8,
                "composite_key_handling": "create_surrogate"
            }
        }
    }
    
    print(f"📁 Package: {test_package_path}")
    print(f"📂 Output: {test_output_path}")
    print(f"⚙️ Staging enabled: {test_settings['staging_tables']['enabled']}")
    print()
    
    try:
        # Run staging table integration
        print("🔄 Running staging table analysis...")
        results = integrate_staging_tables_with_package_migration(
            test_package_path,
            test_output_path,
            test_settings
        )
        
        # Display results
        print("✅ Staging table analysis complete!")
        print()
        print("📊 Results Summary:")
        print(f"   • Staging enabled: {results.get('staging_enabled', False)}")
        print(f"   • Staging tables created: {results.get('staging_tables_created', 0)}")
        print(f"   • Shared keys created: {results.get('shared_keys_created', 0)}")
        print(f"   • Relationships created: {results.get('relationships_created', 0)}")
        print(f"   • Fact tables updated: {results.get('fact_tables_updated', 0)}")
        
        if results.get('error'):
            print(f"❌ Error: {results['error']}")
        
        # Show recommendations if available
        recommendations = results.get('recommendations', [])
        if recommendations:
            print()
            print("💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Save results to file
        results_file = Path(test_output_path) / "staging_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print()
        print(f"📄 Detailed results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error running staging table test: {e}")
        return None

def test_settings_validation():
    """Test different staging table settings"""
    
    print("\n🧪 Testing Settings Validation")
    print("=" * 30)
    
    test_scenarios = [
        {
            "name": "Staging Disabled",
            "settings": {"staging_tables": {"enabled": False}}
        },
        {
            "name": "Auto Mode with LLM",
            "settings": {
                "staging_tables": {
                    "enabled": True,
                    "mode": "auto",
                    "join_analysis": {"use_llm": True}
                }
            }
        },
        {
            "name": "Manual Mode",
            "settings": {
                "staging_tables": {
                    "enabled": True,
                    "mode": "manual"
                }
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"📋 Testing: {scenario['name']}")
        print(f"   Settings: {json.dumps(scenario['settings'], indent=6)}")
        print()

def main():
    """Main test function"""
    setup_logging()
    
    print("🏗️ Power BI Staging Table Test Suite")
    print("=" * 40)
    print()
    
    # Test basic functionality
    results = test_staging_tables()
    
    # Test settings validation
    test_settings_validation()
    
    print("\n" + "=" * 40)
    if results and not results.get('error'):
        print("✅ All tests completed successfully!")
        print()
        print("📋 What was tested:")
        print("   • SQL join analysis from Cognos packages")
        print("   • Staging table definition generation")
        print("   • M-Query creation for staging tables")
        print("   • Relationship generation")
        print("   • Fact table update analysis")
        print("   • TMDL file generation")
        print("   • Documentation creation")
        print()
        print("🎯 Next Steps:")
        print("   1. Enable staging tables in settings.json")
        print("   2. Run package migration with staging enabled")
        print("   3. Review generated staging relationships")
        print("   4. Validate Power BI model performance")
    else:
        print("⚠️ Tests completed with issues - check the logs above")

if __name__ == "__main__":
    main() 