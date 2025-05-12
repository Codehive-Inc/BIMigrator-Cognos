from pathlib import Path
import sys
from typing import Dict, Any

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.dataclasses import PowerBiDatabase
from .base_parser import BaseParser

class DatabaseParser(BaseParser):
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
    
    def extract_database_info(self) -> PowerBiDatabase:
        mapping = self.config['PowerBiDatabase']
        name = self._get_mapping_value(mapping.get('name', {}), None, 'Model')
        return PowerBiDatabase(name=name)

    
    def extract_all(self) -> Dict[str, Any]:
        return {
            'PowerBiDatabase': self.extract_database_info()
        }


def parse_workbook(twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    parser = DatabaseParser(twb_path, config)
    return parser.extract_all()


def main():
    """Command line interface for TWB parser."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Extract information from Tableau Workbook files')
    parser.add_argument('twb_file', help='Path to .twb file')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Parse workbook
    data = parse_workbook(args.twb_file)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
