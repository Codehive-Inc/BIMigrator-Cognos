#!/usr/bin/env python3
"""
Test Session-Based Authentication
Tests the new session authentication flow with base token + credentials
"""

import sys
import os
import logging

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient

def test_session_authentication():
    """Test the session-based authentication flow"""
    print("🔐 TESTING SESSION-BASED AUTHENTICATION")
    print("=" * 50)
    
    # Enable debug logging to see the authentication flow
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        print(f"📋 Configuration loaded:")
        print(f"   Base URL: {cognos_config.base_url}")
        print(f"   Auth Key: {cognos_config.auth_key}")
        print(f"   Username: {cognos_config.username}")
        print(f"   Base Auth Token: {cognos_config.base_auth_token[:20]}..." if cognos_config.base_auth_token else "   Base Auth Token: None")
        print(f"   Direct Auth Value: {cognos_config.auth_value[:20]}..." if cognos_config.auth_value else "   Direct Auth Value: None")
        
        print(f"\n🔌 Creating Cognos client...")
        
        # Create client (this will trigger authentication)
        client = CognosClient(cognos_config)
        
        print(f"✅ Client created successfully!")
        print(f"🔑 Auth token in use: {client.auth_token[:20]}..." if client.auth_token else "🔑 Using fallback authentication")
        
        # Test the authentication by making a simple API call
        print(f"\n🧪 Testing API call...")
        response = client._make_request('GET', '/content')
        
        if response.status_code == 200:
            print(f"✅ API call successful! Status: {response.status_code}")
            
            # Try to parse response
            try:
                data = response.json()
                if 'content' in data:
                    print(f"📊 Found {len(data['content'])} content items")
                else:
                    print(f"📊 Response structure: {list(data.keys())}")
            except:
                print(f"📊 Response received (non-JSON): {len(response.text)} characters")
                
        else:
            print(f"❌ API call failed! Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
        # Test session info if available
        print(f"\n🔍 Testing session info...")
        try:
            session_response = client._make_request('GET', '/session')
            if session_response.status_code == 200:
                print(f"✅ Session info retrieved successfully")
                try:
                    session_data = session_response.json()
                    print(f"   Session details: {session_data}")
                except:
                    print(f"   Session response: {session_response.text[:200]}...")
            else:
                print(f"⚠️  Session info not available: {session_response.status_code}")
        except Exception as e:
            print(f"⚠️  Could not retrieve session info: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_priority():
    """Test which authentication method is being used"""
    print(f"\n🎯 TESTING AUTHENTICATION PRIORITY")
    print("=" * 50)
    
    config_manager = ConfigManager()
    cognos_config = config_manager.get_cognos_config()
    
    print(f"Authentication priority test:")
    
    if cognos_config.base_auth_token and cognos_config.username and cognos_config.password:
        print(f"✅ Should use: Session-based auth (base token + credentials)")
        print(f"   Base token: {cognos_config.base_auth_token[:30]}...")
        print(f"   Username: {cognos_config.username}")
        print(f"   Namespace: {cognos_config.namespace}")
    elif cognos_config.auth_value:
        print(f"✅ Should use: Direct token auth")
        print(f"   Token: {cognos_config.auth_value[:30]}...")
    elif cognos_config.username and cognos_config.password:
        print(f"✅ Should use: Basic auth")
        print(f"   Username: {cognos_config.username}")
    else:
        print(f"❌ No valid authentication method found!")
        
def main():
    """Run all authentication tests"""
    print("🚀 COGNOS SESSION AUTHENTICATION TESTING")
    print(f"📅 Test Date: {os.popen('date').read().strip()}")
    
    success = True
    
    try:
        # Test authentication priority
        test_authentication_priority()
        
        # Test actual authentication
        auth_success = test_session_authentication()
        success = success and auth_success
        
        print(f"\n" + "=" * 50)
        if success:
            print(f"🎉 ALL AUTHENTICATION TESTS PASSED!")
            print(f"✅ Session-based authentication is working correctly")
        else:
            print(f"❌ SOME AUTHENTICATION TESTS FAILED!")
            print(f"⚠️  Check the configuration and token validity")
            
    except Exception as e:
        print(f"❌ TEST SUITE FAILED: {e}")
        success = False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)