#!/usr/bin/env python3
"""
Test script to verify that duplicate tables referencing the same database table
are correctly combined during the migration process.
"""

import os
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from cognos_migrator.extractors.packages.consolidated_package_extractor import ConsolidatedPackageExtractor
from cognos_migrator.models import DataModel, Table

def test_table_combination():
    """Test that tables referencing the same database table are combined."""
    # Set up paths
    package_file = os.path.join(project_dir, "examples", "packages", "FM Models", "Energy_Share.xml")
    output_dir = os.path.join(project_dir, "output", "output_energy_share_test", "extracted")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize extractor
    extractor = ConsolidatedPackageExtractor(logger)
    
    # Extract package
    logger.info(f"Extracting package from {package_file}")
    package_info = extractor.extract_package(package_file, output_dir)
    
    # Convert to data model
    logger.info("Converting package to data model")
    data_model = extractor.convert_to_data_model(package_info)
    
    # Check for combined tables
    check_table_combination(data_model, "Territory", "tblTerritory")
    check_table_combination(data_model, "Agency", "tblAgency")
    check_table_combination(data_model, "Vendor", "tblVendor")
    
    # Print final table count
    logger.info(f"Final data model contains {len(data_model.tables)} tables")
    
    # Print all table names to verify no duplicates
    table_names = [table.name for table in data_model.tables]
    logger.info(f"Table names in data model: {', '.join(table_names)}")
    
    return data_model

def check_table_combination(data_model, business_name, db_name):
    """Check if a business table and DB table were properly combined."""
    # Look for tables with either name
    tables = [t for t in data_model.tables if t.name.lower() in (business_name.lower(), db_name.lower())]
    
    if not tables:
        logger.warning(f"No tables found matching {business_name} or {db_name}")
        return
    
    logger.info(f"\n--- Checking {business_name}/{db_name} combination ---")
    logger.info(f"Found {len(tables)} related tables:")
    
    for table in tables:
        logger.info(f"Table: {table.name}")
        if hasattr(table, 'metadata') and table.metadata:
            if 'original_name' in table.metadata:
                logger.info(f"  Original name: {table.metadata['original_name']}")
            if 'enhanced_with_model_query' in table.metadata:
                logger.info(f"  Enhanced with model query: {table.metadata['enhanced_with_model_query']}")
        
        if table.source_query:
            logger.info(f"  SQL: {table.source_query[:100]}...")
            
            # Check if the SQL is a simple SELECT * query
            if 'select * from' in table.source_query.lower():
                logger.warning(f"  {table.name} has simple SELECT * query - combination may not have worked")
            else:
                logger.info(f"  {table.name} has detailed SQL query - combination successful!")
        
        # Print column count
        logger.info(f"  Column count: {len(table.columns)}")
    
    # Check if we have the expected business-friendly name
    if any(t.name.lower() == business_name.lower() for t in tables) and len(tables) == 1:
        logger.info(f"✓ Success: {db_name} was properly combined into {business_name}")
    elif len(tables) > 1:
        logger.warning(f"✗ Failed: Found multiple tables ({len(tables)}) for {business_name}/{db_name}")
    else:
        logger.warning(f"✗ Failed: Did not find expected business-friendly name {business_name}")
    
    logger.info("-------------------------------------------\n")

if __name__ == "__main__":
    test_table_combination()
