"""Models for Tableau layout objects."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class TableauLayoutObject:
    """Represents a layout object in a Tableau dashboard."""
    object_id: str
    object_type: str  # worksheet, text, image, webPage, filter, parameter, container
    object_name: Optional[str] = None
    
    # Position and size
    x: int = 0
    y: int = 0
    width: int = 300
    height: int = 200
    
    is_floating: bool = False
    
    # For worksheets
    worksheet_ref: Optional[str] = None
    
    # For containers
    container_type: Optional[str] = None
    children: List['TableauLayoutObject'] = field(default_factory=list)
    
    # Additional Tableau parameters
    tableau_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TableauDashboardLayout:
    """Represents a Tableau dashboard layout."""
    dashboard_name: str
    tableau_width: Optional[int] = None
    tableau_height: Optional[int] = None
    layout_objects: List[TableauLayoutObject] = field(default_factory=list)
