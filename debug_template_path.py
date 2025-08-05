#!/usr/bin/env python3
"""
Debug script to test template directory path resolution
"""

import os
import logging
from pathlib import Path

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# Test template directory path construction
print("=== Template Directory Path Debug ===")

# Test 1: Basic path construction from enhanced_main.py
enhanced_main_path = Path(__file__).parent / "cognos_migrator" / "enhanced_main.py"
template_path_1 = str(enhanced_main_path.parent / "templates")
print(f"1. enhanced_main.py template path: {template_path_1}")
print(f"   Exists: {Path(template_path_1).exists()}")

# Test 2: Actual template directory
actual_template_dir = Path(__file__).parent / "cognos_migrator" / "templates"
print(f"2. Actual template directory: {actual_template_dir}")
print(f"   Exists: {actual_template_dir.exists()}")

# Test 3: Check if template engine gets initialized correctly
try:
    from cognos_migrator.generators.template_engine import TemplateEngine
    
    print(f"\n=== Testing TemplateEngine initialization ===")
    
    # Test with correct path
    try:
        engine = TemplateEngine(str(actual_template_dir))
        print(f"SUCCESS: TemplateEngine initialized with {actual_template_dir}")
        print(f"Engine template_directory: {engine.template_directory}")
    except Exception as e:
        print(f"ERROR: TemplateEngine failed with {actual_template_dir}: {e}")
    
    # Test with path that would cause duplication
    bad_path = str(actual_template_dir / "templates")
    print(f"\n=== Testing with doubled template path ===")
    print(f"Testing path: {bad_path}")
    print(f"Path exists: {Path(bad_path).exists()}")
    
    try:
        engine = TemplateEngine(bad_path)
        print(f"UNEXPECTED: TemplateEngine worked with doubled path: {bad_path}")
    except Exception as e:
        print(f"EXPECTED ERROR: TemplateEngine failed with doubled path: {e}")

except ImportError as e:
    print(f"Import error: {e}")

# Test 4: Check MigrationConfig construction
print(f"\n=== Testing MigrationConfig construction ===")
try:
    from cognos_migrator.config import MigrationConfig
    
    test_config = MigrationConfig(
        output_directory="./test_output",
        template_directory=str(actual_template_dir)
    )
    
    print(f"MigrationConfig template_directory: {test_config.template_directory}")
    print(f"Template directory exists: {Path(test_config.template_directory).exists()}")
    
except ImportError as e:
    print(f"Import error: {e}")

# Test 5: Check EnhancedMigrationConfig
print(f"\n=== Testing EnhancedMigrationConfig construction ===")
try:
    from cognos_migrator.config.fallback_config import EnhancedMigrationConfig, ConfigurationManager
    
    # Test default enhanced config
    enhanced_config = EnhancedMigrationConfig()
    print(f"Default EnhancedMigrationConfig template_directory: '{enhanced_config.template_directory}'")
    
    # Test config manager
    config_manager = ConfigurationManager()
    config = config_manager.get_config()
    print(f"ConfigurationManager config template_directory: '{config.template_directory}'")
    
except ImportError as e:
    print(f"Import error: {e}")

print(f"\n=== Summary ===")
print(f"Expected template directory: {actual_template_dir}")
print(f"Directory exists: {actual_template_dir.exists()}")
if actual_template_dir.exists():
    template_files = list(actual_template_dir.glob("*.tmdl")) + list(actual_template_dir.glob("*.json"))
    print(f"Template files found: {len(template_files)}")
    for f in template_files[:5]:  # Show first 5
        print(f"  - {f.name}")