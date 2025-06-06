#!/usr/bin/env python3
"""
Simple test script to verify the Cognos to Power BI migration system
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")
    
    try:
        from cognos_migrator.config import MigrationConfig
        print("✓ Config module imported successfully")
        
        from cognos_migrator.models import (
            DataType, CognosReport, PowerBIProject, DataModel, 
            Table, Column, Relationship, Measure, Report, ReportPage
        )
        print("✓ Models module imported successfully")
        
        from cognos_migrator.client import CognosClient
        print("✓ Client module imported successfully")
        
        from cognos_migrator.parsers import CognosReportConverter
        print("✓ Parsers module imported successfully")
        
        from cognos_migrator.generators import PowerBIProjectGenerator, DocumentationGenerator
        print("✓ Generators module imported successfully")
        
        from cognos_migrator.migrator import CognosToPowerBIMigrator, MigrationBatch
        print("✓ Migrator module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from cognos_migrator.config import MigrationConfig, CognosConfig, ConfigManager
        
        # Test MigrationConfig with default values
        migration_config = MigrationConfig(
            output_directory="output",
            template_directory="bimigrator/templates",
            preserve_structure=True,
            include_metadata=True,
            generate_documentation=True
        )
        
        # Test CognosConfig
        cognos_config = CognosConfig(
            base_url="http://localhost:9300",
            auth_key="IBM-BA-Authorization",
            auth_value="test_auth_value"
        )
        
        # Test ConfigManager
        config_manager = ConfigManager()
        
        print(f"✓ Configuration created successfully")
        print(f"  - Template Directory: {migration_config.template_directory}")
        print(f"  - Output Directory: {migration_config.output_directory}")
        print(f"  - Cognos Base URL: {cognos_config.base_url}")
        print(f"  - Config Manager initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_models():
    """Test model creation"""
    print("\nTesting models...")
    
    try:
        from cognos_migrator.models import DataType, Table, Column, DataModel
        from datetime import datetime
        
        # Create a test column
        column = Column(
            name="test_column",
            data_type=DataType.STRING,
            source_column="source_col"
        )
        
        # Create a test table
        table = Table(
            name="test_table",
            columns=[column],
            partition_mode="Import"
        )
        
        # Create a test data model
        model = DataModel(
            name="test_model",
            compatibility_level=1600,
            culture="en-US",
            tables=[table],
            relationships=[],
            measures=[]
        )
        
        print("✓ Models created successfully")
        print(f"  - Table: {table.name} with {len(table.columns)} columns")
        print(f"  - Model: {model.name} with {len(model.tables)} tables")
        
        return True
        
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False

def test_template_directory():
    """Test template directory exists"""
    print("\nTesting template directory...")
    
    template_dir = Path("bimigrator/templates")
    
    if template_dir.exists():
        print(f"✓ Template directory exists: {template_dir}")
        
        # List template files
        template_files = list(template_dir.glob("*.tmdl")) + list(template_dir.glob("*.json"))
        print(f"  - Found {len(template_files)} template files")
        
        for template_file in template_files:
            print(f"    - {template_file.name}")
        
        return True
    else:
        print(f"✗ Template directory not found: {template_dir}")
        return False

def main():
    """Run all tests"""
    print("=== Cognos to Power BI Migration System Test ===\n")
    
    tests = [
        test_imports,
        test_configuration,
        test_models,
        test_template_directory
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
