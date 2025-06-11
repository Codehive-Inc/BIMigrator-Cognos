#!/usr/bin/env python3
"""
Deep search script to find ALL content types in Cognos Analytics server.
This script recursively explores all folders and identifies any content that could be migrated.
"""

import os
import sys
import json
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from collections import defaultdict
from cognos_migrator.client import CognosClient

# Load environment variables
load_dotenv()

class CognosDeepSearcher:
    """Deep search for all Cognos content types"""
    
    # Extended list of known Cognos content types
    CONTENT_TYPES = [
        'report', 'dashboard', 'story', 'explorationVisualization', 
        'module', 'dataModule', 'uploadedFile', 'query', 'analysis',
        'metric', 'visualization', 'notebook', 'dataset', 'dataSet2',
        'reportView', 'shortcut', 'URL', 'jobDefinition', 'agentDefinition',
        'page', 'pagelet', 'widget', 'portlet', 'powerPlay',
        'querySubject', 'dimension', 'queryItem', 'filter',
        'calculation', 'prompt', 'template', 'theme', 'skin',
        'package', 'model', 'connection', 'dataSource', 'signOn',
        'distributionList', 'contact', 'printer', 'documentation',
        'folder', 'personalFolder', 'favoriteFolder'
    ]
    
    def __init__(self):
        from cognos_migrator.config import ConfigManager
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        self.client = CognosClient(cognos_config)
        self.found_items = defaultdict(list)
        self.unknown_types = set()
        self.error_count = 0
        self.searched_folders = 0
        self.total_items = 0
        
    def search_all_content(self):
        """Main method to search all content"""
        print("Starting deep search of Cognos content...")
        print("=" * 80)
        
        try:
            # Test connection
            print("Testing connection to Cognos server...")
            if not self.client.test_connection():
                print("❌ Connection test failed")
                return
            print("✓ Connection successful")
            print()
            
            # Try multiple approaches to find content
            self._search_using_content_api()
            self._search_using_folders_api()
            self._search_using_search_api()
            self._search_specific_paths()
            
            # Print comprehensive results
            self._print_results()
            
        except Exception as e:
            print(f"\n❌ Error during search: {e}")
            import traceback
            traceback.print_exc()
    
    def _search_using_content_api(self):
        """Search using the /content endpoint with various filters"""
        print("\n1. Searching using /content API...")
        print("-" * 40)
        
        # Try without any type filter first
        try:
            response = self.client.session.get(
                f"{self.client.base_url}/api/v1/content",
                params={
                    'limit': 1000,
                    'include': 'location,defaultName,type,disabled,hidden'
                }
            )
            if response.status_code == 200:
                items = response.json().get('content', [])
                print(f"Found {len(items)} items without type filter")
                for item in items:
                    self._process_item(item)
        except Exception as e:
            print(f"Error searching without filter: {e}")
        
        # Try each content type individually
        for content_type in self.CONTENT_TYPES:
            try:
                response = self.client.session.get(
                    f"{self.client.base_url}/api/v1/content",
                    params={
                        'type': content_type,
                        'limit': 1000,
                        'include': 'location,defaultName,type'
                    }
                )
                if response.status_code == 200:
                    items = response.json().get('content', [])
                    if items:
                        print(f"Found {len(items)} items of type '{content_type}'")
                        for item in items:
                            self._process_item(item)
            except Exception as e:
                self.error_count += 1
                print(f"Error searching for type '{content_type}': {e}")
    
    def _search_using_folders_api(self):
        """Recursively search through folder structure"""
        print("\n2. Searching using recursive folder traversal...")
        print("-" * 40)
        
        # Start from root folders
        root_folders = ['/', '/content', '/team content', '/personal']
        
        for root in root_folders:
            print(f"\nSearching from root: {root}")
            self._search_folder_recursive(root, level=0)
    
    def _search_folder_recursive(self, folder_path: str, level: int = 0):
        """Recursively search a folder and its subfolders"""
        if level > 10:  # Prevent infinite recursion
            return
            
        indent = "  " * level
        
        try:
            # Try to get folder contents
            response = self.client.session.get(
                f"{self.client.base_url}/api/v1/content",
                params={
                    'location': folder_path,
                    'limit': 1000,
                    'include': 'location,defaultName,type,disabled,hidden'
                }
            )
            
            if response.status_code == 200:
                items = response.json().get('content', [])
                self.searched_folders += 1
                
                if items:
                    print(f"{indent}📁 {folder_path}: {len(items)} items")
                
                for item in items:
                    self._process_item(item)
                    
                    # If it's a folder, search recursively
                    if item.get('type') in ['folder', 'personalFolder']:
                        item_path = item.get('location', '') + '/' + item.get('defaultName', '')
                        self._search_folder_recursive(item_path, level + 1)
                        
            elif response.status_code == 403:
                print(f"{indent}🔒 Access denied: {folder_path}")
            else:
                print(f"{indent}⚠️  Error {response.status_code}: {folder_path}")
                
        except Exception as e:
            self.error_count += 1
            print(f"{indent}❌ Error searching {folder_path}: {e}")
    
    def _search_using_search_api(self):
        """Use the search API to find content"""
        print("\n3. Searching using /search API...")
        print("-" * 40)
        
        # Try various search queries
        search_queries = [
            '*',  # Everything
            'type:*',  # All types
            'report OR dashboard OR story OR visualization',
            'module OR dataModule OR dataset',
        ]
        
        for query in search_queries:
            try:
                response = self.client.session.get(
                    f"{self.client.base_url}/api/v1/search",
                    params={
                        'query': query,
                        'limit': 1000,
                        'include': 'location,defaultName,type'
                    }
                )
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    print(f"Query '{query}': {len(results)} results")
                    
                    for result in results:
                        self._process_item(result)
                        
            except Exception as e:
                self.error_count += 1
                print(f"Error with search query '{query}': {e}")
    
    def _search_specific_paths(self):
        """Search specific known paths where content might be stored"""
        print("\n4. Searching specific known paths...")
        print("-" * 40)
        
        known_paths = [
            '/content/folder[@name="Samples"]',
            '/content/folder[@name="Public Folders"]',
            '/content/folder[@name="My Folders"]',
            '/content/folder[@name="Team Content"]',
            '/content/package',
            '/content/reportView',
            '/content/query',
            '/content/analysis',
        ]
        
        for path in known_paths:
            try:
                response = self.client.session.get(
                    f"{self.client.base_url}/api/v1/content",
                    params={
                        'path': path,
                        'limit': 1000
                    }
                )
                
                if response.status_code == 200:
                    items = response.json().get('content', [])
                    print(f"Path '{path}': {len(items)} items")
                    
                    for item in items:
                        self._process_item(item)
                        
            except Exception as e:
                print(f"Error searching path '{path}': {e}")
    
    def _process_item(self, item: Dict):
        """Process a found item"""
        item_type = item.get('type', 'unknown')
        item_id = item.get('id', 'no-id')
        item_name = item.get('defaultName', 'unnamed')
        item_location = item.get('location', '')
        
        # Track the item
        self.total_items += 1
        
        # Store by type
        if item_type:
            self.found_items[item_type].append({
                'id': item_id,
                'name': item_name,
                'location': item_location,
                'full_path': f"{item_location}/{item_name}".replace('//', '/'),
                'disabled': item.get('disabled', False),
                'hidden': item.get('hidden', False)
            })
            
            # Track unknown types
            if item_type not in self.CONTENT_TYPES:
                self.unknown_types.add(item_type)
    
    def _print_results(self):
        """Print comprehensive results"""
        print("\n" + "=" * 80)
        print("SEARCH RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal items found: {self.total_items}")
        print(f"Folders searched: {self.searched_folders}")
        print(f"Errors encountered: {self.error_count}")
        
        # Print content by type
        print("\n" + "-" * 80)
        print("CONTENT BY TYPE:")
        print("-" * 80)
        
        # Sort by count
        sorted_types = sorted(self.found_items.items(), 
                            key=lambda x: len(x[1]), reverse=True)
        
        for content_type, items in sorted_types:
            print(f"\n{content_type.upper()} ({len(items)} items):")
            
            # Show first few items as examples
            for i, item in enumerate(items[:5]):
                status = []
                if item.get('disabled'):
                    status.append('disabled')
                if item.get('hidden'):
                    status.append('hidden')
                status_str = f" [{', '.join(status)}]" if status else ""
                
                print(f"  {i+1}. {item['name']}{status_str}")
                print(f"     ID: {item['id']}")
                print(f"     Path: {item['full_path']}")
            
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
        
        # Print unknown types
        if self.unknown_types:
            print("\n" + "-" * 80)
            print("DISCOVERED UNKNOWN CONTENT TYPES:")
            print("-" * 80)
            for unknown_type in sorted(self.unknown_types):
                count = len(self.found_items.get(unknown_type, []))
                print(f"  - {unknown_type} ({count} items)")
        
        # Print migration candidates
        print("\n" + "-" * 80)
        print("MIGRATION CANDIDATES:")
        print("-" * 80)
        
        migration_types = ['report', 'dashboard', 'story', 'explorationVisualization', 
                          'module', 'dataModule', 'query', 'analysis', 'visualization']
        
        total_candidates = 0
        for mtype in migration_types:
            if mtype in self.found_items:
                count = len(self.found_items[mtype])
                total_candidates += count
                print(f"  - {mtype}: {count} items")
        
        print(f"\nTotal migration candidates: {total_candidates}")
        
        # Save detailed results to file
        self._save_results_to_file()
    
    def _save_results_to_file(self):
        """Save detailed results to a JSON file"""
        output_file = "cognos_content_inventory.json"
        
        try:
            results = {
                'summary': {
                    'total_items': self.total_items,
                    'folders_searched': self.searched_folders,
                    'errors': self.error_count,
                    'content_types_found': len(self.found_items),
                    'unknown_types': list(self.unknown_types)
                },
                'content_by_type': self.found_items,
                'migration_candidates': {
                    content_type: items 
                    for content_type, items in self.found_items.items()
                    if content_type in ['report', 'dashboard', 'story', 
                                      'explorationVisualization', 'module', 
                                      'dataModule', 'query', 'analysis', 'visualization']
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n✓ Detailed results saved to: {output_file}")
            
        except Exception as e:
            print(f"\n❌ Error saving results: {e}")


def main():
    """Main entry point"""
    print("Cognos Deep Content Search")
    print("=" * 80)
    
    try:
        # Run the search
        searcher = CognosDeepSearcher()
        searcher.search_all_content()
    except Exception as e:
        print(f"❌ Error running deep search: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()