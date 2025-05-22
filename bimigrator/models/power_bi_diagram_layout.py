"""Models for Power BI diagram layout models."""
from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass
class TablePosition:
    """Position of a table in the diagram."""
    id: str
    x: int
    y: int
    width: int
    height: int
    visual_type: str
    config: str  # JSON string
    filters: str  # JSON string
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ScrollPosition:
    """Scroll position in the diagram."""
    x: int = 0
    y: int = 0


@dataclass
class DiagramLayout:
    """Diagram layout."""
    ordinal: int = 0
    scroll_position: ScrollPosition = field(default_factory=ScrollPosition)
    tables: List[TablePosition] = field(default_factory=list)
    name: str = "All tables"
    zoom_value: int = 100
    pin_key_fields_to_top: bool = True
    show_extra_header_info: bool = False
    hide_key_fields_when_collapsed: bool = False
    tables_locked: bool = False


@dataclass
class PowerBiDiagramLayout:
    """Power BI diagram layout."""
    version: str = "1.1.0"
    diagrams: List[DiagramLayout] = field(default_factory=lambda: [DiagramLayout()])
