#!/usr/bin/env python3
"""
Test enhanced session validation based on Postman collection analysis
"""

import logging
from cognos_migrator.validation.session_validator import SessionValidator, ValidationEndpoint

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_enhanced_validation():
    """Test the enhanced validation with multiple endpoints"""
    
    print("=== Testing Enhanced Session Validation ===")
    
    # Get fresh session key
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
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            session_key = result.stdout.strip().split('\n')[-1]
            if session_key.startswith('CAM'):
                print(f"Got session key: {session_key[:20]}...")
            else:
                print("Failed to get valid session key")
                return
        else:
            print(f"Failed to get session key: {result.stderr}")
            return
            
    except Exception as e:
        print(f"Error getting session key: {e}")
        return
    
    # Test with enhanced validator
    validator = SessionValidator()
    cognos_url = "http://20.244.32.126:9300/api/v1"
    
    print(f"\nTesting session validation for: {cognos_url}")
    print(f"Session key: {session_key[:20]}...")
    
    # Test with different preferred endpoints
    test_endpoints = [
        ValidationEndpoint.CONTENT,
        ValidationEndpoint.MODULES,
        ValidationEndpoint.CAPABILITIES,
        ValidationEndpoint.SESSION
    ]
    
    for endpoint in test_endpoints:
        print(f"\n--- Testing with preferred endpoint: {endpoint.value} ---")
        result = validator.validate_session(cognos_url, session_key, preferred_endpoint=endpoint)
        
        print(f"Valid: {result['valid']}")
        print(f"Endpoint used: {result['endpoint_used']}")
        print(f"Status code: {result['status_code']}")
        if result['error']:
            print(f"Error: {result['error']}")
        
        print("Endpoints tried:")
        for ep in result['endpoints_tried']:
            print(f"  {ep['endpoint']}: {ep['status']}")
        
        if result['session_info']:
            print(f"Session info: {result['session_info']}")
        
        # If we found a valid endpoint, test module access
        if result['valid']:
            module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
            can_access = validator.test_module_access(cognos_url, session_key, module_id)
            print(f"Can access module {module_id}: {can_access}")
            break
    
    # Test the updated client method
    print("\n=== Testing Updated Client Method ===")
    from cognos_migrator.client import CognosClient
    
    is_valid = CognosClient.test_connection_with_session(cognos_url, session_key)
    print(f"CognosClient.test_connection_with_session result: {is_valid}")
    
    # Test with invalid session
    print("\n=== Testing with Invalid Session ===")
    invalid_key = "CAM INVALID_SESSION_KEY"
    is_valid = CognosClient.test_connection_with_session(cognos_url, invalid_key)
    print(f"Invalid session test result: {is_valid} (should be False)")


if __name__ == "__main__":
    test_enhanced_validation()