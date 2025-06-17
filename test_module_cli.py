#!/usr/bin/env python3
"""
Command-line test for module migration
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a command and print output"""
    print(f"\nRunning: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def test_cli_commands():
    """Test the CLI commands"""
    print("Testing Module Migration CLI Commands")
    print("=" * 60)
    
    # Test 1: Show usage
    print("\n1. Testing help/usage display:")
    run_command(["python", "-m", "cognos_migrator.main"])
    
    # Test 2: Validate prerequisites
    print("\n2. Testing validate command:")
    run_command(["python", "-m", "cognos_migrator.main", "validate"])
    
    # Test 3: List available content
    print("\n3. Testing list command:")
    run_command(["python", "-m", "cognos_migrator.main", "list"])
    
    # Test 4: Test module migration (with dummy IDs)
    print("\n4. Testing migrate-module command (will fail with dummy IDs):")
    run_command([
        "python", "-m", "cognos_migrator.main", 
        "migrate-module", 
        "dummy_module_id", 
        "dummy_folder_id",
        "/tmp/test_module_output"
    ])


def test_python_api():
    """Test the Python API directly"""
    print("\n\nTesting Python API")
    print("=" * 60)
    
    # Add the project to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Test importing
    print("\n1. Testing imports...")
    try:
        from cognos_migrator.main import migrate_module, migrate_module_with_session_key
        print("✓ Successfully imported migrate_module and migrate_module_with_session_key")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return
    
    # Test function signatures
    print("\n2. Testing function signatures...")
    import inspect
    
    # Check migrate_module
    sig = inspect.signature(migrate_module)
    print(f"migrate_module signature: {sig}")
    params = list(sig.parameters.keys())
    expected_params = ['module_id', 'folder_id', 'output_path']
    if params == expected_params:
        print("✓ migrate_module has correct parameters")
    else:
        print(f"✗ Expected parameters {expected_params}, got {params}")
    
    # Check migrate_module_with_session_key
    sig = inspect.signature(migrate_module_with_session_key)
    print(f"\nmigrate_module_with_session_key signature: {sig}")
    params = list(sig.parameters.keys())
    expected_params = ['module_id', 'cognos_url', 'session_key', 'folder_id', 'output_path']
    if params == expected_params:
        print("✓ migrate_module_with_session_key has correct parameters")
    else:
        print(f"✗ Expected parameters {expected_params}, got {params}")


def main():
    """Main test function"""
    print("Module Migration Test Suite")
    print("=" * 60)
    
    # Check environment
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print("✓ .env file found")
    else:
        print("✗ .env file not found - tests may fail")
    
    # Run tests
    test_cli_commands()
    test_python_api()
    
    print("\n\nTest Summary")
    print("=" * 60)
    print("To run actual migrations:")
    print("1. Ensure .env file is configured properly")
    print("2. Get valid module and folder IDs using: python -m cognos_migrator.main list")
    print("3. Run: python -m cognos_migrator.main migrate-module <module_id> <folder_id>")
    print("\nOr use the test script:")
    print("python test_module_migration.py")


if __name__ == "__main__":
    main()