"""Parser for Power BI report config."""
from bimigrator.models.power_bi_report_config import (
    PowerBiReportConfig,
    ThemeCollection,
    BaseTheme,
    Settings,
    Objects,
    Section,
    OutspacePane,
    SectionProperties,
    OutspacePaneProperties,
    Expr,
    LiteralValue
)
from bimigrator.parsers.base_parser import BaseParser


class ReportConfigParser(BaseParser):
    """Parser for Power BI report config structure."""

    def extract_report_config(self) -> PowerBiReportConfig:
        """Extract report config from Tableau workbook.
        
        Returns:
            PowerBiReportConfig object containing report config
        """
        # Create base theme
        base_theme = BaseTheme(
            name="CY24SU10",
            version="5.61",
            type=2
        )
        
        # Create theme collection with the base theme
        theme_collection = ThemeCollection(
            base_theme=base_theme
        )
        
        # Create settings
        settings = Settings(
            use_new_filter_pane_experience=True,
            allow_change_filter_types=True,
            use_stylable_visual_container_header=True,
            query_limit_option=6,
            export_data_mode=1,
            use_default_aggregate_display_name=True,
            use_enhanced_tooltips=True
        )
        
        # Create section properties with vertical alignment
        section_props = SectionProperties(
            vertical_alignment=Expr(
                literal=LiteralValue(value="'Top'")
            )
        )
        
        # Create outspace pane properties
        outspace_props = OutspacePaneProperties(
            expanded=Expr(
                literal=LiteralValue(value="false")
            )
        )
        
        # Create section and outspace pane
        section = Section(properties=section_props)
        outspace_pane = OutspacePane(properties=outspace_props)
        
        # Create objects with section and outspace pane
        objects = Objects(
            section=[section],
            outspace_pane=[outspace_pane]
        )
        
        # Create report config with all components
        report_config = PowerBiReportConfig(
            version="5.59",
            theme_collection=theme_collection,
            active_section_index=0,
            default_drill_filter_other_visuals=True,
            linguistic_schema_sync_version=2,
            settings=settings,
            objects=objects
        )
        
        return report_config
