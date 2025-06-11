#!/usr/bin/env python3
"""
Simple deep search script using existing CognosClient methods to find all content.
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager
from cognos_migrator.client import CognosClient

def search_folder_recursively(client, folder_id, folder_name="Unknown", path="", max_depth=5, current_depth=0):
    """Recursively search a folder for any content"""
    results = []
    
    if current_depth >= max_depth:
        print(f"   Max depth reached for {path}")
        return results
    
    try:
        print(f"{'  ' * current_depth}📁 Exploring: {path}/{folder_name}")
        
        # Get folder contents
        folder_items = client.list_child_objects(folder_id)
        
        if folder_items:
            print(f"{'  ' * current_depth}   Found {len(folder_items)} items")
            
            for item in folder_items:
                item_type = item.get('type', 'unknown')
                item_id = item.get('id', 'no-id')
                item_name = item.get('defaultName', 'Unknown')
                item_path = f"{path}/{folder_name}/{item_name}".replace('//', '/')
                
                # Store this item
                item_info = {
                    'type': item_type,
                    'id': item_id,
                    'name': item_name,
                    'path': item_path,
                    'parent_folder': folder_name,
                    'depth': current_depth + 1
                }
                results.append(item_info)
                
                print(f"{'  ' * current_depth}   - {item_type}: {item_name}")
                
                # If this is a folder, recurse into it
                if item_type == 'folder':
                    try:
                        sub_results = search_folder_recursively(
                            client, item_id, item_name, item_path, 
                            max_depth, current_depth + 1
                        )
                        results.extend(sub_results)
                    except Exception as e:
                        print(f"{'  ' * current_depth}     ❌ Cannot access subfolder: {e}")
        else:
            print(f"{'  ' * current_depth}   Empty folder")
            
    except Exception as e:
        print(f"{'  ' * current_depth}❌ Error exploring {folder_name}: {e}")
    
    return results

def main():
    """Main search function"""
    print("🔍 SIMPLE DEEP SEARCH FOR COGNOS CONTENT")
    print("=" * 60)
    
    try:
        # Initialize client
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        client = CognosClient(cognos_config)
        
        # Test connection
        if not client.test_connection():
            print("❌ Connection failed")
            return
        
        print("✅ Connected to Cognos server")
        print(f"   URL: {cognos_config.base_url}")
        print(f"   User: {cognos_config.username}")
        print()
        
        # Start with root objects
        print("📋 Getting root objects...")
        root_objects = client.list_root_objects()
        
        all_content = []
        content_by_type = defaultdict(list)
        
        print(f"Found {len(root_objects)} root objects")
        print()
        
        # Process each root object
        for root_obj in root_objects:
            obj_type = root_obj.get('type', 'unknown')
            obj_id = root_obj.get('id', 'no-id')
            obj_name = root_obj.get('defaultName', 'Unknown')
            
            # Add root object to results
            root_info = {
                'type': obj_type,
                'id': obj_id,
                'name': obj_name,
                'path': f"/{obj_name}",
                'parent_folder': 'ROOT',
                'depth': 0
            }
            all_content.append(root_info)
            content_by_type[obj_type].append(root_info)
            
            print(f"🔍 Processing root {obj_type}: {obj_name}")
            
            # If it's a folder, explore it recursively
            if obj_type == 'folder':
                folder_results = search_folder_recursively(
                    client, obj_id, obj_name, "", max_depth=4
                )
                all_content.extend(folder_results)
                
                # Group by type
                for item in folder_results:
                    content_by_type[item['type']].append(item)
            
            print()
        
        # Print comprehensive results
        print("=" * 60)
        print("🎯 SEARCH RESULTS")
        print("=" * 60)
        
        print(f"\\nTotal items found: {len(all_content)}")
        print(f"Content types discovered: {len(content_by_type)}")
        
        # Show results by type
        print("\\n📊 CONTENT BY TYPE:")
        print("-" * 40)
        
        # Sort by count
        sorted_types = sorted(content_by_type.items(), 
                            key=lambda x: len(x[1]), reverse=True)
        
        migration_candidates = []
        
        for content_type, items in sorted_types:
            print(f"\\n{content_type.upper()} ({len(items)} items):")
            
            # Check if this type could be migrated
            migratable_types = [
                'report', 'dashboard', 'story', 'explorationVisualization',
                'module', 'dataModule', 'query', 'analysis', 'visualization',
                'uploadedFile'
            ]
            
            is_migratable = content_type in migratable_types
            if is_migratable:
                migration_candidates.extend(items)
            
            # Show examples
            for i, item in enumerate(items[:5]):
                status = "✅ MIGRATABLE" if is_migratable else "ℹ️  Info"
                print(f"   {i+1}. {item['name']}")
                print(f"      ID: {item['id']}")
                print(f"      Path: {item['path']}")
                print(f"      Status: {status}")
                
                if is_migratable:
                    if content_type in ['report', 'dashboard', 'story']:
                        print(f"      Command: python main.py migrate-report {item['id']}")
                    elif content_type in ['folder']:
                        print(f"      Command: python main.py migrate-folder {item['id']}")
            
            if len(items) > 5:
                print(f"   ... and {len(items) - 5} more {content_type} items")
        
        # Summary of migration candidates
        print("\\n" + "=" * 60)
        print("🚀 MIGRATION CANDIDATES SUMMARY")
        print("=" * 60)
        
        if migration_candidates:
            print(f"\\n✅ Found {len(migration_candidates)} items that can be migrated:")
            
            candidate_types = defaultdict(list)
            for item in migration_candidates:
                candidate_types[item['type']].append(item)
            
            for content_type, items in candidate_types.items():
                print(f"\\n{content_type.upper()} ({len(items)} items):")
                for item in items[:3]:
                    print(f"   • {item['name']} (ID: {item['id']})")
                    if content_type == 'folder':
                        print(f"     Command: python main.py migrate-folder {item['id']}")
                    else:
                        print(f"     Command: python main.py migrate-report {item['id']}")
                
                if len(items) > 3:
                    print(f"   ... and {len(items) - 3} more")
        else:
            print("\\n❌ No migration candidates found")
            print("\\nThis could mean:")
            print("   • No reports/dashboards exist in accessible areas")
            print("   • Content is in restricted folders")
            print("   • Different content types are being used")
            print("   • Try exploring with different user permissions")
        
        # Save detailed results
        output_file = "simple_search_results.json"
        try:
            results = {
                'summary': {
                    'total_items': len(all_content),
                    'content_types': len(content_by_type),
                    'migration_candidates': len(migration_candidates)
                },
                'content_by_type': {
                    content_type: [
                        {
                            'id': item['id'],
                            'name': item['name'],
                            'path': item['path'],
                            'parent_folder': item['parent_folder']
                        }
                        for item in items
                    ]
                    for content_type, items in content_by_type.items()
                },
                'migration_candidates': [
                    {
                        'type': item['type'],
                        'id': item['id'],
                        'name': item['name'],
                        'path': item['path']
                    }
                    for item in migration_candidates
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\\n📄 Detailed results saved to: {output_file}")
            
        except Exception as e:
            print(f"\\n❌ Error saving results: {e}")
        
        print("\\n" + "=" * 60)
        print("🎉 SEARCH COMPLETED")
        print("=" * 60)
        
        return len(migration_candidates) > 0
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)