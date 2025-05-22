"""Models for Power BI report settings."""
from dataclasses import dataclass


@dataclass
class QueriesSettings:
    """Query settings for Power BI report."""
    type_detection_enabled: bool
    relationship_import_enabled: bool
    version: str


@dataclass
class PowerBiReportSettings:
    """Power BI report settings."""
    version: int
    report_settings: dict
    queries_settings: QueriesSettings
