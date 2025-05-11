"""Example usage of template generator with dataclasses."""
from pathlib import Path
from src.generators.template_generator import TemplateGenerator
from config.dataclasses import PowerBiTable, PowerBiColumn, PowerBiTargetStructure, PowerBiRelationship

def create_test_model():
    """Create a test Power BI model using dataclasses."""
    # Create columns for Sales table
    sales_columns = [
        PowerBiColumn(
            pbi_name="OrderID",
            pbi_datatype="int64",
            source_name="OrderID"
        ),
        PowerBiColumn(
            pbi_name="ProductID",
            pbi_datatype="int64",
            source_name="ProductID"
        ),
        PowerBiColumn(
            pbi_name="Amount",
            pbi_datatype="decimal",
            source_name="Amount",
            format_string="$#,##0.00"
        )
    ]

    # Create Sales table
    sales_table = PowerBiTable(
        pbi_name="Sales",
        source_name="Sales",
        columns=sales_columns
    )

    # Create columns for Products table
    product_columns = [
        PowerBiColumn(
            pbi_name="ProductID",
            pbi_datatype="int64",
            source_name="ProductID"
        ),
        PowerBiColumn(
            pbi_name="Name",
            pbi_datatype="string",
            source_name="Name"
        )
    ]

    # Create Products table
    products_table = PowerBiTable(
        pbi_name="Products",
        source_name="Products",
        columns=product_columns
    )

    # Create relationship
    relationship = PowerBiRelationship(
        from_table="Sales",
        from_column="ProductID",
        to_table="Products",
        to_column="ProductID",
        cardinality="oneToMany",
        cross_filter_behavior="bothDirections"
    )

    # Create model
    model = PowerBiTargetStructure(
        db_name="Sample Model",
        tables={"Sales": sales_table, "Products": products_table},
        relationships=[relationship]
    )

    # Convert tables to dictionaries
    table_dicts = []
    for table in model.tables.values():
        table_dict = {
            "name": table.pbi_name,
            "source_name": table.source_name,
            "columns": [{
                "name": col.pbi_name,
                "datatype": col.pbi_datatype,
                "source_column": col.source_name,
                "format_string": col.format_string,
                "is_hidden": col.is_hidden,
                "summarize_by": col.summarize_by
            } for col in table.columns]
        }
        table_dicts.append(table_dict)

    # Convert relationships to dictionaries
    rel_dicts = [{
        "id": f"rel_{i}",
        "from_table": rel.from_table,
        "from_column": rel.from_column,
        "to_table": rel.to_table,
        "to_column": rel.to_column,
        "cardinality": rel.cardinality,
        "cross_filter_behavior": rel.cross_filter_behavior
    } for i, rel in enumerate(model.relationships)]

    # Create the full configuration data structure
    config_data = {
        "PowerBiModel": {
            "model_name": model.db_name,
            "default_culture": "en-US",
            "source_culture": "en-US",
            "legacy_redirects": True,
            "return_null_errors": True,
            "query_order_list": ["Sales", "Products"],
            "time_intelligence_enabled": False
        },
        "PowerBiTable": table_dicts,
        "PowerBiRelationship": rel_dicts
    }

    return config_data

def main():
    """Run template generation test."""
    # Create test model
    model_data = create_test_model()
    
    # Initialize template generator
    generator = TemplateGenerator("config/twb-to-pbi.yaml")
    
    # Generate files
    output_dir = Path("output")
    generated_files = generator.generate_files(model_data, str(output_dir))
    
    print("\nGenerated files:")
    for file_type, files in generated_files.items():
        print(f"\n{file_type}:")
        for file in files:
            print(f"  - {file}")

if __name__ == "__main__":
    main()
