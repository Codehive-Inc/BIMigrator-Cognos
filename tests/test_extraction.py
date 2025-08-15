#!/usr/bin/env python3
"""
Script to test package extraction with different namespace versions.
"""

import os
import sys
import logging
from pathlib import Path
from cognos_migrator.extractors.packages.consolidated_package_extractor import ConsolidatedPackageExtractor

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_package_extraction(package_file_path, output_dir):
    """Test extraction of a package file
    
    Args:
        package_file_path: Path to the package XML file
        output_dir: Directory to save extracted data
        
    Returns:
        True if extraction succeeded, False otherwise
    """
    try:
        logger.info(f"Testing extraction of {package_file_path}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create extractor
        extractor = ConsolidatedPackageExtractor(logger=logger)
        
        # Extract package
        result = extractor.extract_package(package_file_path, str(output_path))
        
        # Check if extraction succeeded
        if result:
            logger.info(f"Extraction succeeded for {package_file_path}")
            logger.info(f"Output saved to {output_path}")
            return True
        else:
            logger.error(f"Extraction failed for {package_file_path}")
            return False
    
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        return False

def main():
    # Check if package file path is provided
    if len(sys.argv) < 2:
        print("Usage: python test_extraction.py <package_file_path> [output_dir]")
        return 1
    
    # Get package file path
    package_file_path = sys.argv[1]
    
    # Get output directory (default: ./extraction_output)
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./extraction_output"
    
    # Test extraction
    success = test_package_extraction(package_file_path, output_dir)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
