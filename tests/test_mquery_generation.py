#!/usr/bin/env python
"""
Test script for enhanced M-Query generation.

This script creates a sample table and uses the enhanced M-Query converter
to generate an M-Query, demonstrating the new features.
"""

import os
import logging
from cognos_migrator.converters.mquery_converter import MQueryConverter
from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.models import Table, Column, DataType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set DAX API URL if not already set
if 'DAX_API_URL' not in os.environ:
    os.environ['DAX_API_URL'] = 'http://localhost:8080'
    logger.info(f"DAX_API_URL not set, using default: {os.environ['DAX_API_URL']}")
else:
    logger.info(f"Using DAX_API_URL: {os.environ['DAX_API_URL']}")

def main():
    """Main function to test M-Query generation"""
    # Create a test table with relationships
    table = Table(
        name="SalesData",
        columns=[
            Column(name="OrderID", data_type=DataType.INTEGER),
            Column(name="CustomerID", data_type=DataType.INTEGER),
            Column(name="ProductID", data_type=DataType.INTEGER),
            Column(name="OrderDate", data_type=DataType.DATETIME),
            Column(name="Quantity", data_type=DataType.INTEGER),
            Column(name="UnitPrice", data_type=DataType.DECIMAL),
            Column(name="TotalAmount", data_type=DataType.DECIMAL),
        ],
        source_query="""
        SELECT 
            o.OrderID, 
            o.CustomerID, 
            od.ProductID, 
            o.OrderDate, 
            od.Quantity, 
            od.UnitPrice,
            od.Quantity * od.UnitPrice as TotalAmount
        FROM 
            Sales.Orders o
            JOIN Sales.OrderDetails od ON o.OrderID = od.OrderID
        WHERE 
            o.OrderDate > '2023-01-01'
        """,
        database_type="SqlServer",
        database_name="SalesDB",
        schema_name="Sales"
    )
    
    # Add relationships (these would normally come from the model)
    class Relationship:
        def __init__(self, from_table, from_column, to_table, to_column, join_type="Inner"):
            self.from_table = from_table
            self.from_column = from_column
            self.to_table = to_table
            self.to_column = to_column
            self.join_type = join_type
    
    table.relationships = [
        Relationship("SalesData", "CustomerID", "Customers", "CustomerID"),
        Relationship("SalesData", "ProductID", "Products", "ProductID")
    ]
    
    # Create LLM service client and M-Query converter
    logger.info("Creating LLM service client and M-Query converter")
    llm_client = LLMServiceClient(api_url=os.environ['DAX_API_URL'])
    mquery_converter = MQueryConverter(llm_client)
    
    # Generate M-Query
    logger.info("Generating M-Query for test table")
    try:
        m_query = mquery_converter.convert_to_m_query(table)
        
        logger.info("Successfully generated M-Query:")
        print("\n" + "="*80)
        print("GENERATED M-QUERY:")
        print("="*80)
        print(m_query)
        print("="*80 + "\n")
        
        # Save the M-Query to a file
        output_file = "test_mquery_output.txt"
        with open(output_file, "w") as f:
            f.write(m_query)
        logger.info(f"M-Query saved to {output_file}")
        
    except Exception as e:
        logger.exception(f"Error generating M-Query: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
