"""
Cognos Analytics REST API Client
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin
import logging
from datetime import datetime

from .config import CognosConfig
from .models import CognosObject, DataSource, ObjectType, CognosReport


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
    
    def __init__(self, config: CognosConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            self.config.auth_key: self.config.auth_value,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.logger = logging.getLogger(__name__)
        
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
                
                if response.status_code == 401:
                    self.logger.warning("Authentication failed, attempting to refresh session")
                    self._refresh_session()
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
            response = self._make_request('GET', '/session')
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
        return response.json().get('content', [])
    
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
            
        return CognosObject(
            id=api_obj['id'],
            name=api_obj.get('defaultName', 'Unknown'),
            type=obj_type,
            description=api_obj.get('defaultDescription'),
            modified_date=self._parse_date(api_obj.get('modificationTime')),
            owner=api_obj.get('owner', {}).get('defaultName') if api_obj.get('owner') else None,
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
