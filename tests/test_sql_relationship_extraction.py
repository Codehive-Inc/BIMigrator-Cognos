#!/usr/bin/env python
"""
Test script to verify SQL relationship extraction from XML and generation of JOIN clauses.
"""
import logging
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import the necessary modules
from cognos_migrator.extractors.packages.sql_relationship_extractor import SQLRelationshipExtractor

def test_sql_relationship_extraction():
    """Test SQL relationship extraction from XML and generation of JOIN clauses."""
    logger = logging.getLogger(__name__)
    logger.info("Testing SQL relationship extraction from XML...")
    
    # Create a SQLRelationshipExtractor instance
    extractor = SQLRelationshipExtractor(logger=logger)
    
    # Define paths
    package_file_path = '/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos/examples/packages/ELECTRIC_GENERATION_MAT.xml'
    output_dir = '/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos/test_output/sql_relationship_extraction'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract relationships and generate SQL
    logger.info(f"Extracting relationships from {package_file_path}...")
    result = extractor.extract_and_save(package_file_path, output_dir)
    
    # Check the results
    relationships = result.get('sql_relationships', [])
    logger.info(f"Extracted {len(relationships)} relationships")
    
    # Log some sample relationships
    for i, rel in enumerate(relationships[:5]):  # Show first 5 relationships
        logger.info(f"Relationship {i+1}: {rel['relationship_name']}")
        logger.info(f"  One side: {rel['table_a_one_side']} ({', '.join(rel['keys_a'])})")
        logger.info(f"  Many side: {rel['table_b_many_side']} ({', '.join(rel['keys_b'])})")
        logger.info(f"  Cardinality: {rel['cognos_cardinality']}")
        logger.info(f"  Join type: {rel['join_type']}")
        logger.info(f"  SQL: {rel['sql_join']}")
        logger.info("---")
    
    # Generate a complete SQL example for the first relationship
    if relationships:
        rel = relationships[0]
        complete_sql = f"""
SELECT 
    a.*,
    b.*
FROM 
    {rel['table_a_one_side']} a
{rel['sql_join'].replace(rel['table_b_many_side'], 'b')}
"""
        logger.info("Complete SQL example:")
        logger.info(complete_sql)
    
    logger.info(f"Results saved to {output_dir}/relationship_joins.csv and {output_dir}/sql_relationships.json")
    
    return relationships

if __name__ == "__main__":
    test_sql_relationship_extraction()
