import os
from cognos_migrator.migrations.package import migrate_package_with_local_reports

def test_package_and_report_migration():
    """
    Tests the migration of a package and multiple local report files to a shared semantic model.
    """
    package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
    report_files = [
        "examples/Report XMLs DE/MaterialAdjustmentDetail_UC017.xml",
        "examples/Report XMLs DE/MaterialInquiryDetail_UC012.xml",
        "examples/Report XMLs DE/MaterialReceiptDetail_UC016.xml",
        "examples/Report XMLs DE/PartNumbers_UC013.xml"
    ]
    output_dir = "test_output/z_starSchema_directQuery"

    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    print(f"Starting migration for package '{package_file}' and {len(report_files)} reports.")

    # Dummy values for Cognos connection details (required even for file-based migration)
    cognos_url = "http://dummy-cognos-url"
    session_key = "dummy-session-key"
    
    success = migrate_package_with_local_reports(
        package_file_path=package_file,
        output_path=output_dir,
        report_file_paths=report_files,
        cognos_url=cognos_url,
        session_key=session_key
    )

    if success:
        print("Shared semantic model migration completed successfully.")
        print(f"Output saved in: {output_dir}")
    else:
        print("Shared semantic model migration failed.")

if __name__ == "__main__":
    test_package_and_report_migration() 