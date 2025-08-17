"""
Test script for the staging table handler functionality.

This script tests the staging table handler's ability to create staging tables
and update relationships based on the settings in settings.json.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cognos_migrator.generators.staging_table_handler import StagingTableHandler
from cognos_migrator.models import DataModel, Table, Column, Relationship, DataType

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data_model():
    """Create a test data model with complex relationships for testing."""
    # Create tables
    tables = []
    
    # Create ITEMS table
    items_columns = [
        Column(name="ITEM_NUMBER", data_type="string", source_column="ITEM_NUMBER"),
        Column(name="ITEM_NAME", data_type="string", source_column="ITEM_NAME"),
        Column(name="ITEM_DESCRIPTION", data_type="string", source_column="ITEM_DESCRIPTION")
    ]
    items_table = Table(
        name="ITEMS",
        columns=items_columns,
        source_query="SELECT * FROM ITEMS",
        metadata={"is_source_table": True}
    )
    tables.append(items_table)
    
    # Create SITES table
    sites_columns = [
        Column(name="SITE_NUMBER", data_type="string", source_column="SITE_NUMBER"),
        Column(name="SITE_NAME", data_type="string", source_column="SITE_NAME"),
        Column(name="SITE_LOCATION", data_type="string", source_column="SITE_LOCATION")
    ]
    sites_table = Table(
        name="SITES",
        columns=sites_columns,
        source_query="SELECT * FROM SITES",
        metadata={"is_source_table": True}
    )
    tables.append(sites_table)
    
    # Create MATERIAL_CHARGES table (fact table 1)
    material_charges_columns = [
        Column(name="CHARGE_ID", data_type="string", source_column="CHARGE_ID"),
        Column(name="ITEM_NUMBER", data_type="string", source_column="ITEM_NUMBER"),
        Column(name="SITE_NUMBER", data_type="string", source_column="SITE_NUMBER"),
        Column(name="CHARGE_AMOUNT", data_type="decimal", source_column="CHARGE_AMOUNT"),
        Column(name="CHARGE_DATE", data_type="dateTime", source_column="CHARGE_DATE")
    ]
    material_charges_table = Table(
        name="MATERIAL_CHARGES",
        columns=material_charges_columns,
        source_query="SELECT * FROM MATERIAL_CHARGES",
        metadata={"is_source_table": True}
    )
    tables.append(material_charges_table)
    
    # Create PURCHASE_ORDER_LINE table (fact table 2)
    po_line_columns = [
        Column(name="PO_LINE_ID", data_type="string", source_column="PO_LINE_ID"),
        Column(name="PO_NUMBER", data_type="string", source_column="PO_NUMBER"),
        Column(name="ITEM_NUMBER", data_type="string", source_column="ITEM_NUMBER"),
        Column(name="SITE_NUMBER", data_type="string", source_column="SITE_NUMBER"),
        Column(name="QUANTITY", data_type="decimal", source_column="QUANTITY"),
        Column(name="UNIT_PRICE", data_type="decimal", source_column="UNIT_PRICE")
    ]
    po_line_table = Table(
        name="PURCHASE_ORDER_LINE",
        columns=po_line_columns,
        source_query="SELECT * FROM PURCHASE_ORDER_LINE",
        metadata={"is_source_table": True}
    )
    tables.append(po_line_table)
    
    # Create relationships
    relationships = []
    
    # Relationship 1: MATERIAL_CHARGES to ITEMS
    rel1 = Relationship(
        id="Rel_MC_ITEMS",
        from_table="MATERIAL_CHARGES",
        from_column="ITEM_NUMBER",
        to_table="ITEMS",
        to_column="ITEM_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=True
    )
    relationships.append(rel1)
    
    # Relationship 2: MATERIAL_CHARGES to SITES
    rel2 = Relationship(
        id="Rel_MC_SITES",
        from_table="MATERIAL_CHARGES",
        from_column="SITE_NUMBER",
        to_table="SITES",
        to_column="SITE_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=True
    )
    relationships.append(rel2)
    
    # Relationship 3: PURCHASE_ORDER_LINE to ITEMS
    rel3 = Relationship(
        id="Rel_PO_ITEMS",
        from_table="PURCHASE_ORDER_LINE",
        from_column="ITEM_NUMBER",
        to_table="ITEMS",
        to_column="ITEM_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=True
    )
    relationships.append(rel3)
    
    # Relationship 4: PURCHASE_ORDER_LINE to SITES
    rel4 = Relationship(
        id="Rel_PO_SITES",
        from_table="PURCHASE_ORDER_LINE",
        from_column="SITE_NUMBER",
        to_table="SITES",
        to_column="SITE_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=True
    )
    relationships.append(rel4)
    
    # Add complex relationships (multiple relationships between same tables)
    # Relationship 5: Another relationship between MATERIAL_CHARGES and ITEMS (for a different business context)
    rel5 = Relationship(
        id="Rel_MC_ITEMS_Alt",
        from_table="MATERIAL_CHARGES",
        from_column="ITEM_NUMBER",
        to_table="ITEMS",
        to_column="ITEM_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=False  # This one is inactive but still counts as a complex relationship
    )
    relationships.append(rel5)
    
    # Relationship 6: Composite key relationship
    rel6 = Relationship(
        id="Rel_PO_ITEMS_Composite",
        from_table="PURCHASE_ORDER_LINE",
        from_column="ITEM_NUMBER,SITE_NUMBER",  # Composite key with multiple columns
        to_table="ITEMS",
        to_column="ITEM_NUMBER,SITE_NUMBER",
        from_cardinality="many",
        to_cardinality="one",
        cross_filtering_behavior="BothDirections",
        is_active=True
    )
    relationships.append(rel6)
    
    # Create data model
    data_model = DataModel(
        name="TestModel",
        tables=tables,
        relationships=relationships,
        compatibility_level=1550
    )
    
    return data_model

def test_staging_table_handler():
    """Test the staging table handler functionality."""
    logger.info("Testing staging table handler...")
    
    # Create test settings
    settings = {
        "staging_tables": {
            "enabled": True,
            "naming_prefix": "stg_",
            "model_handling": "star_schema"
        }
    }
    
    # Create staging table handler
    handler = StagingTableHandler(settings)
    
    # Create test data model
    data_model = create_test_data_model()
    logger.info(f"Created test data model with {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
    
    # Process data model
    processed_model = handler.process_data_model(data_model)
    
    # Log results
    logger.info(f"Processed data model has {len(processed_model.tables)} tables and {len(processed_model.relationships)} relationships")
    
    # Log staging tables
    staging_tables = [t for t in processed_model.tables if t.metadata.get('is_staging_table')]
    logger.info(f"Found {len(staging_tables)} staging tables:")
    for table in staging_tables:
        logger.info(f"  - {table.name} with {len(table.columns)} columns")
        logger.info(f"    Source tables: {table.metadata.get('source_tables')}")
        logger.info(f"    M-query: {table.source_query[:100]}...")
    
    # Log relationships involving staging tables
    staging_relationships = [r for r in processed_model.relationships 
                            if any(t.name == r.from_table or t.name == r.to_table for t in staging_tables)]
    logger.info(f"Found {len(staging_relationships)} relationships involving staging tables:")
    for rel in staging_relationships:
        logger.info(f"  - {rel.id}: {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
    
    # Return the processed model for further inspection
    return processed_model

def test_with_settings_from_file():
    """Test the staging table handler using settings from settings.json."""
    logger.info("Testing staging table handler with settings from file...")
    
    # Load settings from file
    settings_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'settings.json'
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        logger.info(f"Loaded settings from {settings_path}")
    else:
        logger.warning(f"Settings file not found at {settings_path}, using default settings")
        settings = {
            "staging_tables": {
                "enabled": True,
                "naming_prefix": "stg_",
                "model_handling": "star_schema"
            }
        }
    
    # Create staging table handler
    handler = StagingTableHandler(settings)
    
    # Create test data model
    data_model = create_test_data_model()
    
    # Process data model
    processed_model = handler.process_data_model(data_model)
    
    # Log results
    logger.info(f"Processed data model with settings from file: {len(processed_model.tables)} tables and {len(processed_model.relationships)} relationships")
    
    # Return the processed model for further inspection
    return processed_model

if __name__ == "__main__":
    # Run tests
    logger.info("Running staging table handler tests...")
    
    # Test with hardcoded settings
    processed_model = test_staging_table_handler()
    
    # Test with settings from file
    processed_model_from_file = test_with_settings_from_file()
    
    logger.info("Tests completed successfully!")
