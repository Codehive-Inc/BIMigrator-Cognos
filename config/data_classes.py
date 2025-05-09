from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any  # Added 'Any' for annotation flexibility


# --- Model Objects (Targeting TMDL Files) ---

@dataclass
class PowerBiColumn:
    """Represents a column within a Power BI table for TMDL."""
    pbi_name: str
    pbi_datatype: str  # e.g., "string", "int64", "double", "dateTime", "boolean"
    source_name: str  # Original source name for reference/lineage
    description: Optional[str] = None
    format_string: Optional[str] = None
    is_hidden: bool = False
    source_column: Optional[str] = None
    summarize_by: Literal['sum', 'count', 'min', 'max', 'average', 'distinctCount', 'none'] = 'none'
    sortByColumnName: Optional[str] = None
    dataCategory: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)  # <-- Added annotations dict
    # Example usage for annotations:
    # col.annotations["SummarizationSetBy"] = "Automatic" # or "User" or "None"
    # col.annotations["PBI_FormatHint"] = '{"currencyCulture":"en-US"}' # Store JSON as a string literal
    # col.annotations["SomeOtherAnnotation"] = True


@dataclass
class PowerBiMeasure:
    """Represents a DAX measure within a Power BI table for TMDL."""
    pbi_name: str
    dax_expression: str
    source_name: str  # Original source name for reference/lineage
    description: Optional[str] = None
    format_string: Optional[str] = None
    is_hidden: bool = False
    display_folder: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)  # <-- Added annotations dict
    # Example usage for annotations:
    # measure.annotations["PBI_FormatHint"] = '{"currencyCulture":"en-US"}'


# --- Other dataclasses remain largely the same as the previous TMDL version ---

@dataclass
class PowerBiHierarchyLevel:
    """Represents a level within a hierarchy."""
    name: str
    column_name: str  # The pbi_name of the column in this table


@dataclass
class PowerBiHierarchy:
    """Represents a hierarchy within a Power BI table for TMDL."""
    name: str
    description: Optional[str] = None
    levels: List[PowerBiHierarchyLevel] = field(default_factory=list)
    is_hidden: bool = False
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations can apply here too


@dataclass
class PowerBiPartition:
    """Represents a partition within a Power BI table for TMDL."""
    name: str
    expression: str  # The M code query (or DAX)
    description: Optional[str] = None
    source_type: Literal['m', 'calculated', 'query'] = 'm'
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations can apply here too


@dataclass
class PowerBiRelationship:
    """Represents a relationship between tables for TMDL."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    description: Optional[str] = None
    cardinality: Literal['oneToOne', 'oneToMany', 'manyToOne', 'manyToMany'] = 'manyToOne'
    cross_filter_behavior: Literal['oneWay', 'bothDirections', 'automatic'] = 'automatic'
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations can apply here too


@dataclass
class PowerBiTable:
    """Represents a table in the Power BI model for TMDL generation."""
    pbi_name: str
    source_name: str  # Original source name for reference/lineage
    description: Optional[str] = None
    is_hidden: bool = False
    partitions: List[PowerBiPartition] = field(default_factory=list)
    columns: List[PowerBiColumn] = field(default_factory=list)
    measures: List[PowerBiMeasure] = field(default_factory=list)
    hierarchies: List[PowerBiHierarchy] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations can apply here too


# --- Report Objects (Targeting report.json - No change needed for model annotations) ---
@dataclass
class PowerBiVisualFieldMapping:
    role: str
    field_name: str


@dataclass
class PowerBiVisual:
    pbi_type: str
    title: str
    source_name: str
    field_mappings: List[PowerBiVisualFieldMapping] = field(default_factory=list)


@dataclass
class PowerBiReportPage:
    name: str
    display_option: Literal["fitToPage", "fitToWidth", "actualSize"] = "fitToPage"
    width: Optional[int] = 1280
    height: Optional[int] = 720
    visuals: List[PowerBiVisual] = field(default_factory=list)


# --- Overall Container ---
@dataclass
class PowerBiTargetStructure:
    """Holds the entire planned Power BI structure for TMDL and Report generation."""
    db_name: str = "SemanticModel"
    compatibility_level: int = 1550
    model_description: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations for the Database/Model itself
    tables: Dict[str, PowerBiTable] = field(default_factory=dict)
    relationships: List[PowerBiRelationship] = field(default_factory=list)
    pages: List[PowerBiReportPage] = field(default_factory=list)
    # roles, cultures, perspectives can be added similarly if needed


# --- Temporary class for processing source info (No change needed) ---
@dataclass
class PowerBiDataSourceInfo:
    pbi_type: str
    connection_details: Dict
    source_name: str
