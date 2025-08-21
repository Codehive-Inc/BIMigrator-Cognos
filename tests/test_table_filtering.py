#!/usr/bin/env python3
"""
Test script to demonstrate the table filtering functionality for package migration.
This script bypasses the Cognos API calls and directly tests the filtering logic.
"""

import os
import sys
import json
from pathlib import Path
from cognos_migrator.migrations.package import filter_data_model_tables
from cognos_migrator.models import DataModel, Table, Column, Relationship

def create_test_data_model():
    """Create a test data model with sample tables"""
    tables = [
        Table(
            name="Customer",
            columns=[
                Column(name="CustomerID", data_type="int", source_column="CustomerID"),
                Column(name="Name", data_type="string", source_column="Name"),
                Column(name="Email", data_type="string", source_column="Email")
            ]
        ),
        Table(
            name="Order",
            columns=[
                Column(name="OrderID", data_type="int", source_column="OrderID"),
                Column(name="CustomerID", data_type="int", source_column="CustomerID"),
                Column(name="OrderDate", data_type="datetime", source_column="OrderDate")
            ]
        ),
        Table(
            name="Product",
            columns=[
                Column(name="ProductID", data_type="int", source_column="ProductID"),
                Column(name="Name", data_type="string", source_column="Name"),
                Column(name="Price", data_type="decimal", source_column="Price")
            ]
        ),
        Table(
            name="OrderDetail",
            columns=[
                Column(name="OrderID", data_type="int", source_column="OrderID"),
                Column(name="ProductID", data_type="int", source_column="ProductID"),
                Column(name="Quantity", data_type="int", source_column="Quantity")
            ]
        ),
        Table(
            name="Category",
            columns=[
                Column(name="CategoryID", data_type="int", source_column="CategoryID"),
                Column(name="Name", data_type="string", source_column="Name")
            ]
        )
    ]
    
    relationships = [
        Relationship(
            from_table="Customer",
            from_column="CustomerID",
            to_table="Order",
            to_column="CustomerID"
        ),
        Relationship(
            from_table="Order",
            from_column="OrderID",
            to_table="OrderDetail",
            to_column="OrderID"
        ),
        Relationship(
            from_table="Product",
            from_column="ProductID",
            to_table="OrderDetail",
            to_column="ProductID"
        )
    ]
    
    return DataModel(
        name="TestModel",
        tables=tables,
        relationships=relationships,
        measures=[]
    )

def main():
    # Create a test data model
    data_model = create_test_data_model()
    print(f"Original data model has {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
    print(f"Tables: {[table.name for table in data_model.tables]}")
    print(f"Relationships: {[(rel.from_table, rel.to_table) for rel in data_model.relationships]}")
    
    # Test case 1: Filter to include Customer and Order tables
    print("\nTest Case 1: Filter to include Customer and Order tables")
    table_references = {"Customer", "Order"}
    filtered_model = filter_data_model_tables(data_model, table_references)
    print(f"Filtered model has {len(filtered_model.tables)} tables and {len(filtered_model.relationships)} relationships")
    print(f"Tables: {[table.name for table in filtered_model.tables]}")
    print(f"Relationships: {[(rel.from_table, rel.to_table) for rel in filtered_model.relationships]}")
    
    # Test case 2: Filter to include Order, OrderDetail, and Product tables
    print("\nTest Case 2: Filter to include Order, OrderDetail, and Product tables")
    table_references = {"Order", "OrderDetail", "Product"}
    filtered_model = filter_data_model_tables(data_model, table_references)
    print(f"Filtered model has {len(filtered_model.tables)} tables and {len(filtered_model.relationships)} relationships")
    print(f"Tables: {[table.name for table in filtered_model.tables]}")
    print(f"Relationships: {[(rel.from_table, rel.to_table) for rel in filtered_model.relationships]}")
    
    # Test case 3: Filter to include only Category table (no relationships)
    print("\nTest Case 3: Filter to include only Category table (no relationships)")
    table_references = {"Category"}
    filtered_model = filter_data_model_tables(data_model, table_references)
    print(f"Filtered model has {len(filtered_model.tables)} tables and {len(filtered_model.relationships)} relationships")
    print(f"Tables: {[table.name for table in filtered_model.tables]}")
    print(f"Relationships: {[(rel.from_table, rel.to_table) for rel in filtered_model.relationships]}")

if __name__ == "__main__":
    main()
