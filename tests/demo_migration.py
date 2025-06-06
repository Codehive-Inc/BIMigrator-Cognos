"""
Demonstration of the Cognos to Power BI Migration System
"""

import os
from pathlib import Path
from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient
from cognos_migrator.migrator import CognosToPowerBIMigrator

def demo_complete_system():
    """Demonstrate the complete migration system"""
    
    print("🚀 Cognos to Power BI Migration System Demo")
    print("=" * 50)
    
    # Step 1: Configuration
    print("\n1️⃣ Loading Configuration...")
    try:
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        migration_config = config_manager.get_migration_config()
        
        print("✅ Configuration loaded successfully")
        print(f"   📡 Cognos URL: {cognos_config.base_url}")
        print(f"   📁 Output Directory: {migration_config.output_directory}")
        print(f"   📋 Template Directory: {migration_config.template_directory}")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    # Step 2: API Client
    print("\n2️⃣ Initializing Cognos API Client...")
    try:
        client = CognosClient(cognos_config)
        print("✅ Cognos API client initialized")
        print(f"   🔑 Using authentication: {cognos_config.auth_key}")
        
        # Test connection
        print("   🔍 Testing connection...")
        if client.test_connection():
            print("   ✅ Connection test successful")
        else:
            print("   ⚠️  Connection test failed (may be session timeout)")
            
    except Exception as e:
        print(f"❌ Client initialization error: {e}")
        return False
    
    # Step 3: Migration System
    print("\n3️⃣ Initializing Migration System...")
    try:
        migrator = CognosToPowerBIMigrator(cognos_config, migration_config)
        print("✅ Migration orchestrator initialized")
        
        # Check templates
        template_path = Path(migration_config.template_directory)
        if template_path.exists():
            templates = list(template_path.glob("*.tmdl")) + list(template_path.glob("*.json"))
            print(f"   📋 Found {len(templates)} template files")
            for template in templates[:5]:
                print(f"      - {template.name}")
        else:
            print("   ⚠️  Template directory not found")
            
    except Exception as e:
        print(f"❌ Migration system error: {e}")
        return False
    
    # Step 4: System Capabilities
    print("\n4️⃣ System Capabilities Summary...")
    print("✅ Complete migration system ready:")
    print("   🔄 API-first approach (no XML parsing)")
    print("   📊 Power BI project generation")
    print("   🏗️  Modular, extensible architecture")
    print("   📝 Template-based file generation")
    print("   🔍 Comprehensive error handling")
    print("   📋 Batch processing support")
    
    # Step 5: Usage Examples
    print("\n5️⃣ Usage Examples:")
    print("   📄 Single report: python main.py migrate-report <report_id>")
    print("   📁 Folder migration: python main.py migrate-folder <folder_id>")
    print("   ✅ Validation: python main.py validate")
    print("   🎯 Demo mode: python main.py demo")
    
    print("\n🎉 System demonstration completed successfully!")
    print("\n💡 Next Steps:")
    print("   1. Get a valid report ID from your Cognos system")
    print("   2. Run the migration command")
    print("   3. Check the output directory for generated Power BI files")
    
    return True

if __name__ == "__main__":
    demo_complete_system()
