# Power BI Project Generation Process

## Overview

The Power BI project generation process creates the necessary files for a Power BI template (.pbit) from the data model and report structure. This includes generating TMDL (Tabular Model Definition Language) files and report JSON files.

The BIMigrator-Cognos tool supports two types of Power BI project generation:

1. **Report Generation**: Creates a Power BI report with visuals and a data model
2. **Module Generation**: Creates a Power BI dataset from a Cognos data module

## Common Process Flow

Both report and module generation follow these common steps:

1. **Initialize Project Structure**
   - Create directory structure for Power BI project
   - Set up Model and Report directories

2. **Generate Core Model Files**
   - Create database.tmdl file
   - Create model.tmdl file with appropriate PBIDesktopVersion annotation
   - Generate table files for each table
   - Generate relationships.tmdl file using relationship names as IDs
   - Generate expressions.tmdl file (for measures)
   - Generate culture files with correct naming (e.g., en-US.tmdl) and version (1.0.0)

3. **Generate Metadata Files**
   - Create metadata files required by Power BI

## Report-Specific Generation

Report generation includes these additional steps:

1. **Generate Report Files**
   - Create report.json file with visual definitions
   - Create config.json file with report settings
   - Generate section files for each page
   - Create visual containers mapped from Cognos visuals

2. **Generate Visual Layout**
   - Position visuals according to Cognos layout
   - Apply formatting and styling
   - Configure interactions between visuals

## Module-Specific Generation

Module generation includes these additional steps:

1. **Generate Module-Specific Model Files**
   - Create tables with appropriate structure for modules
   - Generate relationships with correct cardinality
   - Preserve module-specific metadata

2. **Generate Basic Report Structure**
   - Create minimal report structure without visuals
   - Set up appropriate configuration for dataset usage

## Key Components

### PowerBIProjectGenerator Class

The `PowerBIProjectGenerator` class in `generators.py` handles the generation of Power BI project files:

```python
class PowerBIProjectGenerator:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.template_engine = TemplateEngine(config.template_directory)
        self.visual_generator = VisualContainerGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM service client if enabled
        self.llm_service = None
        if hasattr(config, 'llm_service_enabled') and config.llm_service_enabled:
            from ..llm_service import LLMServiceClient
            self.llm_service = LLMServiceClient(
                base_url=config.llm_service_url,
                api_key=getattr(config, 'llm_service_api_key', None)
            )
    
    def generate_project(self, project: PowerBIProject, output_path: str) -> bool:
        """Generate complete Power BI project structure"""
        try:
            # Create output directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate project file
            self._generate_project_file(project, output_dir)
            
            # Generate model files
            model_dir = output_dir / "Model"
            model_dir.mkdir(exist_ok=True)
            self._generate_model_files(project.data_model, model_dir)
            
            # Generate report files
            report_dir = output_dir / "Report"
            report_dir.mkdir(exist_ok=True)
            self._generate_report_files(project.report, report_dir)
            
            # Generate metadata files
            self._generate_metadata_files(project, output_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate Power BI project: {e}")
            return False
```

### Model File Generation

The model files are generated using the following methods:

```python
def _generate_model_files(self, data_model: DataModel, output_dir: Path, report_spec: Optional[str] = None):
    """Generate model files (database, tables, relationships)"""
    # Generate database.tmdl file
    self._generate_database_file(data_model, output_dir)
    
    # Generate model.tmdl file
    self._generate_model_file(data_model, output_dir)
    
    # Generate table files
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    self._generate_table_files(data_model.tables, tables_dir, report_spec)
    
    # Generate relationships file if there are relationships
    if data_model.relationships:
        self._generate_relationships_file(data_model.relationships, output_dir)
    
    # Generate expressions file if there are measures
    if data_model.measures:
        self._generate_expressions_file(data_model.measures, output_dir)
    
    # Generate culture files
    self._generate_culture_files(data_model, output_dir)
```

### Table File Generation

Table files are generated using templates and include M-queries for data loading:

```python
def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None):
    """Generate table files"""
    for table in tables:
        # Build context for table template
        context = self._build_table_context(table, report_spec)
        
        # Render table template
        table_content = self.template_engine.render('table.tmdl', context)
        
        # Write table file
        table_file = model_dir / f"{table.name}.tmdl"
        with open(table_file, "w", encoding="utf-8") as f:
            f.write(table_content)
```

### Report File Generation

Report files define the structure and layout of the Power BI report:

```python
def _generate_report_files(self, report: Report, output_dir: Path):
    """Generate report files"""
    # Generate report.json file
    self._generate_report_json(report, output_dir)
    
    # Generate config.json file
    self._generate_report_config(report, output_dir)
    
    # Generate section files
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)
    self._generate_report_sections(report.pages, sections_dir)
```

### Template Engine

The `TemplateEngine` class handles rendering templates for various file types:

```python
class TemplateEngine:
    def __init__(self, template_directory: str):
        self.template_directory = Path(template_directory)
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_directory)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Initialize Handlebars compiler
        self.handlebars_compiler = pybars.Compiler()
        
        self.templates = {}
        self.handlebars_templates = {}
        self._load_templates()
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        # Use Handlebars for specific templates
        if template_name.endswith('.hbs'):
            return self._render_handlebars(template_name, context)
        
        # Use Jinja2 for other templates
        return self._render_jinja(template_name, context)
```

## Output Structure

The Power BI project generation process produces a directory structure compatible with the Power BI Desktop template format (.pbit):

```
pbit/
├── .pbixproj.json
├── Model/
│   ├── database.tmdl
│   ├── model.tmdl
│   ├── relationships.tmdl
│   ├── expressions.tmdl
│   └── tables/
│       ├── Table1.tmdl
│       ├── Table2.tmdl
│       └── ...
├── Report/
│   ├── report.json
│   ├── config.json
│   └── sections/
│       ├── Page1.json
│       ├── Page2.json
│       └── ...
└── [Metadata files]
```

This structure can be opened directly in Power BI Desktop or packaged into a .pbit file for distribution.
