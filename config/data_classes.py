from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Literal


# --- Project Objects ---

@dataclass
class PowerBiProject:
    """Project configuration."""
    version: str = '1.0'
    created: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)


@dataclass
class PowerBiReportMetadata:
    """Report metadata."""
    version: str
    name: str
    description: str
    owner: str
    created: str
    modified: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PowerBiVisualSettings:
    """Visual settings configuration."""
    default_visual_style: str
    show_data_labels: bool = False


@dataclass
class PowerBiFilterSettings:
    """Filter settings configuration."""
    persistent_filters: bool = True
    filter_pane_enabled: bool = True


@dataclass
class PowerBiInteractionSettings:
    """Interaction settings configuration."""
    drill_enabled: bool = True
    cross_filtering_enabled: bool = True


@dataclass
class PowerBiReportSettings:
    """Report settings."""
    version: str
    visual_settings: PowerBiVisualSettings = field(default_factory=PowerBiVisualSettings)
    filter_settings: PowerBiFilterSettings = field(default_factory=PowerBiFilterSettings)
    interaction_settings: PowerBiInteractionSettings = field(default_factory=PowerBiInteractionSettings)


@dataclass
class PowerBiTablePosition:
    """Table position in diagram."""
    x: float
    y: float


@dataclass
class PowerBiTableLayout:
    """Table layout in diagram."""
    id: str
    position: PowerBiTablePosition


@dataclass
class PowerBiDiagramLayout:
    """Diagram layout."""
    version: str
    layout: Dict[str, List[PowerBiTableLayout]] = field(default_factory=lambda: {"tables": []})


@dataclass
class PowerBiVersion:
    """Version information."""
    version: str


# --- Report Objects ---

@dataclass
class PowerBiTheme:
    """Report theme."""
    name: str
    version: str
    type: int = 2


@dataclass
class PowerBiSlowDataSourceSettings:
    """Settings for slow data sources."""
    is_cross_highlighting_disabled: bool = False
    is_slicer_selections_enabled: bool = True
    is_filter_selections_enabled: bool = True
    is_field_well_enabled: bool = True
    is_apply_all_enabled: bool = True


@dataclass
class PowerBiReportConfig:
    """Report configuration."""
    version: str
    theme: PowerBiTheme
    active_section_index: int = 0
    default_drill_filter: bool = True
    use_new_filter_pane: bool = True
    allow_change_filter_types: bool = True
    slow_data_source_settings: PowerBiSlowDataSourceSettings = field(default_factory=PowerBiSlowDataSourceSettings)


@dataclass
class PowerBiResourceItem:
    """Resource item in a package."""
    name: str
    path: str
    type: str


@dataclass
class PowerBiResourcePackage:
    """Resource package."""
    disabled: bool = False
    items: List[PowerBiResourceItem] = field(default_factory=list)
    name: str = 'SharedResources'
    type: int = 2


@dataclass
class PowerBiReport:
    """Report definition."""
    id: str
    layout_optimization: str
    resource_packages: List[PowerBiResourcePackage] = field(default_factory=list)


@dataclass
class PowerBiFilterTarget:
    """Filter target specification."""
    table: str
    column: str


@dataclass
class PowerBiFilter:
    """Report filter configuration."""
    type: str
    target: PowerBiFilterTarget
    value: Any


@dataclass
class PowerBiVisualObject:
    """Visual object configuration."""
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PowerBiSectionLayout:
    """Section layout configuration."""
    width: int = 1280
    height: int = 720
    display_option: str = "fitToPage"


@dataclass
class PowerBiReportSection:
    """Report section/page."""
    name: str
    display_name: str
    filters: List[PowerBiFilter] = field(default_factory=list)
    objects: Dict[str, List[PowerBiVisualObject]] = field(default_factory=lambda: {"visuals": []})
    layout: PowerBiSectionLayout = field(default_factory=PowerBiSectionLayout)


# --- Model Objects ---

@dataclass
class PowerBiDatabase:
    """Database configuration."""
    name: str
    compatibility_level: int = 1550


@dataclass
class PowerBiExpression:
    """DAX Expression."""
    name: str
    expression: str
    description: Optional[str] = None


@dataclass
class PowerBiExpressions:
    """Container for DAX expressions."""
    expressions: List[PowerBiExpression] = field(default_factory=list)


@dataclass
class DataAccessOptions:
    """Data access options for the model."""
    legacy_redirects: bool = True
    return_error_values_as_null: bool = True


@dataclass
class PowerBiModel:
    """Represents a Power BI model configuration."""
    model_name: str
    culture: str = 'en-US'
    data_access_options: DataAccessOptions = field(default_factory=DataAccessOptions)
    query_order: List[str] = field(default_factory=list)
    time_intelligence_enabled: bool = False
    version: str = '2.120.7013.10 (Main)'
    tables: List[str] = field(default_factory=list)
    desktop_version: Optional[str] = None


# --- Table Objects ---

@dataclass
class PowerBiColumn:
    """Represents a column in a Power BI table."""
    source_name: str
    pbi_datatype: str
    source_column: str
    format_string: Optional[str] = None
    description: Optional[str] = None
    is_hidden: bool = False
    summarize_by: str = 'none'
    lineage_tag: Optional[str] = None

@dataclass
class PowerBiRelationship:
    """Represents a relationship between two tables."""
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    cardinality: Literal['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'] = 'many_to_one'
    cross_filter_behavior: Literal['both', 'one', 'none'] = 'both'
    is_active: bool = True
    join_on_date_behavior: Optional[str] = None
    type: Optional[str] = None


# --- Culture Objects ---

@dataclass
class EntityBinding:
    """Binding information for an entity."""
    conceptual_entity: str
    conceptual_property: Optional[str] = None


@dataclass
class LinguisticTerm:
    """Term in linguistic metadata."""
    term: str
    state: Literal['Generated', 'Suggested'] = 'Generated'
    type: Optional[Literal['Noun', 'Verb', 'Adjective']] = None
    weight: Optional[float] = None


@dataclass
class LinguisticEntity:
    """Entity in linguistic metadata."""
    binding: EntityBinding
    state: Literal['Generated', 'Suggested'] = 'Generated'
    hidden: bool = False
    terms: List[Dict[str, Dict[str, Any]]] = field(default_factory=list)


@dataclass
class LinguisticMetadata:
    """Linguistic metadata for a culture."""
    version: str = '1.2.0'
    language: str = 'en-US'
    dynamic_improvement: Literal['HighConfidence', 'LowConfidence'] = 'HighConfidence'
    entities: Dict[str, LinguisticEntity] = field(default_factory=dict)


@dataclass
class CultureInfo:
    """Complete culture information."""
    culture: str
    linguistic_metadata: LinguisticMetadata = field(default_factory=LinguisticMetadata)

# --- Culture TMDL Objects ---


@dataclass
class LinguisticTerm:
    """Represents a term in the linguistic metadata."""
    term: str
    state: Literal['Generated', 'Suggested'] = 'Generated'
    type: Optional[Literal['Noun', 'Verb', 'Adjective']] = None
    weight: Optional[float] = None


@dataclass
class EntityBinding:
    """Represents the binding information for an entity."""
    conceptual_entity: str
    conceptual_property: Optional[str] = None


@dataclass
class LinguisticEntity:
    """Represents an entity in the linguistic metadata."""
    binding: EntityBinding
    state: Literal['Generated', 'Suggested'] = 'Generated'
    hidden: bool = False
    terms: List[Dict[str, Dict[str, Any]]] = field(default_factory=list)


@dataclass
class LinguisticMetadata:
    """Represents the linguistic metadata in a culture TMDL file."""
    version: str = '1.2.0'
    language: str = 'en-US'
    dynamic_improvement: Literal['HighConfidence', 'LowConfidence'] = 'HighConfidence'
    entities: Dict[str, LinguisticEntity] = field(default_factory=dict)


@dataclass
class CultureInfo:
    """Represents a complete culture TMDL file."""
    culture: str
    linguistic_metadata: LinguisticMetadata = field(default_factory=LinguisticMetadata)


# --- Model Objects (Targeting TMDL Files) ---

@dataclass
class PowerBiColumn:
    """Represents a column within a Power BI table for TMDL."""
    source_name: str
    pbi_datatype: str # e.g., "string", "int64", "double", "dateTime", "boolean"
    source_column: Optional[str] = None
    description: Optional[str] = None
    format_string: Optional[str] = None
    is_hidden: bool = False
    summarize_by: Literal['sum', 'count', 'min', 'max', 'average', 'distinctCount', 'none'] = 'none'
    sortByColumnName: Optional[str] = None
    dataCategory: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict) # <-- Added annotations dict
    # For calculated columns in TMDL format
    is_calculated: bool = False
    is_data_type_inferred: bool = False
    # Example usage for annotations:
    # col.annotations["SummarizationSetBy"] = "Automatic" # or "User" or "None"
    # col.annotations["PBI_FormatHint"] = '{"currencyCulture":"en-US"}' # Store JSON as a string literal
    # col.annotations["SomeOtherAnnotation"] = True


@dataclass
class PowerBiMeasure:
    """Represents a DAX measure within a Power BI table for TMDL."""
    source_name: str
    dax_expression: str
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
    expression: str
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
    description: Optional[str] = None
    is_active: bool = True
    cardinality: Literal['oneToOne', 'oneToMany', 'manyToOne', 'manyToMany'] = 'manyToOne'
    cross_filter_behavior: Literal['oneWay', 'bothDirections', 'automatic'] = 'automatic'
    annotations: Dict[str, Any] = field(default_factory=dict)  # Annotations can apply here too


@dataclass
class PowerBiTable:
    """Represents a table in the Power BI model for TMDL generation."""
    source_name: str
    description: Optional[str] = None
    is_hidden: bool = False
    source_filename: Optional[str] = None  # Path to the source file
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
