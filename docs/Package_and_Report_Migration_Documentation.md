# Detailed Package and Report Migration Process Documentation

## Test Overview: `test_package_and_report_migration.py`

### Test Setup and Inputs
```python
package_file = "examples/packages/ELECTRIC_GENERATION_MAT.xml"
report_files = [
    "examples/Report XMLs DE/MaterialAdjustmentDetail_UC017.xml",
    "examples/Report XMLs DE/MaterialInquiryDetail_UC012.xml", 
    "examples/Report XMLs DE/MaterialReceiptDetail_UC016.xml",
    "examples/Report XMLs DE/PartNumbers_UC013.xml"
]
output_dir = "test_output/de_package_and_report_migration"
```

## Detailed Migration Process: `_migrate_shared_model()`

### STEP 1: Individual Report Migration
**Location:** Lines 459-490 in `_migrate_shared_model()`

1. **Directory Setup**
   - Creates `intermediate_reports/` directory
   - Removes any existing intermediate reports
   - **Output:** `test_output/de_package_and_report_migration/intermediate_reports/`

2. **Individual Report Processing Loop**
   - For each report file (4 reports):
     - Sanitizes report name: `Path(report_item).stem`
     - Creates report-specific directory: `intermediate_reports/MaterialAdjustmentDetail_UC017/`
     - Calls `migrate_single_report()` for each report
     - **Data Source:** Individual XML report files
     - **Output:** 4 subdirectories with complete report migrations

3. **Success Tracking**
   - Maintains `successful_migrations_paths[]` list
   - Only successful migrations proceed to consolidation

### STEP 2: Table Schema Consolidation
**Location:** Lines 491-551 in `_migrate_shared_model()`

1. **Migrator Initialization**
   - Creates `CognosModuleMigratorExplicit` instance
   - Configures with `MigrationConfig` and `CognosConfig`
   - Sets up template directory path

2. **Report Analysis Loop**
   - For each successful report migration:
     - Reads `intermediate_model_path / "extracted"`
     - Calls `migrator._create_data_model_from_report()`
     - Extracts table names: `required_tables.add(table.name)`
     - **Key Process:** Column merging for same tables across reports

3. **Table Consolidation Logic**
   ```python
   if table.name not in consolidated_tables:
       consolidated_tables[table.name] = table
   else:
       # Merge columns from same table used in different reports
       existing_column_names = {c.name.lower() for c in existing_table.columns}
       for new_column in table.columns:
           if new_column.name.lower() not in existing_column_names:
               existing_table.columns.append(new_column)
   ```

4. **Configuration Integration**
   - Adds "always_include" tables from config
   - Handles "direct" mode safety checks
   - **Output:** `consolidated_tables` dictionary and `required_tables` set

### STEP 2.5: Calculation Merging
**Location:** Lines 553-566 in `_migrate_shared_model()`

1. **Intermediate Report Discovery**
   - Scans `intermediate_reports/` directory
   - Identifies all subdirectories as report paths
   - **Function Call:** `_merge_calculations_from_intermediate_reports()`

2. **Calculation Consolidation Process**
   - Loads existing `calculations.json` if present
   - Merges calculations from all intermediate reports
   - **Output:** `extracted/calculations.json` with consolidated calculations

### STEP 3: Package Extraction with Table Filtering
**Location:** Lines 568-577 in `_migrate_shared_model()`

1. **Extractor Initialization**
   ```python
   package_extractor = ConsolidatedPackageExtractor(
       config=config,
       logger=logging.getLogger(__name__)
   )
   ```

2. **Filtered Package Extraction**
   - **Key Parameter:** `required_tables=required_tables`
   - Only extracts tables actually used by reports
   - **Function Call:** `package_extractor.extract_package()`
   - **Output:** `extracted/package_info.json` (filtered)

### STEP 3.5: SQL Relationship Extraction
**Location:** Lines 579-592 in `_migrate_shared_model()`

1. **SQL Relationship Processing**
   ```python
   sql_relationship_extractor = SQLRelationshipExtractor(
       logger=logging.getLogger(__name__), 
       model_tables=model_table_names
   )
   sql_relationship_extractor.extract_and_save(package_file, extracted_dir)
   ```

2. **Output Files Generated**
   - `extracted/sql_relationships.json` - Complete relationship definitions
   - `extracted/sql_relationship_joins.csv` - Tabular join analysis
   - `extracted/sql_filtered_relationships.json` - Filtered by table usage

### STEP 4: Data Model Conversion
**Location:** Lines 583-602 in `_migrate_shared_model()`

1. **Model Conversion**
   - **Function Call:** `package_extractor.convert_to_data_model(package_info)`
   - Converts filtered package info to Power BI data model
   - **Output:** `data_model` object with tables and relationships

2. **Filtering Verification**
   - Logs query subject names after filtering
   - Logs data model table names after conversion
   - Ensures only required tables are included

### STEP 5: Report-Package Data Merging
**Location:** Lines 604-617 in `_migrate_shared_model()`

1. **Column Integration Process**
   ```python
   for table_name, consolidated_table in consolidated_tables.items():
       target_table = next((t for t in data_model.tables 
                           if t.name.lower() == table_name.lower()), None)
       if target_table:
           # Add missing columns from reports to package tables
   ```

2. **M-Query Generation**
   ```python
   consolidated_converter = ConsolidatedMQueryConverter(output_path=output_path)
   for table in data_model.tables:
       table.m_query = consolidated_converter.convert_to_m_query(table)
   ```

### STEP 6: Power BI Project Generation
**Location:** Lines 626-660 in `_migrate_shared_model()`

1. **Generator Setup**
   ```python
   migration_config = MigrationConfig(
       output_directory=Path(output_path), 
       template_directory=str(Path(__file__).parent.parent / "templates")
   )
   generator = PowerBIProjectGenerator(migration_config)
   ```

2. **Package-Specific Components**
   - `PackageMQueryConverter` for M-query generation
   - `PackageModelFileGenerator` with staging table support
   - `TemplateEngine` for file generation

3. **Final Project Creation**
   ```python
   final_pbi_project = PowerBIProject(
       name=data_model.name,
       data_model=data_model,
       report=Report(id=f"report_{data_model.name}", name=data_model.name)
   )
   ```
   - **Output Directory:** `pbit/`
   - **Key Files:** `.pbixproj.json`, `Model/database.tmdl`

### STEP 6.5: Final Integration Steps
**Location:** Lines 662-680 in `_migrate_shared_model()`

1. **Calculation Integration**
   - **Function:** `_merge_calculations_into_table_json()`
   - Merges calculations into individual table JSON files

2. **Report Consolidation**
   - **Function:** `_consolidate_intermediate_reports_into_final()`
   - Consolidates report pages and slicers into unified report

3. **TMDL Post-Processing**
   ```python
   tmdl_relationships_file = pbit_dir / "Model" / "relationships.tmdl"
   post_processor = TMDLPostProcessor()
   post_processor.fix_relationships(str(tmdl_relationships_file))
   ```

## Staging Table Handler Integration

### Integration Points in Migration Process
1. **Initialization:** Called during `PackageModelFileGenerator` setup
2. **Settings Loading:** Reads from `settings.json`
3. **Model Processing:** Applied during data model conversion
4. **Table Enhancement:** Integrates with `_enhance_table_with_model_query()`

### Staging Table Generation Process
1. **Complex Relationship Detection**
   - Analyzes multi-key relationships
   - Identifies tables requiring staging support

2. **Staging Table Creation**
   - **Naming:** `stg_[TABLE1]_[TABLE2]`
   - **Output:** Individual JSON files (e.g., `table_stg_PURCHASE_ORDER_DESCRIPTIONS_PURCHASE_ORDER_LINE.json`)

3. **Model Handling Approaches**
   - **merged_tables:** Preserves structure, adds staging columns
   - **star_schema:** Creates separate staging entities

## Complete File Output Inventory

### Extracted Directory (38 files)
- `package_info.json` - Complete package metadata
- `sql_relationships.json` - All relationship definitions
- `sql_filtered_relationships.json` - Filtered relationships
- `sql_relationship_joins.csv` - Tabular relationship analysis
- `query_subjects.json` - Query subject definitions
- `table_[NAME].json` - Individual table definitions (8 tables)
- `table_stg_[TABLE1]_[TABLE2].json` - Staging tables (8 staging tables)
- `calculations.json` - Consolidated calculations
- `relationships.json` - Final relationships
- Configuration files: `model.json`, `database.json`, `report_config.json`

### Intermediate Reports Directory (265 files)
- 4 report subdirectories with complete individual migrations
- Each contains: extracted/, pbit/, and generated Power BI files

### Final PBIT Directory (133 files)
- `.pbixproj.json` - Project configuration
- `Model/database.tmdl` - Tabular model definition
- `Model/tables/` - Individual table TMDL files
- `Model/relationships/` - Relationship TMDL files

## Key Success Metrics
- **Input:** 1 package + 4 reports
- **Intermediate:** 4 individual report migrations
- **Tables Processed:** 8 main tables + 8 staging tables
- **Relationships:** Complex multi-key relationships with staging support
- **Output:** Single unified Power BI semantic model

This detailed process ensures complex Cognos packages with multiple reports are converted to optimized Power BI models with proper staging table support for complex relationships.

## Detailed Component Analysis

### ConsolidatedPackageExtractor Deep Dive
**Location:** `cognos_migrator/extractors/packages/consolidated_package_extractor.py`

#### Architecture and Coordination
The `ConsolidatedPackageExtractor` acts as the orchestrator for all package extraction operations, coordinating multiple specialized extractors:

1. **Specialized Extractor Initialization**
   ```python
   self.structure_extractor = PackageStructureExtractor(logger)
   self.query_subject_extractor = PackageQuerySubjectExtractor(logger)
   self.relationship_extractor = PackageRelationshipExtractor(logger)
   self.calculation_extractor = PackageCalculationExtractor(logger)
   self.filter_extractor = PackageFilterExtractor(logger)
   ```

2. **XML Namespace Management**
   - Parses package XML once: `tree = ET.parse(package_file_path)`
   - Updates namespaces on all extractors: `extractor.update_namespaces_from_root(root)`
   - Ensures consistent XML parsing across all specialized extractors

3. **Coordinated Extraction Process**
   - **Structure Extraction:** Package metadata and organization
   - **Query Subject Extraction:** Table definitions and column metadata
   - **Relationship Extraction:** Inter-table relationships and joins
   - **Calculation Extraction:** Cognos expressions and DAX conversions
   - **Filter Extraction:** Package-level filters and constraints

#### Table Filtering Integration
**Function:** `extract_package()` with `required_tables` parameter

```python
def extract_package(self, package_file_path: str, output_dir: str, 
                   required_tables: Optional[set] = None) -> Dict[str, Any]:
```

- **Filtering Logic:** Only extracts tables actually used by reports
- **Performance Optimization:** Reduces extraction time and output size
- **Integration Point:** Called from `_migrate_shared_model()` with report-derived table list

#### Data Model Conversion
**Function:** `convert_to_data_model()`

1. **Table Processing**
   - Converts query subjects to Power BI tables
   - Maps Cognos data types to Power BI equivalents
   - Processes column metadata and annotations

2. **Relationship Processing**
   - Converts Cognos relationships to Power BI relationships
   - Handles cardinality mapping and join types
   - Integrates with staging table requirements

3. **Model Enhancement**
   - **Function:** `_enhance_table_with_model_query()`
   - Adds M-query definitions to tables
   - Integrates with staging table handler for complex relationships

### SQLRelationshipExtractor Deep Dive
**Location:** `cognos_migrator/extractors/packages/sql_relationship_extractor.py`

#### Core Functionality
1. **Relationship Analysis**
   ```python
   def _process_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
   ```
   - Analyzes Cognos relationship XML
   - Determines join types (INNER, LEFT OUTER, RIGHT OUTER)
   - Maps cardinalities (0..1 to 1..n, 1..1 to 1..n)

2. **SQL Generation**
   - **Join SQL:** `RIGHT OUTER JOIN PURCHASE_ORDER_LINE ON ...`
   - **Power BI Config:** `Many-to-One, Single Direction Filter`
   - **Cardinality Mapping:** Cognos to Power BI relationship types

3. **Multi-Key Relationship Handling**
   ```python
   "keys_a": ["PO_NUMBER", "RELEASE_NUMBER", "PO_LINE_NUMBER", "SITE_NUMBER"]
   "keys_b": ["PO_NUMBER", "RELEASE_NUMBER", "PO_LINE_NUMBER", "SITE_NUMBER"]
   ```
   - Identifies complex multi-column joins
   - Triggers staging table creation for complex relationships

#### Output Files Generated
1. **sql_relationships.json**
   - Complete relationship definitions with SQL joins
   - Original Cognos relationship metadata preserved
   - Power BI configuration mappings

2. **sql_relationship_joins.csv**
   - Tabular format for relationship analysis
   - Join type and cardinality information
   - Used for debugging and validation

3. **sql_filtered_relationships.json**
   - **Function:** `_filter_staging_table_relationships()`
   - Only relationships requiring staging tables
   - Filtered by model table usage

#### Integration with Staging Tables
- **Model Table Filtering:** Uses `model_tables` parameter to filter relationships
- **Staging Table Detection:** Identifies relationships requiring staging support
- **SQL Join Logic:** Provides SQL foundation for staging table M-queries

### StagingTableHandler Detailed Integration
**Location:** `cognos_migrator/generators/staging_table_handler.py`

#### Integration Points in Migration Flow

1. **Initialization During Model Generation**
   ```python
   # In PackageModelFileGenerator
   staging_handler = StagingTableHandler(settings)
   processed_model = staging_handler.process_data_model(data_model)
   ```

2. **Settings-Based Configuration**
   ```json
   {
     "staging_tables": {
       "enabled": true,
       "naming_prefix": "stg_",
       "model_handling": "merged_tables"
     }
   }
   ```

#### Complex Relationship Detection Logic
**Function:** `_identify_complex_relationship_tables()`

1. **Multi-Key Analysis**
   - Scans relationships for multiple join keys
   - Identifies tables involved in complex joins
   - Returns set of table names requiring staging support

2. **Cardinality Analysis**
   - Analyzes relationship cardinalities
   - Identifies many-to-many relationships
   - Flags relationships requiring bridge tables

#### Staging Table Creation Process

1. **Merged Tables Approach** (`model_handling: "merged_tables"`)
   ```python
   def _process_merged_tables(self, data_model: DataModel) -> DataModel:
   ```
   - **Process:** Preserves original table structure
   - **Enhancement:** Adds staging columns for complex joins
   - **Relationship Updates:** Modifies relationships to use merged tables
   - **Output:** Enhanced tables with staging support

2. **Star Schema Approach** (`model_handling: "star_schema"`)
   ```python
   def _process_star_schema(self, data_model: DataModel) -> DataModel:
   ```
   - **Process:** Creates separate staging entities
   - **M-Query Generation:** Builds queries combining related tables
   - **Dimensional Design:** Maintains star schema principles
   - **Output:** Separate staging tables with dedicated M-queries

#### Staging Table File Generation
**Naming Convention:** `table_stg_[TABLE1]_[TABLE2].json`

**Example Output Structure:**
```json
{
  "source_name": "stg_PURCHASE_ORDER_DESCRIPTIONS_PURCHASE_ORDER_LINE",
  "name": "stg_PURCHASE_ORDER_DESCRIPTIONS_PURCHASE_ORDER_LINE",
  "columns": [
    {
      "source_name": "ITEM_NUMBER",
      "datatype": "string",
      "source_column": "ITEM_NUMBER"
    }
  ]
}
```

### FastAPI/DAX API Integration
**Location:** `Bi-Migrator-Cognos-DAX-API/` (Git Submodule)

#### FastAPI Service Architecture
**Main Application:** `Bi-Migrator-Cognos-DAX-API/main.py`

```python
app = FastAPI(
    title="Cognos to Power BI Migration API",
    description="Streamlined API for converting Cognos formulas to DAX and generating Power BI M-Query expressions",
    version="2.0.0"
)
```

#### API Endpoints and Integration

1. **Health Check Endpoint**
   - **Route:** `/health`
   - **Purpose:** Service availability verification
   - **Integration:** Used by migration system to verify DAX API availability

2. **DAX Conversion Endpoints**
   - **Route:** `/api/convert-to-dax`
   - **Purpose:** Convert Cognos expressions to DAX
   - **Integration:** Called during calculation extraction and processing

3. **M-Query Generation Endpoints**
   - **Route:** `/api/generate-mquery`
   - **Purpose:** Generate Power BI M-queries from SQL and metadata
   - **Integration:** Used by M-query converters during table processing

#### LLM Service Client Integration
**Location:** `cognos_migrator/llm_service.py`

```python
class LLMServiceClient:
    def __init__(self, base_url=None, api_key: Optional[str] = None):
        if not base_url:
            base_url = os.environ.get('DAX_API_URL', 'http://localhost:8080')
```

#### Integration Points in Migration Process

1. **Expression Conversion**
   ```python
   # In ExpressionConverter
   def convert_expression(self, cognos_formula: str, table_name: str = None):
       # Calls FastAPI service for DAX conversion
   ```

2. **M-Query Generation**
   ```python
   # In MQueryConverter classes
   def convert_to_m_query(self, table: Table, **kwargs) -> str:
       # Uses LLM service for optimized M-query generation
   ```

3. **Configuration Integration**
   ```python
   # In migration configuration
   config = MigrationConfig(
       llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
       llm_service_enabled=True
   )
   ```

#### Service Communication Flow

1. **Service Discovery**
   - Migration system checks `DAX_API_URL` environment variable
   - Defaults to `http://localhost:8080` for local development
   - Docker network communication in containerized environments

2. **Request Processing**
   - **Context Building:** Assembles table metadata, relationships, and filters
   - **API Call:** Sends structured request to FastAPI service
   - **Response Processing:** Integrates generated DAX/M-query into migration output

3. **Error Handling**
   - **Fallback Logic:** Uses basic conversion if API unavailable
   - **Retry Mechanism:** Configurable retry attempts for network issues
   - **Logging Integration:** Comprehensive error logging and debugging

#### Docker Integration
**Configuration:** `Bi-Migrator-Cognos-DAX-API/docker-compose.yml`

- **Service Isolation:** DAX API runs as separate containerized service
- **Network Communication:** Internal Docker network for service-to-service calls
- **Environment Configuration:** Environment-based service discovery
- **Scalability:** Independent scaling of DAX processing capabilities

## Complete Integration Flow Summary

### Phase-by-Phase Integration

1. **Migration Orchestration**
   - Settings loaded from `settings.json`
   - FastAPI service availability checked
   - LLM service client initialized

2. **Individual Report Migration**
   - Each report processed independently
   - DAX API called for expression conversions
   - M-query generation uses LLM service

3. **Package Extraction**
   - `ConsolidatedPackageExtractor` coordinates all extraction
   - `SQLRelationshipExtractor` generates relationship SQL
   - Table filtering based on report requirements

4. **Staging Table Integration**
   - `StagingTableHandler` processes complex relationships
   - Creates staging tables based on SQL relationship analysis
   - Integrates with M-query generation for staging queries

5. **Data Model Consolidation**
   - Report and package data merged
   - Staging tables integrated into final model
   - Relationships optimized based on staging requirements

6. **Power BI Project Generation**
   - Final M-queries generated with LLM service support
   - TMDL files created with staging table definitions
   - Complete Power BI project structure generated

This comprehensive integration ensures that complex Cognos packages with multiple reports, advanced relationships, and sophisticated expressions are successfully converted to optimized Power BI semantic models with full DAX and M-query support.
