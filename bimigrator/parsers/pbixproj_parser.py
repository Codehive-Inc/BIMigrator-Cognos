from datetime import datetime
from typing import Dict, Any

from bimigrator.config.data_classes import PowerBiProject
from bimigrator.parsers.base_parser import BaseParser


class PbixprojParser(BaseParser):
    """Parser for generating .pbixproj.json content from Tableau workbook"""

    def extract_pbixproj_info(self) -> PowerBiProject:
        """Extract information needed for .pbixproj.json
        
        Returns:
            PowerBiProject: Project configuration data
        """
        now = datetime.now()
        return PowerBiProject(
            version="1.0",
            created=now,
            last_modified=now
        )

    def extract_all(self) -> Dict[str, Any]:
        """Extract all project information
        
        Returns:
            Dict[str, Any]: Dictionary containing project information
        """
        data = {
            'PowerBiProject': self.extract_pbixproj_info()
        }

        # Save intermediate file
        self.save_intermediate(data, 'project')

        return data


def parse_workbook(twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Tableau workbook for project information.
    
    Args:
        twb_path: Path to TWB file
        config: Configuration dictionary
        
    Returns:
        Dict[str, Any]: Extracted project information
    """
    parser = PbixprojParser(twb_path, config)
    return parser.extract_all()
