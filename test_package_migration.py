import os
from cognos_migrator.migrations.package import migrate_package_with_explicit_session

def test_package_migration_from_file():
    """
    Tests the migration of a Cognos Framework Manager package from a local XML file.
    """
    # Path to the package XML file to be migrated
    package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
    
    # Directory where the migration output will be saved
    output_dir = "test_output/package_migration_output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Cognos connection details (required even for file-based migration)
    cognos_url = "http://localhost:9300"
    session_key = "CAM MTsxMDE6ZjE1OWUyNmYtNTE4Mi05YTg0LWI5YWEtNjAxZWEyMDM4YzA5OjE2ODk1NzM1MDA7MDszOzA7"

    print(f"Starting migration for package file: {package_file}")

    # Call the migration function with the package file path
    success = migrate_package_with_explicit_session(
        package_file_path=package_file,
        output_path=output_dir,
        cognos_url=cognos_url,
        session_key=session_key
    )

    if success:
        print(f"Package migration from file '{package_file}' completed successfully.")
        print(f"Output saved in: {output_dir}")
    else:
        print(f"Package migration from file '{package_file}' failed.")

if __name__ == "__main__":
    print("--- Running Test: Basic Package Migration from File ---")
    test_package_migration_from_file() 