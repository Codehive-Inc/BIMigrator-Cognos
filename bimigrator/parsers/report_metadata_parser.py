"""Parser for extracting report metadata from Tableau workbooks."""
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.data_classes import PowerBiReportMetadata
from .base_parser import BaseParser


class ReportMetadataParser(BaseParser):
    """Parser for extracting report metadata from Tableau workbooks."""

    def __init__(self, filename: str, config: Dict[str, Any], output_dir: Optional[Path] = None):
        """Initialize parser with configuration.
        
        Args:
            filename: Path to input file
            config: Configuration dictionary
            output_dir: Optional output directory override
        """
        super().__init__(filename, config, output_dir)

    def extract_metadata(self) -> PowerBiReportMetadata:
        """Extract report metadata from workbook.
        
        Returns:
            PowerBiReportMetadata object containing extracted metadata
        """
        # Extract workbook name
        name = Path(self.filename).stem

        # Get current timestamp for created/modified
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Extract owner from workbook if available, otherwise use system user
        owner = self.tree.find('.//repository-location[@owner]')
        owner = owner.get('owner') if owner is not None else 'Unknown'

        # Extract description if available
        description = ''
        caption = self.tree.find('.//workbook[@caption]')
        if caption is not None:
            description = caption.get('caption', '')

        # Extract any custom metadata
        custom_metadata = {}
        
        # Extract tags if available
        tags = []
        tag_elements = self.tree.findall('.//tag')
        if tag_elements:
            tags = [tag.get('name') for tag in tag_elements if tag.get('name')]

        # Create metadata object
        metadata = PowerBiReportMetadata(
            version='1.0',
            name=name,
            description=description,
            owner=owner,
            created=now,
            modified=now,
            tags=tags,
            custom_metadata=custom_metadata
        )

        return metadata
