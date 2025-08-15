import os
from cognos_migrator.migrations.report import migrate_single_report

def test_report_migration_from_id():
    """
    Tests the migration of a single report from a live Cognos server using a report ID.
    """
    # The ID of the report to be migrated
    report_id = "iFEE26FFBB98643308E6FEFC235B2D2CF"
    
    # Directory where the migration output will be saved
    output_dir = "test_output/report_id_migration_output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Cognos connection details
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6ZDE0Zjc1MDUtZDExNC1hYjM2LTczMzQtYWQ5ZTJjYThhOGM1OjExODA0NTY4Mjg7MDszOzA7"

    print(f"Starting migration for report ID: {report_id}")

    # Call the migration function with the report ID
    success = migrate_single_report(
        output_path=output_dir,
        cognos_url=cognos_url,
        session_key=session_key,
        report_id=report_id,
    )

    if success:
        print(f"Report migration for ID '{report_id}' completed successfully.")
        print(f"Output saved in: {output_dir}")
    else:
        print(f"Report migration for ID '{report_id}' failed.")

def test_material_inquiry_detail_report_from_xml():
    """
    Tests the migration of a single report from a local XML file.
    """
    # Path to the report XML file to be migrated
    report_file = "examples/Report XMLs DE/MaterialInquiryDetail_UC012.xml"
    
    # Directory where the migration output will be saved
    output_dir = "test_output/report_xml_migration_output_new"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Dummy values for Cognos connection details are provided since we are migrating 
    # from a local file and a connection to a live server is not required.
    cognos_url = "http://dummy-cognos-url"
    session_key = "dummy-session-key"

    print(f"Starting migration for report file: {report_file}")

    # Call the migration function with the file path
    success = migrate_single_report(
        output_path=output_dir,
        cognos_url=cognos_url,
        session_key=session_key,
        report_file_path=report_file,
    )

    if success:
        print(f"Report migration from XML file '{report_file}' completed successfully.")
        print(f"Output saved in: {output_dir}")
    else:
        print(f"Report migration from XML file '{report_file}' failed.")

if __name__ == "__main__":
    print("--- Running Test: Report Migration from ID ---")
    #test_report_migration_from_id()
    print("\n--- Running Test: Report Migration from XML File ---")
    test_material_inquiry_detail_report_from_xml() 