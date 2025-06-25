"""Cognos Analytics REST API Client."""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests

from .config import CognosConfig
from .models import CognosObject, DataSource, ObjectType, CognosReport

__all__ = ['CognosAPIError', 'CognosClient']


class CognosAPIError(Exception):
    """Custom exception for Cognos API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class CognosClient:
    """
    Cognos Analytics REST API Client
    Provides methods to interact with Cognos Analytics REST API
    """
    
    def __init__(self, config: CognosConfig, base_url: str = None, session_key: str = None):
        if base_url and session_key:
            # Direct initialization with session
            self.config = config
            self.base_url = base_url
            self.session = requests.Session()
            self.session.headers[self.config.auth_key] = session_key
            self.logger = logging.getLogger(__name__)
            self.auth_token = session_key
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            self._verify_session()
            self.authenticated = True
        else: 
            self.config = config
            self.session = requests.Session()
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            self.logger = logging.getLogger(__name__)
            self.auth_token = None
            self._authenticate()
    
    @staticmethod
    def test_connection_with_session(cognos_url: str, session_key: str) -> bool:
        """Test connection to Cognos using only URL and session key
        
        Args:
            cognos_url: The Cognos base URL
            session_key: The session key to test
            
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Create a simple session with the provided credentials
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'IBM-BA-Authorization': session_key  # Using hardcoded auth key
            })
            
            # Try to verify the session
            response = session.get(
                f"{cognos_url}/session",
                timeout=30
            )
            
            if response.status_code == 200:
                # Check if session is valid and not anonymous
                try:
                    session_data = response.json()
                    if session_data and not session_data.get('isAnonymous', True):
                        return True
                except:
                    pass
                    
            return False
            
        except Exception as e:
            logging.error(f"Connection test failed: {e}")
            return False
    
    def _authenticate(self):
        """Authenticate with Cognos using session-based authentication"""
        try:
            # Use session-based authentication with base token + credentials
            if hasattr(self.config, 'base_auth_token') and self.config.base_auth_token:
                session_key = self._get_session_key()
                if session_key:
                    self.session.headers[self.config.auth_key] = session_key
                    self.auth_token = session_key
                    self.logger.info("Successfully authenticated with session key")
                    return
            
            # Fallback to direct token auth if configured
            if self.config.auth_value:
                self.session.headers[self.config.auth_key] = self.config.auth_value
                self.logger.info("Using direct token-based authentication")
                return
            
            # Fallback to basic auth if username/password provided
            if self.config.username and self.config.password:
                try:
                    import base64
                    credentials = f"{self.config.username}:{self.config.password}"
                    encoded_credentials = base64.b64encode(credentials.encode()).decode()
                    self.session.headers['Authorization'] = f'Basic {encoded_credentials}'
                    self.logger.info("Using basic authentication")
                except Exception as e:
                    self.logger.error(f"Basic authentication setup failed: {e}")
            else:
                self.logger.warning("No authentication credentials provided")
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise CognosAPIError(f"Authentication failed: {e}")
    
    def _get_session_key(self) -> Optional[str]:
        """Get session key using base auth token + credentials via PUT /session"""
        try:
            # Prepare session request
            session_url = self.config.base_url + '/session'
            
            # Try different payload formats based on Cognos API documentation
            
            # Format 1: Standard Cognos format
            credentials_payload = {
                "parameters": [
                    {
                        "name": "CAMNamespace",
                        "value": self.config.namespace or "LDAP"
                    },
                    {
                        "name": "CAMUsername", 
                        "value": self.config.username
                    },
                    {
                        "name": "CAMPassword",
                        "value": self.config.password
                    },
                    {
                        "name": "h_CAM_action",
                        "value": "logonAs"
                    }
                ]
            }
            
            # Set base auth token header
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                self.config.auth_key: self.config.base_auth_token
            }
            
            self.logger.info("Requesting session key with base auth token...")
            
            # Make PUT request to /session
            response = requests.put(
                session_url,
                json=credentials_payload,
                headers=headers,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200 or response.status_code == 201:
                # Extract session key from response headers first
                session_key = response.headers.get(self.config.auth_key)
                if session_key:
                    self.logger.info("Successfully obtained session key from headers")
                    return session_key
                
                # Try to get from response body
                try:
                    response_data = response.json()
                    # Check various possible fields in response
                    session_key = (response_data.get('sessionKey') or 
                                  response_data.get('session_key') or
                                  response_data.get('cafContextId'))
                    if session_key:
                        self.logger.info("Session key found in response body") 
                        return session_key
                        
                    # If response contains session info, we might already be authenticated
                    if 'generation' in response_data and not response_data.get('isAnonymous', True):
                        self.logger.info("Session established successfully, continuing with base token")
                        return self.config.base_auth_token
                        
                except Exception as e:
                    self.logger.warning(f"Could not parse response body: {e}")
                    
                self.logger.warning("Session key not found in response headers or body")
            else:
                self.logger.error(f"Session request failed: {response.status_code} - {response.text}")
                
                # Try alternative format if first attempt fails
                if response.status_code == 401:
                    return self._try_alternative_session_format()
                
        except Exception as e:
            self.logger.error(f"Failed to get session key: {e}")
            
        return None
    
    def _try_alternative_session_format(self) -> Optional[str]:
        """Try alternative session request format"""
        try:
            session_url = self.config.base_url + '/session'
            
            # Alternative format: Form data instead of JSON
            form_data = {
                'CAMNamespace': self.config.namespace or 'LDAP',
                'CAMUsername': self.config.username,
                'CAMPassword': self.config.password,
                'h_CAM_action': 'logonAs'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                self.config.auth_key: self.config.base_auth_token
            }
            
            self.logger.info("Trying alternative session format (form data)...")
            
            response = requests.put(
                session_url,
                data=form_data,
                headers=headers,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200 or response.status_code == 201:
                session_key = response.headers.get(self.config.auth_key)
                if session_key:
                    self.logger.info("Successfully obtained session key with alternative format")
                    return session_key
            else:
                self.logger.warning(f"Alternative session format also failed: {response.status_code}")
                
        except Exception as e:
            self.logger.warning(f"Alternative session format failed: {e}")
            
        return None
    
    def _verify_session(self) -> bool:
        """Verify if the current session is valid"""
        try:
            response = self._make_request('GET', '/session')
            if response.status_code == 200:
                self.logger.info("Session is valid")
                return True
            else:
                self.logger.warning(f"Session verification failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Session verification error: {e}")
            return False
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling and retries"""
        url = self.config.base_url + endpoint
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.request_timeout,
                    **kwargs
                )
                
                if response.status_code == 401 and attempt == 0:
                    self.logger.warning("Authentication failed, attempting to re-authenticate")
                    self._authenticate()
                    continue
                    
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    raise CognosAPIError(f"Request failed after {self.config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise CognosAPIError("Maximum retry attempts exceeded")
    
    def _refresh_session(self):
        """Refresh the authentication session"""
        try:
            response = self._make_request('GET', '/session')
            if response.status_code == 200:
                self.logger.info("Session refreshed successfully")
        except Exception as e:
            self.logger.error(f"Failed to refresh session: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to Cognos Analytics"""
        try:
            response = self._make_request('GET', '/content')
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        response = self._make_request('GET', '/session')
        return response.json()
    
    def list_root_objects(self) -> List[Dict[str, Any]]:
        """List root content objects"""
        response = self._make_request('GET', '/content')
        return response.json().get('content', [])
    
    def get_object(self, object_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """Get object by ID"""
        params = {}
        if fields:
            params['fields'] = fields
            
        response = self._make_request('GET', f'/content/{object_id}', params=params)
        return response.json()
    
    def list_child_objects(self, parent_id: str, fields: Optional[str] = None, nav_filter: bool = True) -> List[Dict[str, Any]]:
        """List child objects of a parent"""
        params = {}
        if fields:
            params['fields'] = fields
        if nav_filter:
            params['nav_filter'] = 'true'
            
        response = self._make_request('GET', f'/content/{parent_id}/items', params=params)
        response_data = response.json()
        
        # Handle different response formats
        if isinstance(response_data, list):
            return response_data
        elif isinstance(response_data, dict):
            return response_data.get('content', [])
        else:
            return []
    
    def search_objects(self, search_path: str = "", object_types: Optional[List[str]] = None) -> List[CognosObject]:
        """Search for objects in Cognos"""
        objects = []
        
        # Start with root objects if no search path provided
        if not search_path:
            root_objects = self.list_root_objects()
            for obj in root_objects:
                cognos_obj = self._convert_to_cognos_object(obj)
                objects.append(cognos_obj)
                
                # Recursively get child objects
                if obj.get('type') in ['folder', 'package']:
                    child_objects = self._get_all_child_objects(obj['id'])
                    objects.extend(child_objects)
        
        # Filter by object types if specified
        if object_types:
            objects = [obj for obj in objects if obj.type.value in object_types]
            
        return objects
    
    def _get_all_child_objects(self, parent_id: str) -> List[CognosObject]:
        """Recursively get all child objects"""
        objects = []
        try:
            child_items = self.list_child_objects(parent_id)
            for item in child_items:
                cognos_obj = self._convert_to_cognos_object(item)
                objects.append(cognos_obj)
                
                # Recursively get children if it's a container
                if item.get('type') in ['folder', 'package']:
                    child_objects = self._get_all_child_objects(item['id'])
                    objects.extend(child_objects)
                    
        except Exception as e:
            self.logger.warning(f"Failed to get child objects for {parent_id}: {e}")
            
        return objects
    
    def _convert_to_cognos_object(self, api_obj: Dict[str, Any]) -> CognosObject:
        """Convert API response to CognosObject"""
        obj_type = ObjectType.REPORT  # Default
        try:
            obj_type = ObjectType(api_obj.get('type', 'report'))
        except ValueError:
            # Handle unknown types
            pass
            
        # Handle owner field which can be a list or dict
        owner_name = None
        owner = api_obj.get('owner')
        if owner:
            if isinstance(owner, list) and len(owner) > 0:
                owner_name = owner[0].get('defaultName')
            elif isinstance(owner, dict):
                owner_name = owner.get('defaultName')
        
        return CognosObject(
            id=api_obj['id'],
            name=api_obj.get('defaultName', 'Unknown'),
            type=obj_type,
            description=api_obj.get('defaultDescription'),
            modified_date=self._parse_date(api_obj.get('modificationTime')),
            owner=owner_name,
            permissions=api_obj.get('permissions', []),
            metadata=api_obj
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            # Handle different date formats from Cognos
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def get_report_specification(self, report_id: str) -> str:
        """Get report specification (XML)"""
        # This would typically require additional API calls to get the full report spec
        # For now, we'll get the basic object info
        response = self._make_request('GET', f'/content/{report_id}', params={'fields': 'specification'})
        return response.json().get('specification', '')
    
    def get_report_data_sources(self, report_id: str) -> List[DataSource]:
        """Get data sources used by a report"""
        data_sources = []
        try:
            # Get report object details
            report_obj = self.get_object(report_id)
            
            # Extract data source information from report metadata
            # This is a simplified implementation - actual implementation would
            # need to parse the report specification XML
            
            # For now, return empty list - would need to implement XML parsing
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to get data sources for report {report_id}: {e}")
            
        return data_sources
    
    def list_data_sources(self) -> List[DataSource]:
        """List all data sources"""
        response = self._make_request('GET', '/datasources')
        data_sources = []
        
        for ds_data in response.json().get('dataSources', []):
            data_source = DataSource(
                id=ds_data['id'],
                name=ds_data.get('defaultName', 'Unknown'),
                connection_string='',  # Would need additional API call
                type=ds_data.get('type', 'unknown'),
                disabled=ds_data.get('disabled', False),
                capabilities=ds_data.get('capabilities', [])
            )
            data_sources.append(data_source)
            
        return data_sources
    
    def get_data_source(self, datasource_id: str) -> Optional[DataSource]:
        """Get detailed data source information"""
        try:
            response = self._make_request('GET', f'/datasources/{datasource_id}', params={'fields': 'connections,signons'})
            ds_data = response.json()
            
            return DataSource(
                id=ds_data['id'],
                name=ds_data.get('defaultName', 'Unknown'),
                connection_string='',  # Would extract from connections
                type=ds_data.get('type', 'unknown'),
                disabled=ds_data.get('disabled', False),
                connections=ds_data.get('connections', []),
                signons=ds_data.get('signons', []),
                capabilities=ds_data.get('capabilities', [])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get data source {datasource_id}: {e}")
            return None
    
    def get_report(self, report_id: str) -> Optional[CognosReport]:
        """Get complete Cognos report structure (alias for compatibility)"""
        return self.get_cognos_report(report_id)
    
    def get_cognos_report(self, report_id: str) -> Optional[CognosReport]:
        """Get complete Cognos report structure"""
        try:
            # Get basic report info
            report_obj = self.get_object(report_id)
            
            # Get report specification
            specification = self.get_report_specification(report_id)
            
            # Get associated data sources
            data_sources = self.get_report_data_sources(report_id)
            
            return CognosReport(
                id=report_id,
                name=report_obj.get('defaultName', 'Unknown'),
                specification=specification,
                data_sources=data_sources,
                metadata=report_obj
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get Cognos report {report_id}: {e}")
            return None
    
    def list_reports_in_folder(self, folder_id: str, recursive: bool = True) -> List[CognosObject]:
        """List all reports in a folder"""
        reports = []
        try:
            # Get items in folder
            items = self.list_child_objects(folder_id)
            
            # Ensure items is a list
            if not isinstance(items, list):
                self.logger.warning(f"Expected list from list_child_objects, got {type(items)}")
                return reports
            
            for item in items:
                # Ensure item is a dictionary
                if not isinstance(item, dict):
                    self.logger.warning(f"Expected dict item, got {type(item)}: {item}")
                    continue
                    
                item_type = item.get('type', '')
                if item_type == 'report':
                    cognos_obj = self._convert_to_cognos_object(item)
                    reports.append(cognos_obj)
                elif recursive and item_type == 'folder':
                    # Recursively get reports from subfolders
                    item_id = item.get('id', '')
                    if item_id:
                        sub_reports = self.list_reports_in_folder(item_id, recursive)
                        reports.extend(sub_reports)
            
        except Exception as e:
            self.logger.warning(f"Failed to list reports in folder {folder_id}: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        return reports
    
    def export_report(self, report_id: str, format_type: str = 'XML') -> Optional[bytes]:
        """Export report in specified format"""
        try:
            # This would use the Cognos reporting service API
            # Implementation depends on specific Cognos version and configuration
            self.logger.warning("Report export not yet implemented")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to export report {report_id}: {e}")
            return None
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """List available modules"""
        response = self._make_request('GET', '/modules')
        return response.json().get('modules', [])
    
    def get_module(self, module_id: str) -> Dict[str, Any]:
        """Get module by ID"""
        response = self._make_request('GET', f'/modules/{module_id}')
        return response.json()
    
    def get_module_metadata(self, module_id: str) -> Dict[str, Any]:
        """Get module metadata by ID"""
        response = self._make_request('GET', f'/modules/{module_id}/metadata')
        return response.json()
    
    def close(self):
        """Close the client session"""
        if self.session:
            self.session.close()
