"""Models for Power BI report config."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BaseTheme:
    """Base theme in a Power BI report config."""
    name: str = "CY24SU10"
    version: str = "5.61"
    type: int = 2


@dataclass
class ThemeCollection:
    """Theme collection in a Power BI report config."""
    base_theme: BaseTheme = field(default_factory=BaseTheme)


@dataclass
class LiteralValue:
    """Literal value in a Power BI report config."""
    value: str


@dataclass
class Expr:
    """Expression in a Power BI report config."""
    literal: LiteralValue = field(default_factory=LiteralValue)


@dataclass
class SectionProperties:
    """Section properties in a Power BI report config."""
    vertical_alignment: Expr = field(default_factory=lambda: Expr(LiteralValue("'Top'")))


@dataclass
class OutspacePaneProperties:
    """Outspace pane properties in a Power BI report config."""
    expanded: Expr = field(default_factory=lambda: Expr(LiteralValue("false")))


@dataclass
class Section:
    """Section in a Power BI report config."""
    properties: SectionProperties = field(default_factory=SectionProperties)


@dataclass
class OutspacePane:
    """Outspace pane in a Power BI report config."""
    properties: OutspacePaneProperties = field(default_factory=OutspacePaneProperties)


@dataclass
class Objects:
    """Objects in a Power BI report config."""
    section: List[Section] = field(default_factory=lambda: [Section()])
    outspace_pane: List[OutspacePane] = field(default_factory=lambda: [OutspacePane()])


@dataclass
class Settings:
    """Settings in a Power BI report config."""
    use_new_filter_pane_experience: bool = True
    allow_change_filter_types: bool = True
    use_stylable_visual_container_header: bool = True
    query_limit_option: int = 6
    export_data_mode: int = 1
    use_default_aggregate_display_name: bool = True
    use_enhanced_tooltips: bool = True


@dataclass
class PowerBiReportConfig:
    """Power BI report config structure."""
    version: str = "5.59"
    theme_collection: ThemeCollection = field(default_factory=ThemeCollection)
    active_section_index: int = 0
    default_drill_filter_other_visuals: bool = True
    linguistic_schema_sync_version: int = 2
    settings: Settings = field(default_factory=Settings)
    objects: Objects = field(default_factory=Objects)
