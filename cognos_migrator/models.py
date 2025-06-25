"""Data models for Cognos to BI Migrator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

__all__ = [
    # Enums
    'ObjectType', 'DataType',
    # Data models
    'CognosObject', 'DataSource', 'Column', 'Table', 'Relationship', 'Measure',
    'DataModel', 'ReportPage', 'Report', 'MigrationResult', 'MigrationSummary',
    'QueryDefinition', 'CognosReport', 'CognosModule', 'PowerBIProject'
]


class ObjectType(Enum):
    """Cognos object types"""
    REPORT = "report"
    DASHBOARD = "dashboard"
    DATASET = "dataset"
    DATASOURCE = "datasource"
    FOLDER = "folder"
    PACKAGE = "package"
    QUERY = "query"
    MODULE = "module"


class DataType(Enum):
    """Data types mapping"""
    STRING = "string"
    INTEGER = "int64"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    DATE = "dateTime"
    DECIMAL = "decimal"


@dataclass
class CognosObject:
    """Base Cognos object"""
    id: str
    name: str
    type: ObjectType
    parent_id: Optional[str] = None
    description: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    owner: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSource:
    """Cognos data source definition"""
    id: str
    name: str
    connection_string: str
    type: str
    disabled: bool = False
    connections: List[Dict[str, Any]] = field(default_factory=list)
    signons: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class Column:
    """Table column definition"""
    name: str
    data_type: DataType
    source_column: str
    format_string: Optional[str] = None
    summarize_by: str = "none"
    is_key: bool = False
    is_nullable: bool = True
    description: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Table:
    """Table definition"""
    name: str
    columns: List[Column]
    source_query: Optional[str] = None
    partition_mode: str = "import"
    description: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """Table relationship definition"""
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "many_to_one"
    cross_filter_direction: str = "single"
    is_active: bool = True


@dataclass
class Measure:
    """Calculated measure definition"""
    name: str
    expression: str
    format_string: Optional[str] = None
    description: Optional[str] = None
    folder: Optional[str] = None
    is_hidden: bool = False


@dataclass
class DataModel:
    """Power BI data model"""
    name: str
    tables: List[Table]
    relationships: List[Relationship] = field(default_factory=list)
    measures: List[Measure] = field(default_factory=list)
    compatibility_level: int = 1550
    culture: str = "en-US"
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportPage:
    """Report page definition"""
    name: str
    display_name: str
    width: int = 1280
    height: int = 720
    visuals: List[Dict[str, Any]] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    """Power BI report definition"""
    id: str
    name: str
    sections: List[ReportPage] = field(default_factory=list)
    data_model: Optional[DataModel] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationResult:
    """Migration operation result"""
    success: bool
    source_object: CognosObject
    target_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None


@dataclass
class MigrationSummary:
    """Summary of migration operation"""
    total_objects: int
    successful_migrations: int
    failed_migrations: int
    warnings_count: int
    start_time: datetime
    end_time: Optional[datetime] = None
    results: List[MigrationResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_objects == 0:
            return 0.0
        return (self.successful_migrations / self.total_objects) * 100
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate total duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class QueryDefinition:
    """SQL query definition from Cognos"""
    name: str
    sql: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    data_source_id: str = ""
    columns: List[Column] = field(default_factory=list)


@dataclass
class CognosReport:
    """Cognos report structure"""
    id: str
    name: str
    specification: str  # XML specification
    data_sources: List[DataSource] = field(default_factory=list)
    queries: List[QueryDefinition] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognosModule:
    """Cognos module structure"""
    id: str
    name: str
    specification: str
    content: Dict[str, Any] = field(default_factory=dict)
    query_subjects: List[Dict[str, Any]] = field(default_factory=list)
    query_items: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    hierarchies: List[Dict[str, Any]] = field(default_factory=list)
    expressions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PowerBIProject:
    """Complete Power BI project structure"""
    name: str
    version: str = "1.0"
    compatibility_level: int = 1550
    created: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    # Project components
    data_model: Optional[DataModel] = None
    report: Optional[Report] = None
    
    # File paths
    project_file: str = ".pbixproj.json"
    diagram_layout: str = "DiagramLayout.json"
    report_metadata: str = "ReportMetadata.json"
    report_settings: str = "ReportSettings.json"
    version_file: str = "Version.txt"
