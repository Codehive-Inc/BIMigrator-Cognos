#!/usr/bin/env python3
"""
Command-line interface for testing enhanced migration

Usage:
    python test_enhanced_migration_cli.py [options]

Examples:
    # Test with session key
    python test_enhanced_migration_cli.py --session-key "CAM ..." --module-id "i5F34A7A52E2645C0AB03C34BA50941D7"
    
    # Test with fresh session generation
    python test_enhanced_migration_cli.py --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" --generate-session
    
    # Quick connection test only
    python test_enhanced_migration_cli.py --test-connection-only
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add the project to the path
sys.path.append(str(Path(__file__).parent))

from cognos_migrator.enhanced_main import (
    test_cognos_connection_enhanced,
    migrate_module_with_enhanced_validation
)


def get_fresh_session_key():
    """Generate a fresh session key"""
    try:
        sys.path.append('/Users/prithirajsengupta/cognos-explorer')
        from explorer.config import CognosConfig
        from explorer.client import CognosClient
        from dotenv import load_dotenv

        load_dotenv('/Users/prithirajsengupta/cognos-explorer/.env')

        config = CognosConfig(
            base_url=os.getenv('COGNOS_BASE_URL'),
            auth_key=os.getenv('COGNOS_AUTH_KEY'),
            username=os.getenv('COGNOS_USERNAME'),
            password=os.getenv('COGNOS_PASSWORD'),
            namespace=os.getenv('COGNOS_NAMESPACE', 'CognosEx'),
            base_auth_token=os.getenv('COGNOS_BASE_AUTH_TOKEN', '').strip('\\"')
        )

        client = CognosClient(config)
        session_info = client.get_session_info()
        return client.auth_token
        
    except Exception as e:
        print(f"❌ Failed to generate session key: {e}")
        return None


def test_connection(cognos_url, session_key, enable_validation=True):
    """Test connection with enhanced validation"""
    print("🔍 Testing enhanced connection...")
    
    result = test_cognos_connection_enhanced(
        cognos_url=cognos_url,
        session_key=session_key,
        enable_validation=enable_validation
    )
    
    print(f"📊 Connection Test Results:")
    print(f"   Connection Valid: {'✅' if result['connection_valid'] else '❌'}")
    print(f"   Validation Framework: {'✅' if result['validation_framework_available'] else '❌'}")
    print(f"   Fallback Strategy: {'✅' if result['fallback_strategy_available'] else '❌'}")
    print(f"   Reporters: {'✅' if result['reporters_available'] else '❌'}")
    print(f"   Enhanced Converters: {'✅' if result['enhanced_converters_available'] else '❌'}")
    
    return result['connection_valid']


def run_migration(module_id, output_path, cognos_url, session_key, enable_validation=True, validation_config=None):
    """Run the enhanced migration"""
    print(f"🚀 Starting enhanced migration for module: {module_id}")
    
    result = migrate_module_with_enhanced_validation(
        module_id=module_id,
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key,
        enable_enhanced_validation=enable_validation,
        validation_config=validation_config or {}
    )
    
    print(f"📋 Migration Results:")
    print(f"   Success: {'✅' if result['success'] else '❌'}")
    print(f"   Module ID: {result['module_id']}")
    print(f"   Output Path: {result['output_path']}")
    print(f"   Migration Type: {result['migration_type']}")
    print(f"   Validation Enabled: {result['validation_enabled']}")
    
    if 'config' in result:
        print(f"   Config:")
        for key, value in result['config'].items():
            print(f"     {key}: {value}")
    
    if 'error' in result:
        print(f"   ❌ Error: {result['error']}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Migration Testing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --session-key "CAM ..." --module-id "i5F34A7A52E2645C0AB03C34BA50941D7"
  %(prog)s --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" --generate-session
  %(prog)s --test-connection-only --generate-session
  %(prog)s --quick-test
        """
    )
    
    # Connection parameters
    parser.add_argument('--cognos-url', 
                       default='http://20.244.32.126:9300/api/v1',
                       help='Cognos Analytics URL (default: http://20.244.32.126:9300/api/v1)')
    
    parser.add_argument('--session-key',
                       help='Cognos session key (CAM token)')
    
    parser.add_argument('--generate-session', 
                       action='store_true',
                       help='Generate a fresh session key automatically')
    
    # Migration parameters
    parser.add_argument('--module-id',
                       default='i5F34A7A52E2645C0AB03C34BA50941D7',
                       help='Cognos module ID to migrate (default: i5F34A7A52E2645C0AB03C34BA50941D7)')
    
    parser.add_argument('--output-path',
                       default='./output/cli_test',
                       help='Output directory for migration (default: ./output/cli_test)')
    
    # Testing options
    parser.add_argument('--test-connection-only',
                       action='store_true',
                       help='Only test connection, do not run migration')
    
    parser.add_argument('--disable-validation',
                       action='store_true',
                       help='Disable enhanced validation')
    
    parser.add_argument('--quick-test',
                       action='store_true',
                       help='Run a quick test with session generation and connection test')
    
    # Validation configuration
    parser.add_argument('--validation-config',
                       help='JSON string with validation configuration')
    
    # Output options
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Verbose output')
    
    parser.add_argument('--json-output',
                       action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Handle quick test mode
    if args.quick_test:
        print("⚡ Quick Test Mode")
        session_key = get_fresh_session_key()
        if session_key:
            print(f"✅ Generated session key: {session_key[:30]}...")
            connection_valid = test_connection(args.cognos_url, session_key)
            if connection_valid:
                print("✅ Quick test successful!")
            else:
                print("❌ Quick test failed!")
        else:
            print("❌ Could not generate session key")
        return
    
    # Determine session key
    session_key = args.session_key
    
    if args.generate_session or not session_key:
        print("🔐 Generating fresh session key...")
        session_key = get_fresh_session_key()
        if not session_key:
            print("❌ Failed to generate session key. Exiting.")
            return 1
        print(f"✅ Generated session key: {session_key[:30]}...")
    
    # Parse validation config
    validation_config = None
    if args.validation_config:
        try:
            validation_config = json.loads(args.validation_config)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid validation config JSON: {e}")
            return 1
    
    # Test connection
    connection_valid = test_connection(
        args.cognos_url, 
        session_key, 
        enable_validation=not args.disable_validation
    )
    
    if not connection_valid:
        print("❌ Connection test failed. Exiting.")
        return 1
    
    # Run migration if requested
    if not args.test_connection_only:
        result = run_migration(
            module_id=args.module_id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=session_key,
            enable_validation=not args.disable_validation,
            validation_config=validation_config
        )
        
        if args.json_output:
            print(json.dumps(result, indent=2))
        
        return 0 if result['success'] else 1
    
    print("✅ Connection test completed successfully!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)