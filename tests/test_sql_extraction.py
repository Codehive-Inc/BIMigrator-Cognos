#!/usr/bin/env python
"""
Test script to verify SQL extraction from XML and assignment to Table objects.
"""
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import the necessary modules
from cognos_migrator.extractors.packages.consolidated_package_extractor import ConsolidatedPackageExtractor

def test_sql_extraction():
    """Test SQL extraction from XML and assignment to Table objects."""
    logger = logging.getLogger(__name__)
    logger.info("Testing SQL extraction from XML...")
    
    # Create a ConsolidatedPackageExtractor instance
    extractor = ConsolidatedPackageExtractor(logger=logger)
    
    # Define paths
    package_file_path = '/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos/examples/packages/FM Models/Energy_Share.xml'
    output_dir = '/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos/test_output'
    
    # Extract package information
    logger.info(f"Extracting package from {package_file_path}...")
    package_info = extractor.extract_package(package_file_path, output_dir)
    
    # Convert to data model
    logger.info("Converting package to data model...")
    data_model = extractor.convert_to_data_model(package_info)
    
    # Check if tables have source_query attribute set
    logger.info(f"Checking source_query attribute for {len(data_model.tables)} tables...")
    
    tables_with_sql = 0
    tables_without_sql = 0
    
    for table in data_model.tables:
        if table.source_query:
            tables_with_sql += 1
            logger.info(f"Table {table.name} has SQL: {table.source_query[:100]}...")
        else:
            tables_without_sql += 1
            logger.info(f"Table {table.name} has no SQL")
    
    logger.info(f"Summary: {tables_with_sql} tables with SQL, {tables_without_sql} tables without SQL")
    
    # Look for specific tables
    territory_table = next((t for t in data_model.tables if t.name == 'tblTerritory'), None)
    if territory_table:
        logger.info(f"Territory table SQL: {territory_table.source_query}")
    else:
        logger.info("Territory table not found")
    
    return data_model

if __name__ == "__main__":
    test_sql_extraction()
