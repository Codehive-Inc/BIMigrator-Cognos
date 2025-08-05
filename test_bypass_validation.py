#!/usr/bin/env python3
"""
Test migration bypassing session validation entirely
"""

import logging
import os
import uuid
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def get_fresh_session_key():
    """Get fresh session key from cognos-explorer"""
    import subprocess
    import sys
    
    try:
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
            session_key = result.stdout.strip().split('\n')[-1]
            if session_key.startswith('CAM'):
                return session_key
        
        print(f"Failed to get session key: {result.stderr}")
        return None
        
    except Exception as e:
        print(f"Error getting session key: {e}")
        return None


def test_migration_bypass_validation():
    """Test migration by completely bypassing session validation"""
    
    print("=== Testing Migration with Session Validation Bypass ===")
    
    # Get fresh session
    session_key = get_fresh_session_key()
    if not session_key:
        print("Failed to get session key")
        return False
    
    print(f"Got session key: {session_key[:20]}...")
    
    # Import the components we need
    from cognos_migrator.config import MigrationConfig, CognosConfig
    from cognos_migrator.config.fallback_config import EnhancedMigrationConfig, ConfigurationManager
    from cognos_migrator.common.websocket_client import logging_helper, set_task_info
    
    # Generate task_id
    task_id = f"enhanced_migration_{uuid.uuid4().hex}"
    set_task_info(task_id, total_steps=18)
    
    logger = logging.getLogger(__name__)
    
    logging_helper(
        message="Starting enhanced migration (validation bypassed)",
        progress=0,
        message_type="info"
    )
    
    try:
        # Initialize enhanced configuration
        logging_helper(
            message="Initializing enhanced migration configuration",
            progress=5,
            message_type="info"
        )
        
        config_manager = ConfigurationManager()
        enhanced_config = config_manager.get_config()
        
        # Create migration config
        migration_config = MigrationConfig(
            output_directory="./output/bypass_test",
            preserve_structure=enhanced_config.preserve_structure,
            include_metadata=enhanced_config.include_metadata,
            generate_documentation=enhanced_config.generate_documentation,
            template_directory=str(Path(__file__).parent / "cognos_migrator" / "templates"),
            llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
            llm_service_enabled=enhanced_config.llm_service_enabled
        )
        
        # Create Cognos config
        cognos_config = CognosConfig(
            base_url="http://20.244.32.126:9300/api/v1",
            auth_key="IBM-BA-Authorization",
            auth_value=session_key,
            session_timeout=3600,
            max_retries=3,
            request_timeout=30
        )
        
        logging_helper(
            message="Configuration initialized successfully",
            progress=10,
            message_type="info"
        )
        
        # Skip enhanced orchestrator, use standard migration directly
        logging_helper(
            message="Using standard migration (bypassing enhanced validation)",
            progress=15,
            message_type="info"
        )
        
        from cognos_migrator.main import migrate_module_with_explicit_session
        success = migrate_module_with_explicit_session(
            module_id="i5F34A7A52E2645C0AB03C34BA50941D7",
            output_path="./output/bypass_test",
            cognos_url="http://20.244.32.126:9300/api/v1",
            session_key=session_key,
            folder_id=None,
            cpf_file_path=None,
            task_id=task_id,
            auth_key="IBM-BA-Authorization"
        )
        
        result = {
            'success': success,
            'module_id': "i5F34A7A52E2645C0AB03C34BA50941D7",
            'output_path': "./output/bypass_test",
            'migration_type': 'standard_bypassed',
            'validation_enabled': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate final report
        if result.get('success', False):
            logging_helper(
                message="Migration completed successfully",
                progress=100,
                message_type="info"
            )
        else:
            logging_helper(
                message="Migration failed",
                progress=100,
                message_type="error"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logging_helper(
            message=f"Migration failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'module_id': "i5F34A7A52E2645C0AB03C34BA50941D7",
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    result = test_migration_bypass_validation()
    print(f"\nFinal result: {result}")
    
    if result.get('success'):
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    else:
        print("❌ MIGRATION FAILED!")
        if 'error' in result:
            print(f"Error: {result['error']}")