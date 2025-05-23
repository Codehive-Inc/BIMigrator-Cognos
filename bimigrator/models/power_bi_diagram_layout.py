"""Models for Power BI diagram layout models."""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import uuid


@dataclass
class Location:
    """Location in the diagram."""
    x: int = 0
    y: int = 0


@dataclass
class Size:
    """Size in the diagram."""
    width: int = 234
    height: int = 296


@dataclass
class Node:
    """Node in the diagram."""
    location: Location
    nodeIndex: str
    nodeLineageTag: str
    size: Size
    zIndex: int


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
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    name: str = "All tables"
    zoom_value: int = 100
    pin_key_fields_to_top: bool = False
    show_extra_header_info: bool = False
    hide_key_fields_when_collapsed: bool = False
    tables_locked: bool = False


@dataclass
class PowerBiDiagramLayout:
    """Power BI diagram layout."""
    version: str = "1.1.0"
    diagrams: List[DiagramLayout] = field(default_factory=lambda: [DiagramLayout()])
    selected_diagram: str = "All tables"
    default_diagram: str = "All tables"
