#!/usr/bin/env python3
"""
Create sample output to demonstrate the migration system
"""
import os
import sys
import json
from pathlib import Path

def create_sample_powerbi_project():
    """Create a sample Power BI project structure"""
    
    # Create output directory
    output_dir = Path("output") / "sample_cognos_migration"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating sample Power BI project in: {output_dir}")
    
    # Create Model directory
    model_dir = output_dir / "Model"
    model_dir.mkdir(exist_ok=True)
    
    # Create tables directory
    tables_dir = model_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    
    # Create cultures directory
    cultures_dir = model_dir / "cultures"
    cultures_dir.mkdir(exist_ok=True)
    
    # Create Report directory
    report_dir = output_dir / "Report"
    report_dir.mkdir(exist_ok=True)
    
    # Create sections directory
    sections_dir = report_dir / "sections"
    sections_dir.mkdir(exist_ok=True)
    
    # Create a sample page section
    page_dir = sections_dir / "000_Page1"
    page_dir.mkdir(exist_ok=True)
    
    # Create StaticResources directory
    static_dir = output_dir / "StaticResources"
    static_dir.mkdir(exist_ok=True)
    
    shared_dir = static_dir / "SharedResources"
    shared_dir.mkdir(exist_ok=True)
    
    # Create project configuration file
    project_config = {
        "version": "1.0",
        "name": "Sample Cognos Migration",
        "description": "Migrated from Cognos Analytics",
        "created": "2025-05-28",
        "migrationTool": "cognos_to_bimigrator"
    }
    
    with open(output_dir / ".pbixproj.json", 'w') as f:
        json.dump(project_config, f, indent=2)
    
    # Create database.tmdl
    database_content = """database 'Sample Cognos Migration'
	culture 'en-US'

	table 'Sample Data'
		lineageTag: 12345678-1234-1234-1234-123456789012

		column 'ID'
			dataType: int64
			formatString: 0
			lineageTag: 12345678-1234-1234-1234-123456789013

		column 'Name'
			dataType: string
			lineageTag: 12345678-1234-1234-1234-123456789014

		column 'Value'
			dataType: double
			formatString: #,0.00
			lineageTag: 12345678-1234-1234-1234-123456789015

		partition 'Sample Data'
			mode: import
			source =
				let
					Source = Table.FromRows({
						{"ID", "Name", "Value"},
						{1, "Sample Item 1", 100.50},
						{2, "Sample Item 2", 200.75},
						{3, "Sample Item 3", 300.25}
					}),
					#"Changed Type" = Table.TransformColumnTypes(Source,{{"ID", Int64.Type}, {"Name", type text}, {"Value", type number}})
				in
					#"Changed Type"

"""
    
    with open(model_dir / "database.tmdl", 'w') as f:
        f.write(database_content)
    
    # Create model.tmdl
    model_content = """model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: en-US
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

"""
    
    with open(model_dir / "model.tmdl", 'w') as f:
        f.write(model_content)
    
    # Create sample table file
    table_content = """table 'Sample Data'
	lineageTag: 12345678-1234-1234-1234-123456789012

	column 'ID'
		dataType: int64
		formatString: 0
		lineageTag: 12345678-1234-1234-1234-123456789013
		summarizeBy: none
		sourceColumn: ID

	column 'Name'
		dataType: string
		lineageTag: 12345678-1234-1234-1234-123456789014
		summarizeBy: none
		sourceColumn: Name

	column 'Value'
		dataType: double
		formatString: #,0.00
		lineageTag: 12345678-1234-1234-1234-123456789015
		summarizeBy: sum
		sourceColumn: Value

	partition 'Sample Data'
		mode: import
		source =
			let
				Source = Table.FromRows({
					{"ID", "Name", "Value"},
					{1, "Sample Item 1", 100.50},
					{2, "Sample Item 2", 200.75},
					{3, "Sample Item 3", 300.25}
				}),
				#"Changed Type" = Table.TransformColumnTypes(Source,{{"ID", Int64.Type}, {"Name", type text}, {"Value", type number}})
			in
				#"Changed Type"

"""
    
    with open(tables_dir / "Sample Data.tmdl", 'w') as f:
        f.write(table_content)
    
    # Create culture file
    culture_content = """culture en-US
	linguisticMetadata =
		{
			"Version": "1.0.0",
			"Language": "en-US"
		}

"""
    
    with open(cultures_dir / "en-US.tmdl", 'w') as f:
        f.write(culture_content)
    
    # Create report config
    report_config = {
        "version": "5.0",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU06"
            }
        }
    }
    
    with open(report_dir / "config.json", 'w') as f:
        json.dump(report_config, f, indent=2)
    
    # Create report.json
    report_json = {
        "name": "Sample Cognos Migration",
        "id": "12345678-1234-1234-1234-123456789012",
        "pages": [
            {
                "name": "Page1",
                "displayName": "Sample Page",
                "width": 1280,
                "height": 720,
                "visualContainers": []
            }
        ],
        "sections": [
            {
                "name": "000_Page1",
                "displayName": "Sample Page"
            }
        ]
    }
    
    with open(report_dir / "report.json", 'w') as f:
        json.dump(report_json, f, indent=2)
    
    # Create Version.txt
    with open(output_dir / "Version.txt", 'w') as f:
        f.write("1.0\n")
    
    # Create DiagramLayout.json
    diagram_layout = {
        "version": 1,
        "nodes": [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 150
            }
        ],
        "edges": []
    }
    
    with open(output_dir / "DiagramLayout.json", 'w') as f:
        json.dump(diagram_layout, f, indent=2)
    
    # Create ReportMetadata.json
    report_metadata = {
        "version": "1.0",
        "createdFrom": "Cognos Analytics",
        "migrationTool": "cognos_to_bimigrator",
        "migrationDate": "2025-05-28"
    }
    
    with open(output_dir / "ReportMetadata.json", 'w') as f:
        json.dump(report_metadata, f, indent=2)
    
    # Create ReportSettings.json
    report_settings = {
        "version": "1.0",
        "settings": {
            "theme": "default",
            "locale": "en-US"
        }
    }
    
    with open(output_dir / "ReportSettings.json", 'w') as f:
        json.dump(report_settings, f, indent=2)
    
    print("✅ Sample Power BI project structure created successfully!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    
    # List all created files
    print("\n📄 Generated files:")
    for file_path in sorted(output_dir.rglob("*")):
        if file_path.is_file():
            print(f"  - {file_path.relative_to(output_dir)}")
    
    return output_dir

def main():
    """Main function"""
    print("=== Creating Sample Power BI Migration Output ===")
    
    try:
        output_dir = create_sample_powerbi_project()
        print(f"\n🎉 Success! Sample migration output created in: {output_dir}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
