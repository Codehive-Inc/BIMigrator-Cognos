#!/usr/bin/env python3
"""
Test script using real Cognos Analytics API data
Fetches actual module data from the specified endpoint and generates Table.tmdl
"""

import os
import json
import logging
from pathlib import Path

from cognos_migrator.config import CognosConfig
from cognos_migrator.client import CognosClient
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import TemplateEngine


def setup_logging():
    """Setup detailed logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_real_config():
    """Load real Cognos configuration from environment"""
    config = CognosConfig(
        base_url=os.getenv('COGNOS_BASE_URL'),
        username=os.getenv('COGNOS_USERNAME'),
        password=os.getenv('COGNOS_PASSWORD'),
        namespace=os.getenv('COGNOS_NAMESPACE', 'LDAP'),
        auth_key=os.getenv('COGNOS_AUTH_KEY', 'IBM-BA-Authorization'),
        auth_value=os.getenv('COGNOS_AUTH_VALUE')
    )
    
    # Validate required configuration
    if not config.base_url:
        raise ValueError("COGNOS_BASE_URL environment variable is required")
    if not config.auth_value and not (config.username and config.password):
        raise ValueError("Either COGNOS_AUTH_VALUE or COGNOS_USERNAME/PASSWORD is required")
    
    return config


def test_real_api():
    """Test with real Cognos Analytics API"""
    
    print("🚀 Testing Real Cognos Analytics API")
    print("=" * 60)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load real configuration
        config = load_real_config()
        print(f"📡 Connecting to: {config.base_url}")
        
        # Create client
        client = CognosClient(config)
        
        # Test connection
        print("🔍 Testing connection...")
        if not client.test_connection():
            print("❌ Failed to connect to Cognos Analytics")
            print("Please check your credentials in .env file")
            return False
        
        print("✅ Connected to Cognos Analytics successfully")
        
        # Get session info
        try:
            session_info = client.get_session_info()
            print(f"👤 Session user: {session_info.get('session_key', 'Unknown')[:20]}...")
        except Exception as e:
            logger.warning(f"Could not get session info: {e}")
        
        # Create module parser
        parser = CognosModuleParser(client)
        
        # List available modules first
        print("\n📋 Listing available modules...")
        try:
            modules = client.list_modules()
            print(f"Found {len(modules)} modules:")
            
            for i, module in enumerate(modules[:10]):  # Show first 10
                module_id = module.get('id', 'N/A')
                module_name = module.get('name') or module.get('defaultName') or 'Unknown'
                print(f"  {i+1:2d}. {module_name} (ID: {module_id})")
                
        except Exception as e:
            logger.error(f"Failed to list modules: {e}")
            print("⚠️  Could not list modules, proceeding with target module...")
        
        # Target module ID from your specification
        target_module_id = "iA1C3A12631D84E428678FE1CC2E69C6B"
        print(f"\n🎯 Fetching target module: {target_module_id}")
        
        # Fetch real module data
        try:
            print("📥 Fetching module metadata...")
            module_data = parser.fetch_module(target_module_id)
            
            print("✅ Module data fetched successfully")
            print(f"📊 Module keys: {list(module_data.keys())}")
            
            # Show basic module info
            module_name = module_data.get('name') or module_data.get('defaultName') or 'Unknown'
            print(f"📋 Module name: {module_name}")
            
            # Parse the real module data
            print("\n🔄 Parsing module data...")
            module_table = parser.parse_module_to_table(module_data)
            
            print(f"✅ Parsed module: {module_table.name}")
            print(f"   📋 Columns: {len(module_table.columns)}")
            print(f"   📈 Measures: {len(module_table.measures)}")
            
            # Show column details
            if module_table.columns:
                print("\n📋 Column Details:")
                for i, col in enumerate(module_table.columns[:10]):  # Show first 10
                    print(f"   {i+1:2d}. {col.name} ({col.data_type}) - {col.summarize_by or 'none'}")
                if len(module_table.columns) > 10:
                    print(f"   ... and {len(module_table.columns) - 10} more columns")
            
            # Show measure details
            if module_table.measures:
                print("\n📈 Measure Details:")
                for i, measure in enumerate(module_table.measures):
                    print(f"   {i+1:2d}. {measure.name}: {measure.expression}")
            
            # Generate JSON for template
            print("\n🔧 Generating JSON for template...")
            table_json = parser.generate_table_json(module_table)
            
            # Create output directory
            output_dir = Path("output/real_api_test")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save JSON file
            json_file = output_dir / f"{module_table.name}_real_data.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(table_json, f, indent=2)
            
            print(f"💾 Real API JSON saved to: {json_file}")
            
            # Generate TMDL file
            try:
                print("\n📄 Generating TMDL file...")
                template_engine = TemplateEngine("bimigrator/templates")
                tmdl_content = template_engine.render('Table', table_json)
                
                # Save TMDL file
                tmdl_file = output_dir / f"{module_table.name}_real_data.tmdl"
                with open(tmdl_file, 'w', encoding='utf-8') as f:
                    f.write(tmdl_content)
                
                print(f"📄 Real API TMDL saved to: {tmdl_file}")
                
                # Show preview
                print("\n📖 TMDL Preview (first 15 lines):")
                lines = tmdl_content.split('\n')
                for i, line in enumerate(lines[:15]):
                    print(f"   {i+1:2d}: {line}")
                
                if len(lines) > 15:
                    print(f"   ... ({len(lines) - 15} more lines)")
                
            except Exception as e:
                logger.error(f"Template rendering failed: {e}")
                print(f"❌ TMDL generation failed: {e}")
            
            # Save raw module data for inspection
            raw_data_file = output_dir / f"{module_table.name}_raw_module_data.json"
            with open(raw_data_file, 'w', encoding='utf-8') as f:
                json.dump(module_data, f, indent=2)
            
            print(f"🔍 Raw module data saved to: {raw_data_file}")
            
            print("\n✅ Real API test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch/parse module {target_module_id}: {e}")
            print(f"❌ Module processing failed: {e}")
            
            # Try to get more specific error info
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                print(f"   HTTP Status: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Response text: {e.response.text[:200]}...")
            
            return False
            
    except Exception as e:
        logger.error(f"Real API test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Close client connection
        try:
            client.close()
        except:
            pass


def show_environment_help():
    """Show help for setting up environment variables"""
    
    print("\n" + "=" * 60)
    print("🔧 Environment Setup Required")
    print("=" * 60)
    
    print("""
To run this test with real Cognos Analytics API, set these environment variables in your .env file:

# Cognos Analytics Server Configuration
COGNOS_BASE_URL=https://your-cognos-server.com/api/v1
COGNOS_USERNAME=your_username
COGNOS_PASSWORD=your_password
COGNOS_NAMESPACE=your_namespace  # e.g., LDAP, AD, etc.

# Alternative: Use direct authentication token
COGNOS_AUTH_KEY=IBM-BA-Authorization
COGNOS_AUTH_VALUE=your_auth_token

# Example .env file:
COGNOS_BASE_URL=https://cognos.example.com:9300/api/v1
COGNOS_USERNAME=admin
COGNOS_PASSWORD=password123
COGNOS_NAMESPACE=LDAP

The test will:
1. Connect to your real Cognos Analytics server
2. Fetch the actual module: iA1C3A12631D84E428678FE1CC2E69C6B
3. Parse the real module structure (columns, measures, etc.)
4. Generate JSON mapping for the Table.tmdl template
5. Create a real TMDL file with actual data

Make sure your Cognos server is accessible and the module ID exists.
""")


if __name__ == "__main__":
    # Check if environment is configured
    if not os.getenv('COGNOS_BASE_URL'):
        print("⚠️  Environment not configured for real API testing")
        show_environment_help()
        print("\nRunning with current environment anyway...")
    
    success = test_real_api()
    
    if not success:
        print("\n" + "=" * 60)
        print("💡 Troubleshooting Tips")
        print("=" * 60)
        print("""
1. Verify your Cognos server URL is correct and accessible
2. Check your username/password or auth token
3. Ensure the module ID 'iA1C3A12631D84E428678FE1CC2E69C6B' exists
4. Verify your user has permissions to access modules
5. Check if the Cognos server is running and responding
6. Try accessing the API endpoint directly in a browser:
   https://your-server/api/v1/session
""")
