import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cognos_migrator.migrations.package import migrate_package_with_local_reports, migrate_package_with_reports_explicit_session

def test_unified_shared_model_migration():
    """
    Tests both pathways (local files and report IDs) for the unified
    shared model creation to validate the new `_migrate_shared_model` engine.
    """
    package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
    
    # --- Test 1: Local Report Files ---
    print("--- Running Test 1: Shared Model with Local Report Files ---")
    local_report_files = [
        "examples/Report XMLs DE/MaterialAdjustmentDetail_UC017.xml",
        "examples/Report XMLs DE/MaterialInquiryDetail_UC012.xml",
        "examples/Report XMLs DE/MaterialReceiptDetail_UC016.xml",
        "examples/Report XMLs DE/PartNumbers_UC013.xml"
    ]
    output_dir_local = "test_output/unified_shared_model_local"
    os.makedirs(output_dir_local, exist_ok=True)

    success_local = migrate_package_with_local_reports(
        package_file_path=package_file,
        output_path=output_dir_local,
        report_file_paths=local_report_files,
        cognos_url="dummy-url", # Not used for local files, but required
        session_key="dummy-key" # Not used for local files, but required
    )
    assert success_local is True
    print("--- Test 1 PASSED ---")

    # --- Test 2: Report IDs from Server ---
    print("\n--- Running Test 2: Shared Model with Report IDs ---")
    id_report_ids = ["i85E7DF75D282452BAF5231C18F5B48A7"] # Use a real ID
    output_dir_id = "test_output/unified_shared_model_id"
    os.makedirs(output_dir_id, exist_ok=True)

    # IMPORTANT: Provide valid credentials for the ID-based test
    cognos_url = "http://20.244.32.126:9300/api/v1"
    session_key = "CAM MTsxMDE6MTljMTE4NDQtNThlNi1mN2Y1LTBkNTctNjQyYjc3NzNmM2E0OjEwNDEzNjI0MjQ7MDszOzA7" # Replace with a valid key

    if "PASTE_YOUR_SESSION_KEY_HERE" in session_key:
        print("WARNING: Skipping live server test. Please provide a valid session key.")
    else:
        success_id = migrate_package_with_reports_explicit_session(
            package_file_path=package_file,
            output_path=output_dir_id,
            cognos_url=cognos_url,
            session_key=session_key,
            report_ids=id_report_ids
        )
        assert success_id is True
        print("--- Test 2 PASSED ---")

if __name__ == "__main__":
    test_unified_shared_model_migration() 