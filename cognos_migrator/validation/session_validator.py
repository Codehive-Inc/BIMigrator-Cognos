"""
Enhanced session validation for Cognos Analytics REST API
Based on Postman collection analysis
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from enum import Enum


class ValidationEndpoint(Enum):
    """Reliable endpoints for session validation"""
    CONTENT = "/content"  # Most reliable, always available
    MODULES = "/modules"  # Good for module operations
    CAPABILITIES = "/capabilities"  # Lightweight, no params
    DATASOURCES = "/datasources"  # For data operations
    SESSION = "/session"  # Official but sometimes problematic


class SessionValidator:
    """Enhanced session validator with multiple endpoint strategies"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Endpoint priority order (most reliable first)
        self.validation_endpoints = [
            ValidationEndpoint.CONTENT,
            ValidationEndpoint.MODULES,
            ValidationEndpoint.CAPABILITIES,
            ValidationEndpoint.SESSION
        ]
    
    def validate_session(self, cognos_url: str, session_key: str, 
                        preferred_endpoint: Optional[ValidationEndpoint] = None) -> Dict[str, Any]:
        """
        Validate a Cognos session using multiple strategies
        
        Args:
            cognos_url: The Cognos base URL
            session_key: The session key to validate
            preferred_endpoint: Optional preferred endpoint to try first
            
        Returns:
            Dict with validation results
        """
        result = {
            'valid': False,
            'endpoint_used': None,
            'status_code': None,
            'error': None,
            'session_info': None,
            'endpoints_tried': []
        }
        
        # Create session
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'IBM-BA-Authorization': session_key
        })
        
        # Determine endpoint order
        endpoints_to_try = self.validation_endpoints.copy()
        if preferred_endpoint and preferred_endpoint in endpoints_to_try:
            endpoints_to_try.remove(preferred_endpoint)
            endpoints_to_try.insert(0, preferred_endpoint)
        
        # Try each endpoint
        for endpoint in endpoints_to_try:
            try:
                url = f"{cognos_url}{endpoint.value}"
                response = session.get(url, timeout=10)
                
                result['endpoints_tried'].append({
                    'endpoint': endpoint.value,
                    'status': response.status_code
                })
                
                if response.status_code == 200:
                    result['valid'] = True
                    result['endpoint_used'] = endpoint.value
                    result['status_code'] = 200
                    
                    # Get session info if available
                    if endpoint == ValidationEndpoint.SESSION:
                        try:
                            data = response.json()
                            result['session_info'] = {
                                'isAnonymous': data.get('isAnonymous', True),
                                'generation': data.get('generation'),
                                'cafContextId': data.get('cafContextId')
                            }
                        except:
                            pass
                    
                    self.logger.info(f"Session validated successfully using {endpoint.value}")
                    return result
                    
                elif response.status_code == 401:
                    # Clear unauthorized - session is invalid
                    result['status_code'] = 401
                    result['error'] = "Unauthorized - session is invalid"
                    self.logger.warning(f"Session invalid at {endpoint.value}: 401 Unauthorized")
                    return result
                    
                elif response.status_code >= 500:
                    # Server error - try next endpoint
                    self.logger.warning(f"Server error at {endpoint.value}: {response.status_code}")
                    continue
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout at {endpoint.value}")
                continue
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error at {endpoint.value}")
                continue
            except Exception as e:
                self.logger.warning(f"Error at {endpoint.value}: {e}")
                continue
        
        # All endpoints failed
        result['error'] = "All validation endpoints failed"
        return result
    
    def get_session_info(self, cognos_url: str, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed session information (if /session endpoint is working)
        
        Args:
            cognos_url: The Cognos base URL
            session_key: The session key
            
        Returns:
            Session info dict or None
        """
        try:
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'IBM-BA-Authorization': session_key
            })
            
            response = session.get(f"{cognos_url}/session", timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get session info: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting session info: {e}")
            return None
    
    def test_module_access(self, cognos_url: str, session_key: str, module_id: str) -> bool:
        """
        Test if session can access a specific module
        
        Args:
            cognos_url: The Cognos base URL
            session_key: The session key
            module_id: The module ID to test
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'IBM-BA-Authorization': session_key
            })
            
            response = session.get(f"{cognos_url}/modules/{module_id}", timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Error testing module access: {e}")
            return False


def quick_validate(cognos_url: str, session_key: str) -> bool:
    """
    Quick session validation using most reliable endpoint
    
    Args:
        cognos_url: The Cognos base URL
        session_key: The session key to validate
        
    Returns:
        True if valid, False otherwise
    """
    validator = SessionValidator()
    result = validator.validate_session(cognos_url, session_key)
    return result['valid']


# Update the existing test_connection_with_session to use new validator
def test_connection_with_session(cognos_url: str, session_key: str) -> bool:
    """
    Test connection to Cognos using URL and session key
    (Updated to use enhanced validation)
    
    Args:
        cognos_url: The Cognos base URL
        session_key: The session key to test
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    return quick_validate(cognos_url, session_key)