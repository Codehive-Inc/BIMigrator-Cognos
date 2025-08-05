"""
Test script to verify enhanced DAX API integration
Run this after implementing the DAX API changes
"""

import requests
import json
import sys
from typing import Dict, Any


def test_dax_api_enhanced():
    """Test the enhanced DAX API with error handling"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Enhanced DAX API Integration")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health check passed: {health.get('status')}")
            
            # Check for enhanced features
            features = health.get('features', {})
            if features.get('error_handling'):
                print("✅ Error handling feature available")
            if features.get('template_mode'):
                print("✅ Template mode feature available")
            if features.get('validation'):
                print("✅ Validation feature available")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Basic M-Query generation
    print("\n2. Testing basic M-Query generation...")
    basic_request = {
        "context": {
            "table_name": "Orders",
            "source_type": "sql",
            "columns": [
                {"name": "OrderID", "type": "int"},
                {"name": "CustomerName", "type": "string"},
                {"name": "OrderDate", "type": "datetime"}
            ],
            "connection_info": {
                "server": "localhost",
                "database": "SalesDB",
                "schema": "dbo"
            }
        },
        "options": {
            "optimize_for_performance": True,
            "include_comments": True
        }
    }
    
    if not test_mquery_request(base_url, basic_request, "Basic generation"):
        return False
    
    # Test 3: Template mode
    print("\n3. Testing template mode...")
    template_request = {
        "context": {
            "table_name": "Customers",
            "source_type": "sql",
            "columns": [
                {"name": "CustomerID", "type": "int"},
                {"name": "CustomerName", "type": "string"}
            ],
            "connection_info": {
                "server": "myserver",
                "database": "CRM"
            }
        },
        "options": {
            "use_template_mode": True,
            "template_compliance": "guided",
            "error_handling_mode": "comprehensive"
        }
    }
    
    if not test_mquery_request(base_url, template_request, "Template mode"):
        return False
    
    # Test 4: Error handling validation
    print("\n4. Testing error handling validation...")
    validation_request = {
        "context": {
            "table_name": "Products",
            "source_type": "csv",
            "columns": [
                {"name": "ProductID", "type": "int"},
                {"name": "ProductName", "type": "string"}
            ],
            "connection_info": {
                "file_path": "/path/to/products.csv"
            }
        },
        "options": {
            "include_exception_handling": True,
            "fallback_strategy": "empty_table_with_schema"
        }
    }
    
    if not test_mquery_request(base_url, validation_request, "Error handling validation"):
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Enhanced DAX API is working correctly.")
    print("\nKey improvements verified:")
    print("✅ Comprehensive error handling in generated M-Query")
    print("✅ Template-based generation with validation")
    print("✅ Fallback mechanisms for failed operations")
    print("✅ Detailed validation and metadata")
    return True


def test_mquery_request(base_url: str, request_data: Dict[str, Any], test_name: str) -> bool:
    """Test a specific M-Query request"""
    try:
        response = requests.post(
            f"{base_url}/api/m-query",
            headers={"Content-Type": "application/json"},
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            m_query = result.get('m_query', '')
            
            print(f"✅ {test_name} successful")
            
            # Validate error handling features
            validation_results = validate_error_handling(m_query, result)
            
            for check, passed in validation_results.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check}")
            
            # Show M-Query snippet
            print(f"   📄 M-Query preview: {m_query[:100]}...")
            
            return all(validation_results.values())
        else:
            print(f"❌ {test_name} failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ {test_name} error: {e}")
        return False


def validate_error_handling(m_query: str, response: Dict[str, Any]) -> Dict[str, bool]:
    """Validate that M-Query includes proper error handling"""
    return {
        "Has try-otherwise blocks": 'try' in m_query and 'otherwise' in m_query,
        "Has error checking": '[HasError]' in m_query or 'HasError' in m_query,
        "Has fallback tables": any(x in m_query for x in ['Table.FromColumns', 'Table.FromRows']),
        "Has error records": 'error [' in m_query or 'Reason =' in m_query,
        "Validation passed": response.get('validation', {}).get('is_valid', False),
        "Template compliance": response.get('template_used', False) or 'template' not in str(response.get('options', {})),
        "Success response": response.get('success', False)
    }


def test_integration_with_bimigrator():
    """Test integration with BIMigrator enhanced requests"""
    print("\n🔗 Testing BIMigrator Integration")
    print("-" * 30)
    
    # Simulate BIMigrator enhanced request
    bimigrator_request = {
        "context": {
            "table_name": "Orders",
            "source_type": "sql",
            "columns": [
                {"name": "OrderID", "type": "int"},
                {"name": "CustomerName", "type": "string"},
                {"name": "OrderDate", "type": "datetime"}
            ],
            "connection_info": {
                "server": "localhost",
                "database": "SalesDB"
            },
            "error_handling_requirements": {
                "wrap_with_try_otherwise": True,
                "include_fallback_empty_table": True,
                "preserve_schema_on_error": True,
                "add_error_info_column": True
            }
        },
        "options": {
            "optimize_for_performance": True,
            "include_comments": True,
            "error_handling_mode": "comprehensive",
            "include_exception_handling": True,
            "fallback_strategy": "empty_table_with_schema"
        },
        "system_prompt_additions": [
            "Generate M-Query code with comprehensive exception handling",
            "Ensure the query won't break Power BI refresh even if data source is unavailable"
        ]
    }
    
    return test_mquery_request(
        "http://localhost:8080", 
        bimigrator_request, 
        "BIMigrator integration"
    )


if __name__ == "__main__":
    print("Enhanced DAX API Integration Test")
    print("Make sure your DAX API service is running at localhost:8080")
    
    # Run tests
    success = test_dax_api_enhanced()
    
    if success:
        # Test BIMigrator integration
        bimigrator_success = test_integration_with_bimigrator()
        
        if bimigrator_success:
            print("\n🎉 Complete integration test passed!")
            print("Your DAX API is ready for enhanced BIMigrator integration.")
            sys.exit(0)
        else:
            print("\n⚠️  BIMigrator integration needs attention.")
            sys.exit(1)
    else:
        print("\n❌ Enhanced DAX API integration failed.")
        print("Please check the integration guide and try again.")
        sys.exit(1)