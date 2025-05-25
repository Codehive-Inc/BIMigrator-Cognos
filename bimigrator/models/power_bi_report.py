"""Models for Power BI report."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ResourceItem:
    """Resource item in a resource package."""
    name: str
    path: str
    type: int


@dataclass
class ResourcePackage:
    """Resource package in a Power BI report."""
    disabled: bool = False
    items: List[ResourceItem] = field(default_factory=list)
    name: str = "SharedResources"
    type: int = 2


@dataclass
class ResourcePackageWrapper:
    """Wrapper for resource package."""
    resource_package: ResourcePackage


@dataclass
class PowerBiReport:
    """Power BI report structure."""
    report_id: int = 0
    layout_optimization: int = 0
    resource_packages: List[ResourcePackageWrapper] = field(default_factory=list)
