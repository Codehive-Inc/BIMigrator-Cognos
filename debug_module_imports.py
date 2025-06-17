#!/usr/bin/env python3
"""
Debug script to investigate module import issues
"""

import sys
import importlib
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Print Python path
logger.info(f"Python path: {sys.path}")

# Check if module files exist
module_path = os.path.join("cognos_migrator", "extractors", "modules", "module_source_extractor.py")
logger.info(f"Checking if {module_path} exists: {os.path.exists(module_path)}")

# Try different import approaches
logger.info("Attempting imports with different approaches:")

# Approach 1: Direct import
try:
    logger.info("Approach 1: Direct import")
    from cognos_migrator.extractors.modules.module_source_extractor import ModuleSourceExtractor
    logger.info("✅ Direct import successful")
except ImportError as e:
    logger.error(f"❌ Direct import failed: {e}")

# Approach 2: Import module then class
try:
    logger.info("Approach 2: Import module then class")
    import cognos_migrator.extractors.modules.module_source_extractor
    ModuleSourceExtractor = cognos_migrator.extractors.modules.module_source_extractor.ModuleSourceExtractor
    logger.info("✅ Module import successful")
except ImportError as e:
    logger.error(f"❌ Module import failed: {e}")

# Approach 3: Dynamic import
try:
    logger.info("Approach 3: Dynamic import")
    module = importlib.import_module("cognos_migrator.extractors.modules.module_source_extractor")
    ModuleSourceExtractor = getattr(module, "ModuleSourceExtractor")
    logger.info("✅ Dynamic import successful")
except ImportError as e:
    logger.error(f"❌ Dynamic import failed: {e}")
except AttributeError as e:
    logger.error(f"❌ Class not found in module: {e}")

# Approach 4: Relative import
try:
    logger.info("Approach 4: Relative import")
    from .extractors.modules.module_source_extractor import ModuleSourceExtractor
    logger.info("✅ Relative import successful")
except ImportError as e:
    logger.error(f"❌ Relative import failed: {e}")
except ValueError as e:
    logger.error(f"❌ Relative import error: {e}")

# Approach 5: Import from main module
try:
    logger.info("Approach 5: Import from main module")
    from cognos_migrator.main import ModuleSourceExtractor
    logger.info("✅ Main module import successful")
except ImportError as e:
    logger.error(f"❌ Main module import failed: {e}")

# Try to create the module migrator
try:
    logger.info("Attempting to create CognosModuleMigrator")
    from cognos_migrator.module_migrator import CognosModuleMigrator
    from cognos_migrator.config import ConfigManager
    
    config_manager = ConfigManager()
    config = config_manager.get_migration_config()
    
    module_migrator = CognosModuleMigrator(config)
    logger.info("✅ CognosModuleMigrator created successfully")
except Exception as e:
    logger.error(f"❌ Error creating CognosModuleMigrator: {e}")

logger.info("Debug complete")
