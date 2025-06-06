#!/usr/bin/env python3
"""
Test script to verify installation and basic functionality
"""
import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    try:
        import requests
        print("✅ requests imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        return False
    
    try:
        import pydantic
        print("✅ pydantic imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pydantic: {e}")
        return False
    
    try:
        import jinja2
        print("✅ jinja2 imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import jinja2: {e}")
        return False
    
    try:
        import lxml
        print("✅ lxml imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import lxml: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import python-dotenv: {e}")
        return False
    
    return True

def test_cognos_migrator():
    """Test if our cognos_migrator module can be imported"""
    try:
        # Test basic imports without the generators module first
        from cognos_migrator.models import CognosReport, PowerBIProject
        print("✅ cognos_migrator.models imported successfully")
        
        from cognos_migrator.config import ConfigManager
        print("✅ cognos_migrator.config imported successfully")
        
        from cognos_migrator.client import CognosClient
        print("✅ cognos_migrator.client imported successfully")
        
        from cognos_migrator.parsers import CognosReportParser
        print("✅ cognos_migrator.parsers imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import cognos_migrator: {e}")
        return False

def main():
    """Main test function"""
    print("Testing package installation and basic functionality...")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print("-" * 50)
    
    # Test package imports
    if not test_imports():
        print("\n❌ Package import tests failed")
        return 1
    
    print("\n" + "-" * 50)
    
    # Test cognos_migrator module
    if not test_cognos_migrator():
        print("\n❌ cognos_migrator module tests failed")
        return 1
    
    print("\n✅ All tests passed! Installation appears to be working.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
