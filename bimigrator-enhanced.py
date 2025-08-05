#\!/usr/bin/env python3
"""
BIMigrator Enhanced CLI
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project to the path
sys.path.append(str(Path(__file__).parent))

try:
    from cognos_migrator.enhanced_main import (
        test_cognos_connection_enhanced,
        migrate_module_with_enhanced_validation
    )
    from cognos_migrator.client import CognosClient, CognosAPIError
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)


def get_session_key():
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
        raise Exception(f"Failed to generate session key: {e}")


def cmd_get_session(args):
    """Get a fresh session key"""
    try:
        print("🔐 Generating fresh session key...")
        session_key = get_session_key()
        print(f"✅ Session key: {session_key}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_migrate_module(args):
    """Migrate a Cognos module"""
    session_key = args.session_key
    
    # Handle empty session key
    if not session_key or session_key.strip() == '""' or session_key.strip() == "''":
        try:
            print("🔐 Generating fresh session key...")
            session_key = get_session_key()
            print(f"✅ Generated session key: {session_key[:30]}...")
        except Exception as e:
            print(f"❌ Error generating session key: {e}")
            return 1
    
    try:
        print("🚀 Starting Enhanced Module Migration")
        print(f"   📋 Module ID: {args.module_id}")
        print(f"   📁 Output Path: {args.output_path}")
        print(f"   🌐 Cognos URL: {args.cognos_url}")
        print(f"   ✨ Enhanced Validation: {'✅' if args.enable_enhanced_validation else '❌'}")
        print()
        
        result = migrate_module_with_enhanced_validation(
            module_id=args.module_id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=session_key,
            enable_enhanced_validation=args.enable_enhanced_validation
        )
        
        print("="*60)
        print("📊 MIGRATION RESULTS")
        print("="*60)
        print(f"✨ Success: {'✅' if result['success'] else '❌'}")
        print(f"📋 Module ID: {result['module_id']}")
        print(f"📁 Output Path: {result['output_path']}")
        print(f"🔧 Type: {result['migration_type']}")
        print(f"⏰ Timestamp: {result['timestamp']}")
        
        if result['success']:
            print(f"\n🎉 Migration completed successfully\!")
            return 0
        else:
            print(f"\n💥 Migration failed\!")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="BIMigrator Enhanced")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # get-session command
    get_session_parser = subparsers.add_parser('get-session')
    
    # migrate-module command
    migrate_parser = subparsers.add_parser('migrate-module')
    migrate_parser.add_argument('--module-id', required=True)
    migrate_parser.add_argument('--output-path', required=True)
    migrate_parser.add_argument('--cognos-url', default='http://20.244.32.126:9300/api/v1')
    migrate_parser.add_argument('--session-key', default='')
    migrate_parser.add_argument('--enable-enhanced-validation', action='store_true')
    migrate_parser.add_argument('--verbose', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'get-session':
        return cmd_get_session(args)
    elif args.command == 'migrate-module':
        return cmd_migrate_module(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())