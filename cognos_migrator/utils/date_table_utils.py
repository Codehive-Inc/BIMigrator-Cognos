"""
Utility functions for creating and managing date tables in Power BI models.

This module provides functionality for creating central date tables and
establishing relationships between datetime columns and the central date table.
"""

import logging
import os
import uuid
from typing import Dict, Any, Optional

from cognos_migrator.models import DataModel, Table, Column, Relationship


def create_central_date_table(data_model: DataModel, logger=None) -> None:
    """Creates a single, central date table for the data model.
    
    Args:
        data_model: The data model to add the central date table to
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    logger.info("Creating a single central date table for the model.")

    # Determine which template to use based on the mode
    template_filename = f"DateTableTemplate_{data_model.date_table_mode.capitalize()}.tmdl"
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                               'templates', template_filename)
    
    if not os.path.exists(template_path):
        logger.warning(f"{template_filename} not found at {template_path}. Skipping central date table creation.")
        return
    
    # Read the template content
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read DateTableTemplate.tmdl: {e}")
        return
    
    # Initialize date_tables attribute if it doesn't exist
    if not hasattr(data_model, 'date_tables'):
        data_model.date_tables = []
    
    # Create the central date table
    date_table_name = "CentralDateTable"
    
    data_model.date_tables.append({
        'id': str(uuid.uuid4()),
        'name': date_table_name,
        'template_content': template_content.replace('DateTableTemplate_19728d8e-9427-4914-8bc5-607973681b1e', date_table_name)
    })
    
    logger.info(f"Successfully created central date table: {date_table_name}")


def create_date_relationships(table: Table, data_model: DataModel, logger=None) -> None:
    """Create relationships between datetime columns and the central date table.
    
    Args:
        table: The table containing datetime columns
        data_model: The data model which contains the central date table
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    # Skip if no date tables exist
    if not hasattr(data_model, 'date_tables') or not data_model.date_tables:
        logger.warning("No date tables found in the data model. Skipping date relationship creation.")
        return
        
    # Find the central date table
    central_date_table_name = "CentralDateTable"
    
    # Look for datetime columns in the table
    for column in table.columns:
        if column.data_type == "dateTime":
            logger.info(f"Creating date relationship for column {column.name} in table {table.name}")
            
            # Create a relationship between this column and the central date table
            relationship = Relationship(
                from_table=table.name,
                from_column=column.name,
                to_table=central_date_table_name,
                to_column="Date",  # Standard date column in the central date table
                from_cardinality="many",
                to_cardinality="one",
                cross_filtering_behavior="BothDirections",
                join_on_date_behavior="datePartOnly"
            )
            
            # Add the relationship to the data model
            data_model.relationships.append(relationship)
            
            # Add metadata to the column to indicate it's connected to the date table
            if not hasattr(column, 'metadata'):
                column.metadata = {}
                
            column.metadata['date_relationship_id'] = relationship.id
            column.metadata['date_hierarchy'] = "Date Hierarchy"
            
            logger.info(f"Created date relationship for column {column.name} in table {table.name}")
