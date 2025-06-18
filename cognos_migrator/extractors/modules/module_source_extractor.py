"""
Module source extractor for Cognos to Power BI migration
"""

import logging
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

class ModuleSourceExtractor:
    """Extracts source data information from Cognos module metadata"""
    
    def __init__(self, logger=None):
        """Initialize the extractor
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract source data information from module metadata and save to file
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with source data information
        """
        try:
            # Parse module content
            module_data = json.loads(module_content)
            
            # Extract source data information
            source_data = self._extract_source_data(module_data)
            
            # Save to file
            output_path = Path(output_dir) / "source_data.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(source_data, f, indent=2)
            
            self.logger.info(f"Saved data to {output_path}")
            return source_data
            
        except Exception as e:
            self.logger.error(f"Error extracting source data: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return {"sources": []}
    
    def _extract_source_data(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract source data information from module metadata
        
        Args:
            module_data: Module metadata
            
        Returns:
            Dictionary with source data information formatted for Power BI
        """
        sources = []
        
        # Check for useSpec which contains the source data information
        use_specs = module_data.get('useSpec', [])
        
        for spec in use_specs:
            # Original source info for metadata
            original_info = {
                "identifier": spec.get('identifier', ''),
                "type": spec.get('type', ''),
                "storeID": spec.get('storeID', ''),
                "searchPath": spec.get('searchPath', '')
            }
            
            # Extract file name from searchPath if available
            file_name = ""
            if original_info["searchPath"]:
                file_name = self._extract_file_name(original_info["searchPath"])
                if file_name:
                    original_info["fileName"] = file_name
            
            # Extract folder path if available
            folder_path = ""
            if original_info["searchPath"]:
                folder_path = self._extract_folder_path(original_info["searchPath"])
                if folder_path:
                    original_info["folderPath"] = folder_path
            
            # Format according to the requested structure
            source_info = {
                "class": "",  # No class information available in Cognos metadata
                "server": None,
                "database": None,
                "schema": None,
                "username": None,
                "port": None,
                "authentication": None,
                "table_name": self._determine_table_name(file_name),
                "sql_queries": [],
                "metadata": original_info  # Store original metadata for reference
            }
            
            sources.append(source_info)
        
        return {
            "sources": sources
        }
        
    def _determine_table_name(self, file_name: str) -> str:
        """Determine table name from file name
        
        Args:
            file_name: File name
            
        Returns:
            Table name (for Excel files, this is typically SheetName$)
        """
        if not file_name:
            return ""
            
        # For Excel files, default to Sheet1$ if we can't determine the actual sheet name
        if file_name.lower().endswith(('.xls', '.xlsx', '.xlsm')):
            return "Sheet1$"
            
        # For CSV files, use the file name without extension
        if file_name.lower().endswith('.csv'):
            return file_name.rsplit('.', 1)[0]
            
        return file_name
    
    def _extract_file_name(self, search_path: str) -> str:
        """Extract file name from searchPath
        
        Args:
            search_path: Search path string
            
        Returns:
            File name or empty string if not found
        """
        # Pattern to match uploadedFile[@name='filename.ext']
        file_pattern = r"uploadedFile\[@name='([^']+)'\]"
        match = re.search(file_pattern, search_path)
        
        if match:
            return match.group(1)
        
        return ""
    
    def _extract_folder_path(self, search_path: str) -> str:
        """Extract folder path from searchPath
        
        Args:
            search_path: Search path string
            
        Returns:
            Folder path or empty string if not found
        """
        # Pattern to match folder[@name='foldername']
        folder_pattern = r"folder\[@name='([^']+)'\]"
        folders = re.findall(folder_pattern, search_path)
        
        if folders:
            return "/".join(folders)
        
        return ""
