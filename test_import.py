#!/usr/bin/env python3
"""
Test script to verify ModuleSourceExtractor import
"""

import sys
print(f"Python path: {sys.path}")

try:
    from cognos_migrator.extractors.modules.module_source_extractor import ModuleSourceExtractor
    print("✅ ModuleSourceExtractor imported successfully")
    extractor = ModuleSourceExtractor()
    print(f"✅ ModuleSourceExtractor instance created: {extractor}")
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
