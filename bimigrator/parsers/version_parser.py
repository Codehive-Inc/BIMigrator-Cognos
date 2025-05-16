from typing import Dict, Any

from bimigrator.config.data_classes import PowerBiVersion
from .base_parser import BaseParser


class VersionParser(BaseParser):
    """Parser for version information."""

    def extract_version(self) -> PowerBiVersion:
        """Extract version information."""
        # You can customize this based on your needs
        return PowerBiVersion(version="1.28")
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all information and save intermediate file."""
        data = {
            'Version': self.extract_version()
        }
        self.save_intermediate(data, 'version')
        return data
