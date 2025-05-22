"""Models for Power BI diagram layout."""
from dataclasses import dataclass
from typing import List


@dataclass
class TablePosition:
    """Position of a table in the diagram."""
    id: str
    x: float
    y: float


@dataclass
class DiagramLayout:
    """Layout information for the diagram."""
    tables: List[TablePosition]


@dataclass
class PowerBiDiagramLayout:
    """Power BI diagram layout."""
    version: int
    layout: DiagramLayout
