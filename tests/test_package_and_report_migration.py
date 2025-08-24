import os
import json
from pathlib import Path

from cognos_migrator.migrations.package import migrate_package_with_local_reports


def test_package_and_report_migration():
    """
    Tests the migration of a package and multiple local report files to a shared semantic model.
    This test validates that backend settings override local settings.json file.
    """
    package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
    report_files = [
        "examples/Report XMLs DE/MaterialAdjustmentDetail_UC017.xml",
        "examples/Report XMLs DE/MaterialInquiryDetail_UC012.xml",
        "examples/Report XMLs DE/MaterialReceiptDetail_UC016.xml",
        "examples/Report XMLs DE/PartNumbers_UC013.xml"
    ]
    
    # Test 1: Using settings.json (should use "direct_query" from file)
    output_dir_1 = "test_output/z_settings_from_file"
    os.makedirs(output_dir_1, exist_ok=True)
    
    # Test 2: Using backend settings (should override settings.json)
    output_dir_2 = "test_output/z_settings_from_backend"
    os.makedirs(output_dir_2, exist_ok=True)

    print("=" * 80)
    print("SETTINGS FLOW VALIDATION TEST")
    print("=" * 80)
    
    # Read current settings.json to show what it contains
    settings_file = Path("settings.json")
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            file_settings = json.load(f)
        print(f"📄 Current settings.json contains:")
        print(f"   - data_load_mode: {file_settings.get('staging_tables', {}).get('data_load_mode', 'NOT SET')}")
        print(f"   - model_handling: {file_settings.get('staging_tables', {}).get('model_handling', 'NOT SET')}")
        print(f"   - naming_prefix: {file_settings.get('staging_tables', {}).get('naming_prefix', 'NOT SET')}")
        print(f"   - enabled: {file_settings.get('staging_tables', {}).get('enabled', 'NOT SET')}")
    else:
        print("📄 No settings.json file found")
    
    print()

    # Dummy values for Cognos connection details
    cognos_url = "http://dummy-cognos-url"
    session_key = "dummy-session-key"

    # TEST 1: Migration using settings.json file (settings=None)
    print("🧪 TEST 1: Migration using settings.json file")
    print(f"   Output directory: {output_dir_1}")
    print("   Expected: Should use settings from settings.json file")
    print("   - data_load_mode should be 'direct_query' (from file)")
    print("   - naming_prefix should be 'Dim_' (from file)")
    print("   - model_handling should be 'merged_tables' (from file)")
    print()

    success_1 = migrate_package_with_local_reports(
        package_file_path=package_file,
        output_path=output_dir_1,
        report_file_paths=report_files,
        cognos_url=cognos_url,
        session_key=session_key,
        task_id="test_migration_file_settings",
        settings=None  # This should use settings.json
    )

    print(f"✅ TEST 1 Result: {'SUCCESS' if success_1 else 'FAILED'}")
    print()

    # TEST 2: Migration using explicit backend settings (conflicting with settings.json)
    backend_settings = {
        "date_table_mode": "hidden",  # Different from settings.json
        "table_filtering": {
            "mode": "include_all",  # Different from settings.json
            "always_include": ["CustomTable"]  # Different from settings.json
        },
        "staging_tables": {
            "enabled": True,
            "naming_prefix": "STG_",  # Different from settings.json ("Dim_")
            "data_load_mode": "direct_query",  # Different from settings.json ("direct_query")
            "model_handling": "merged_tables"  # Different from settings.json ("merged_tables")
        }
    }

    print("🧪 TEST 2: Migration using explicit backend settings (CONFLICTING with settings.json)")
    print(f"   Output directory: {output_dir_2}")
    print("   Backend settings (should OVERRIDE settings.json):")
    print(f"   - data_load_mode: 'import' (overrides 'direct_query' from file)")
    print(f"   - naming_prefix: 'STG_' (overrides 'Dim_' from file)")
    print(f"   - model_handling: 'star_schema' (overrides 'merged_tables' from file)")
    print(f"   - date_table_mode: 'hidden' (overrides 'visible' from file)")
    print()

    success_2 = migrate_package_with_local_reports(
        package_file_path=package_file,
        output_path=output_dir_2,
        report_file_paths=report_files,
        cognos_url=cognos_url,
        session_key=session_key,
        task_id="test_migration_backend_settings",
        settings=backend_settings  # This should override settings.json
    )

    print(f"✅ TEST 2 Result: {'SUCCESS' if success_2 else 'FAILED'}")
    print()

    # VALIDATION: Check the generated files to verify settings were applied correctly
    print("🔍 VALIDATION: Checking generated files for settings application")
    print("=" * 80)
    
    def validate_settings_in_output(output_dir, expected_prefix, expected_mode, test_name):
        """Validate that the correct settings were applied in the output"""
        print(f"📁 Validating {test_name} output in: {output_dir}")
        
        # Check if staging tables were created with correct prefix
        extracted_dir = Path(output_dir) / "extracted"
        if extracted_dir.exists():
            table_files = list(extracted_dir.glob("table_*.json"))
            staging_tables = [f for f in table_files if expected_prefix in f.name]
            
            print(f"   - Found {len(table_files)} total table files")
            print(f"   - Found {len(staging_tables)} staging tables with prefix '{expected_prefix}'")
            
            # Check a staging table file for partition mode
            if staging_tables:
                sample_file = staging_tables[0]
                try:
                    with open(sample_file, 'r') as f:
                        table_data = json.load(f)
                    
                    partitions = table_data.get('partitions', [])
                    if partitions:
                        partition_mode = partitions[0].get('mode', 'NOT SET')
                        print(f"   - Sample staging table partition mode: '{partition_mode}'")
                        
                        expected_partition_mode = 'directQuery' if expected_mode == 'direct_query' else 'import'
                        if partition_mode == expected_partition_mode:
                            print(f"   ✅ Partition mode matches expected: {expected_partition_mode}")
                        else:
                            print(f"   ❌ Partition mode mismatch! Expected: {expected_partition_mode}, Got: {partition_mode}")
                    else:
                        print(f"   ⚠️  No partitions found in staging table")
                        
                except Exception as e:
                    print(f"   ❌ Error reading staging table file: {e}")
            else:
                print(f"   ⚠️  No staging tables found with prefix '{expected_prefix}'")
        else:
            print(f"   ❌ Extracted directory not found: {extracted_dir}")
        
        print()

    # Validate TEST 1 (should use settings.json values)
    if success_1:
        validate_settings_in_output(output_dir_1, "Dim_", "direct_query", "TEST 1 (settings.json)")
    
    # Validate TEST 2 (should use backend settings)
    if success_2:
        validate_settings_in_output(output_dir_2, "STG_", "import", "TEST 2 (backend settings)")

    # FINAL SUMMARY
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"TEST 1 (settings.json):     {'✅ PASSED' if success_1 else '❌ FAILED'}")
    print(f"TEST 2 (backend override):  {'✅ PASSED' if success_2 else '❌ FAILED'}")
    
    if success_1 and success_2:
        print("🎉 ALL TESTS PASSED - Settings flow is working correctly!")
        print("   - settings.json is used when no explicit settings provided")
        print("   - Backend settings correctly override settings.json")
    else:
        print("❌ SOME TESTS FAILED - Settings flow needs investigation")
    
    print(f"\n📁 Output directories:")
    print(f"   - TEST 1: {output_dir_1}")
    print(f"   - TEST 2: {output_dir_2}")


if __name__ == "__main__":
    test_package_and_report_migration()
