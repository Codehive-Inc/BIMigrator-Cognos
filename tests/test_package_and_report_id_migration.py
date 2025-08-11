import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cognos_migrator.migrations.package import migrate_package_with_reports_explicit_session

def test_package_and_report_id_migration():
    """
    Tests the migration of a package and multiple reports by ID to a shared semantic model.
    """
    package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
    report_ids = [
        "iCE1165EC80204771A0522FC80833824E",
        "i57591C769343460D8336D2E09BDD9329",
        "i85E7DF75D282452BAF5231C18F5B48A7"
    ]
    output_dir = "test_output/package_and_report_id_migration_output"

    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    print(f"Starting migration for package '{package_file}' and {len(report_ids)} reports by ID.")

    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6YmJhZTEzYmQtYWMxZS1jZWU2LWI3NDgtZTQzZTkzYmE4Yjk1OjA2MTQ0MDU5NTk7MDszOzA7"
    
    success, _ = migrate_package_with_reports_explicit_session(
        package_file_path=package_file,
        output_path=output_dir,
        cognos_url=cognos_url,
        session_key=session_key,
        report_ids=report_ids
    )

    if success:
        print("Shared semantic model migration with report IDs completed successfully.")
        print(f"Output saved in: {output_dir}")
    else:
        print("Shared semantic model migration with report IDs failed.")


if __name__ == "__main__":
    test_package_and_report_id_migration() 