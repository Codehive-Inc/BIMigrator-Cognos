#!/usr/bin/env python3
"""
Test direct migration bypassing session validation
"""

import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_direct_migration():
    """Test migration directly without upfront session validation"""
    
    print("=== Testing Direct Migration ===")
    
    # Get fresh session key from cognos-explorer
    print("Getting fresh session key...")
    
    import subprocess
    import sys
    
    try:
        # Run the session key extraction
        result = subprocess.run([
            sys.executable, '-c', '''
import sys
sys.path.append("/Users/prithirajsengupta/cognos-explorer")
from explorer.config import CognosConfig
from explorer.client import CognosClient
import os
from dotenv import load_dotenv

load_dotenv("/Users/prithirajsengupta/cognos-explorer/.env")

config = CognosConfig(
    base_url=os.getenv("COGNOS_BASE_URL"),
    auth_key=os.getenv("COGNOS_AUTH_KEY"),
    username=os.getenv("COGNOS_USERNAME"),
    password=os.getenv("COGNOS_PASSWORD"),
    namespace=os.getenv("COGNOS_NAMESPACE", "CognosEx"),
    base_auth_token=os.getenv("COGNOS_BASE_AUTH_TOKEN", "").strip('\\"')
)

try:
    client = CognosClient(config)
    session_info = client.get_session_info()
    print(client.auth_token)
except Exception as e:
    print(f"ERROR: {e}")
'''
        ], capture_output=True, text=True, cwd="/Users/prithirajsengupta/codehivesolutions/cognos/BIMigrator-Cognos")
        
        if result.returncode == 0:
            session_key = result.stdout.strip().split('\n')[-1]  # Get last line
            if session_key.startswith('CAM'):
                print(f"Got session key: {session_key[:20]}...")
            else:
                print("Failed to get valid session key")
                return False
        else:
            print(f"Failed to get session key: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error getting session key: {e}")
        return False
    
    # Now test migration bypassing validation
    print("\n=== Testing Enhanced Migration ===")
    
    try:
        # Import without triggering session validation
        from cognos_migrator.config import MigrationConfig, CognosConfig
        from cognos_migrator.config.fallback_config import EnhancedMigrationConfig, ConfigurationManager
        from cognos_migrator.enhanced_migration_orchestrator import EnhancedMigrationOrchestrator
        
        # Create configs without session validation
        migration_config = MigrationConfig(
            output_directory="./output/test_module",
            preserve_structure=True,
            include_metadata=True,
            generate_documentation=True,
            template_directory=str(Path(__file__).parent / "cognos_migrator" / "templates"),
            llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
            llm_service_enabled=True
        )
        
        cognos_config = CognosConfig(
            base_url="http://20.244.32.126:9300/api/v1",
            auth_key="IBM-BA-Authorization",
            auth_value=session_key,
            session_timeout=3600,
            max_retries=3,
            request_timeout=30
        )
        
        print("Configs created successfully")
        
        # Test enhanced orchestrator initialization
        logger = logging.getLogger(__name__)
        orchestrator = EnhancedMigrationOrchestrator(
            config_file_path=None,
            llm_service_client=None,
            logger=logger
        )
        
        print("Enhanced orchestrator created successfully")
        
        # Test template engine directly first
        from cognos_migrator.generators.template_engine import TemplateEngine
        template_engine = TemplateEngine(migration_config.template_directory)
        print(f"Template engine loaded {len(template_engine.templates)} templates")
        
        # Now try the migration (this might fail due to session, but we'll see where)
        print("\n=== Attempting Migration ===")
        result = orchestrator.migrate_module_with_validation(
            module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
            output_path="./output/test_module"
        )
        
        print(f"Migration result: {result}")
        return result.get('success', False)
        
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_migration()
    print(f"\nOverall result: {'SUCCESS' if success else 'FAILED'}")