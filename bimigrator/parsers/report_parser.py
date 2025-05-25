"""Parser for Power BI report structure."""
from bimigrator.models.power_bi_report import (
    PowerBiReport,
    ResourcePackageWrapper,
    ResourcePackage,
    ResourceItem
)
from bimigrator.parsers.base_parser import BaseParser


class ReportParser(BaseParser):
    """Parser for Power BI report structure."""

    def extract_report(self) -> PowerBiReport:
        """Extract report structure from Tableau workbook.
        
        Returns:
            PowerBiReport object containing report structure
        """
        # Create default resource item for theme
        theme_resource = ResourceItem(
            name="CY24SU10",
            path="BaseThemes/CY24SU10.json",
            type=202
        )
        
        # Create resource package with the theme
        resource_package = ResourcePackage(
            disabled=False,
            items=[theme_resource],
            name="SharedResources",
            type=2
        )
        
        # Create wrapper for the resource package
        package_wrapper = ResourcePackageWrapper(
            resource_package=resource_package
        )
        
        # Create report with default values
        report = PowerBiReport(
            report_id=0,
            layout_optimization=0,
            resource_packages=[package_wrapper]
        )
        
        return report
