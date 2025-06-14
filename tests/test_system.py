#!/usr/bin/env python3
"""
System Test Suite - Production Ready
Tests core functionality of the Cognos to Power BI migration system
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

def test_imports():
    """Test that all core modules can be imported"""
    print("🔍 Testing module imports...")
    
    try:
        from cognos_migrator.client import CognosClient
        from cognos_migrator.config import ConfigManager
        from cognos_migrator.generators import PowerBIProjectGenerator
        from cognos_migrator.migrator import CognosMigrator
        print("✅ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("🔍 Testing configuration...")
    
    try:
        from cognos_migrator.config import ConfigManager
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        migration_config = config_manager.get_migration_config()
        
        print(f"✅ Configuration loaded:")
        print(f"   Cognos URL: {cognos_config.base_url}")
        print(f"   Output Dir: {migration_config.output_directory}")
        print(f"   Template Dir: {migration_config.template_directory}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_templates():
    """Test that templates are available"""
    print("🔍 Testing templates...")
    
    template_dir = Path("bimigrator/templates")
    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        return False
    
    required_templates = [
        "database.tmdl", "model.tmdl", "Table.tmdl", "relationship.tmdl",
        "expressions.tmdl", "culture.tmdl", "pbixproj.json", "report.json"
    ]
    
    missing_templates = []
    for template in required_templates:
        if not (template_dir / template).exists():
            missing_templates.append(template)
    
    if missing_templates:
        print(f"❌ Missing templates: {missing_templates}")
        return False
    
    print(f"✅ All {len(required_templates)} required templates found")
    return True

def test_output_directory():
    """Test output directory access"""
    print("🔍 Testing output directory...")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Test write access
    test_file = output_dir / "test_write.tmp"
    try:
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink()
        print("✅ Output directory is writable")
        return True
    except Exception as e:
        print(f"❌ Cannot write to output directory: {e}")
        return False

def test_dependencies():
    """Test that required dependencies are installed"""
    print("🔍 Testing dependencies...")
    
    required_packages = [
        ("requests", "requests"),
        ("jinja2", "jinja2"), 
        ("python-dotenv", "dotenv")
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def main():
    """Run all system tests"""
    print("🧪 COGNOS TO POWER BI MIGRATION - SYSTEM TESTS")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("Templates", test_templates),
        ("Output Directory", test_output_directory),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
        else:
            print("🔧 Fix this issue before proceeding")
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for migration.")
        print()
        print("💡 Next steps:")
        print("   1. Configure your .env file with Cognos credentials")
        print("   2. Run: python run_demo.py")
        print("   3. Or run: python main.py --help")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)