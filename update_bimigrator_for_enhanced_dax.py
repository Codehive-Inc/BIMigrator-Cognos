"""
Update BIMigrator to use enhanced DAX API features
This integrates our templates and validation with the existing system
"""

import os
import logging
from typing import Dict, Any
from .llm_template_integration import prepare_llm_request_with_template, validate_llm_output


class EnhancedLLMServiceClient:
    """Enhanced LLM Service Client that uses our template integration"""
    
    def __init__(self, base_url=None, api_key=None):
        if not base_url:
            base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        
    def generate_m_query(self, context: Dict[str, Any]) -> str:
        """
        Generate M-Query using enhanced DAX API with error handling
        """
        table_name = context.get('table_name', 'unknown')
        
        try:
            import requests
            
            # Prepare enhanced request with templates
            enhanced_request = prepare_llm_request_with_template(context)
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self.logger.info(f"Sending enhanced request to DAX API for table {table_name}")
            
            response = requests.post(
                f'{self.base_url}/api/m-query',
                headers=headers,
                json=enhanced_request,
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Validate the response
            if 'm_query' in result:
                m_query = result['m_query']
                
                # Additional validation
                validation_result = validate_llm_output(m_query)
                
                if not validation_result['is_valid']:
                    self.logger.warning(f"Generated M-Query validation failed: {validation_result['issues']}")
                    # Log but continue - the DAX API should have handled this
                
                # Log enhanced features
                if result.get('template_used'):
                    self.logger.info(f"Template-based generation used for {table_name}")
                
                if result.get('validation', {}).get('has_try_otherwise'):
                    self.logger.info(f"Error handling verified for {table_name}")
                
                confidence = result.get('confidence', 1.0)
                self.logger.info(f"Generation confidence: {confidence:.2f} for {table_name}")
                
                return m_query
            else:
                error_msg = f"Enhanced DAX API response missing 'm_query' field for table {table_name}: {result}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with enhanced DAX API for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Enhanced M-Query generation failed for table {table_name}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)


def update_migration_config_for_enhanced_dax():
    """
    Update migration configuration to use enhanced DAX features
    """
    enhanced_config = {
        'llm_service_url': os.environ.get('DAX_API_URL', 'http://localhost:8080'),
        'llm_service_enabled': True,
        'enhanced_dax_features': {
            'error_handling_required': True,
            'template_mode': True,
            'validation_enabled': True,
            'fallback_strategy': 'empty_table_with_schema'
        },
        'request_enhancements': {
            'use_template_mode': True,
            'template_compliance': 'guided',
            'error_handling_mode': 'comprehensive',
            'include_exception_handling': True
        }
    }
    
    return enhanced_config


def patch_existing_llm_service():
    """
    Patch the existing LLM service to use enhanced features
    """
    try:
        # Import existing LLM service
        from cognos_migrator.llm_service import LLMServiceClient
        
        # Store original method
        original_generate = LLMServiceClient.generate_m_query
        
        def enhanced_generate_m_query(self, context: Dict[str, Any]) -> str:
            """Enhanced version of generate_m_query with error handling"""
            
            # Add enhanced context
            enhanced_context = {
                **context,
                'source_type': context.get('source_type', 'sql'),
                'error_handling_requirements': {
                    'wrap_with_try_otherwise': True,
                    'include_fallback_empty_table': True,
                    'preserve_schema_on_error': True,
                    'add_error_info_column': True
                }
            }
            
            # Prepare enhanced request
            enhanced_request = prepare_llm_request_with_template(enhanced_context)
            
            try:
                import requests
                
                headers = {'Content-Type': 'application/json'}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                response = requests.post(
                    f'{self.base_url}/api/m-query',
                    headers=headers,
                    json=enhanced_request,
                    timeout=120
                )
                
                response.raise_for_status()
                result = response.json()
                
                if 'm_query' in result:
                    m_query = result['m_query']
                    
                    # Validate error handling
                    validation = validate_llm_output(m_query)
                    if not validation['is_valid']:
                        self.logger.warning(f"M-Query validation issues: {validation['issues']}")
                    
                    return m_query
                else:
                    raise Exception("Missing m_query in response")
                    
            except Exception as e:
                self.logger.error(f"Enhanced DAX API failed, falling back to original: {e}")
                # Fallback to original method
                return original_generate(self, context)
        
        # Patch the method
        LLMServiceClient.generate_m_query = enhanced_generate_m_query
        
        logging.getLogger(__name__).info("Successfully patched LLMServiceClient with enhanced features")
        return True
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to patch LLMServiceClient: {e}")
        return False


def test_enhanced_integration():
    """Test the enhanced integration"""
    print("🧪 Testing Enhanced BIMigrator Integration")
    
    # Create enhanced client
    client = EnhancedLLMServiceClient()
    
    # Test context
    test_context = {
        'table_name': 'TestTable',
        'source_type': 'sql',
        'columns': [
            {'name': 'ID', 'type': 'int'},
            {'name': 'Name', 'type': 'string'}
        ],
        'connection_info': {
            'server': 'localhost',
            'database': 'test'
        }
    }
    
    try:
        m_query = client.generate_m_query(test_context)
        
        # Validate result
        validation = validate_llm_output(m_query)
        
        print("✅ Enhanced integration test results:")
        print(f"   Has error handling: {'✅' if validation['has_try_otherwise'] else '❌'}")
        print(f"   Has fallback: {'✅' if validation['has_fallback'] else '❌'}")
        print(f"   Valid structure: {'✅' if validation['is_valid'] else '❌'}")
        
        if validation['is_valid']:
            print("🎉 Enhanced integration working correctly!")
            return True
        else:
            print(f"⚠️  Issues found: {validation['issues']}")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced integration test failed: {e}")
        return False


if __name__ == "__main__":
    # Test enhanced integration
    success = test_enhanced_integration()
    
    if success:
        print("\n✅ Enhanced DAX API integration is ready!")
        print("BIMigrator will now generate M-Query with comprehensive error handling.")
    else:
        print("\n❌ Enhanced integration needs attention.")
        print("Check DAX API service and configuration.")