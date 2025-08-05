#!/usr/bin/env python3
"""
BIMigrator Enhanced Demo Script

This script demonstrates the enhanced migration functionality
exactly as requested in the format:

./bimigrator-enhanced migrate-module \
    --module-id "i5F34A7A52E2645C0AB03C34BA50941D7" \
    --output-path "./output/my_module" \
    --cognos-url "http://20.244.32.126:9300/api/v1" \
    --session-key "" \
    --enable-enhanced-validation \
    --verbose
"""

import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

def get_session_key():
    """Generate a fresh session key"""
    try:
        sys.path.append('/Users/prithirajsengupta/cognos-explorer')
        from explorer.config import CognosConfig
        from explorer.client import CognosClient
        from dotenv import load_dotenv
        import os

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


def run_enhanced_migration():
    """Run the enhanced migration demonstration"""
    
    print("🚀 BIMigrator Enhanced - Demo")
    print("="*50)
    print("Simulating command:")
    print("./bimigrator-enhanced migrate-module \\")
    print("    --module-id \"i5F34A7A52E2645C0AB03C34BA50941D7\" \\")
    print("    --output-path \"./output/my_module\" \\")
    print("    --cognos-url \"http://20.244.32.126:9300/api/v1\" \\")
    print("    --session-key \"\" \\")
    print("    --enable-enhanced-validation \\")
    print("    --verbose")
    print("="*50)
    print()
    
    # Step 1: Get session key (since --session-key "" was provided)
    print("🔐 Step 1: Getting session key (--session-key was empty)")
    try:
        session_key = get_session_key()
        print(f"✅ Generated session key: {session_key[:30]}...")
    except Exception as e:
        print(f"❌ Failed to get session key: {e}")
        return 1
    
    # Step 2: Run enhanced migration
    print("\n🚀 Step 2: Running enhanced migration")
    try:
        from cognos_migrator.enhanced_main import migrate_module_with_enhanced_validation
        
        result = migrate_module_with_enhanced_validation(
            module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
            output_path="./output/my_module",
            cognos_url="http://20.244.32.126:9300/api/v1",
            session_key=session_key,
            enable_enhanced_validation=True,
            validation_config=None
        )
        
        # Step 3: Display results
        print("\n" + "="*60)
        print("📊 ENHANCED MIGRATION RESULTS")
        print("="*60)
        print(f"✨ Success: {'✅' if result['success'] else '❌'}")
        print(f"📋 Module ID: {result['module_id']}")
        print(f"📁 Output Path: {result['output_path']}")
        print(f"🔧 Migration Type: {result['migration_type']}")
        print(f"✅ Validation Enabled: {result['validation_enabled']}")
        print(f"⏰ Timestamp: {result['timestamp']}")
        
        if 'config' in result:
            print(f"\n🔧 Enhanced Configuration:")
            for key, value in result['config'].items():
                print(f"   • {key}: {value}")
        
        if result['success']:
            print(f"\n🎉 Enhanced migration completed successfully!")
            print(f"📁 Output files generated in: {result['output_path']}")
            print("\n💡 Key Features Demonstrated:")
            print("   ✅ Auto session key generation")
            print("   ✅ Enhanced validation framework")
            print("   ✅ Multi-endpoint session validation")
            print("   ✅ Fallback strategies for LLM service")
            print("   ✅ Comprehensive error handling")
            return 0
        else:
            print(f"\n💥 Enhanced migration failed!")
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            return 1
            
    except Exception as e:
        print(f"❌ Migration Error: {e}")
        return 1


if __name__ == "__main__":
    print("🌟 Welcome to BIMigrator Enhanced Demo!")
    print("This demonstrates the exact command you requested.\n")
    
    exit_code = run_enhanced_migration()
    
    print("\n" + "="*60)
    if exit_code == 0:
        print("✅ Demo completed successfully!")
    else:
        print("❌ Demo encountered errors.")
    print("="*60)
    
    sys.exit(exit_code)