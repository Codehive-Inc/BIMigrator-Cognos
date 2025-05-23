"""Parser for report settings."""
from bimigrator.models.power_bi_report_settings import (
    PowerBiReportSettings,
    QueriesSettings
)
from bimigrator.parsers.base_parser import BaseParser


class ReportSettingsParser(BaseParser):
    """Parser for report settings."""

    def extract_report_settings(self) -> PowerBiReportSettings:
        """Extract report settings from Tableau workbook.
        
        Returns:
            PowerBiReportSettings object containing report settings
        """
        # For now, use default values based on examples
        queries_settings = QueriesSettings(
            type_detection_enabled=True,
            relationship_import_enabled=True,
            version="2.142.580.0"
        )

        settings = PowerBiReportSettings(
            version=4,
            report_settings={},
            queries_settings=queries_settings
        )

        return settings
