# Cognos Analytics to Power BI Migration Tool

A comprehensive tool for migrating IBM Cognos Analytics reports to Microsoft Power BI, featuring automated conversion of data models, reports, and visualizations.

## Features

- **Automated Report Migration**: Convert Cognos Analytics reports to Power BI project format
- **Data Model Conversion**: Transform Cognos data sources, tables, and relationships to Power BI data model
- **Template-Based Generation**: Uses PyBars3 templating for flexible and customizable output
- **Batch Processing**: Migrate multiple reports or entire folders at once
- **Documentation Generation**: Automatic migration reports and documentation
- **Modular Architecture**: Well-organized, extensible codebase

## Architecture

The tool is built with a modular architecture:

```
cognos_migrator/
├── __init__.py          # Package initialization
├── config.py            # Configuration management
├── models.py            # Data models and structures
├── client.py            # Cognos Analytics API client
├── parsers.py           # Report parsing and conversion logic
├── generators.py        # Power BI project file generation
└── migrator.py          # Main migration orchestrator
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cognos_to_bimigrator
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   Copy `.env.example` to `.env` and configure your Cognos Analytics connection:
   ```bash
   cp .env.example .env
   ```

4. **Configure your environment**:
   ```env
   COGNOS_URL=https://your-cognos-server.com
   COGNOS_USERNAME=your_username
   COGNOS_PASSWORD=your_password
   COGNOS_NAMESPACE=LDAP
   TEMPLATE_DIRECTORY=bimigrator/templates
   OUTPUT_DIRECTORY=output
   ```

## Usage

### Command Line Interface

The tool provides several command-line options:

```bash
# Run demonstration
python main.py demo

# Migrate a single report
python main.py migrate-report <report_id> [output_path]

# Migrate all reports in a folder
python main.py migrate-folder <folder_id> [output_path] [recursive]

# Validate prerequisites
python main.py validate
```

### Programmatic Usage

```python
from cognos_migrator.config import MigrationConfig
from cognos_migrator.migrator import CognosToPowerBIMigrator

# Load configuration
config = MigrationConfig(
    cognos_url="https://your-cognos-server.com",
    cognos_username="username",
    cognos_password="password",
    cognos_namespace="LDAP",
    template_directory="bimigrator/templates",
    output_directory="output"
)

# Initialize migrator
migrator = CognosToPowerBIMigrator(config)

# Migrate a single report
success = migrator.migrate_report("report_id", "output/path")

# Migrate multiple reports
results = migrator.migrate_multiple_reports(
    ["report1", "report2", "report3"], 
    "output/base/path"
)

# Migrate entire folder
results = migrator.migrate_folder("folder_id", "output/path")
```

### Batch Migration

For large-scale migrations, use the batch processing capabilities:

```python
from cognos_migrator.migrator import MigrationBatch

# Create batch processor
batch_processor = MigrationBatch(migrator)

# Define migration plan
source_config = {
    'report_ids': ['report1', 'report2'],
    'folder_ids': ['folder1', 'folder2']
}

# Create and execute migration plan
plan = batch_processor.create_migration_plan(source_config)
results = batch_processor.execute_migration_plan(plan, "output/path")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COGNOS_URL` | Cognos Analytics server URL | `http://localhost:9300` |
| `COGNOS_USERNAME` | Username for authentication | - |
| `COGNOS_PASSWORD` | Password for authentication | - |
| `COGNOS_NAMESPACE` | Authentication namespace | `LDAP` |
| `TEMPLATE_DIRECTORY` | Path to template files | `bimigrator/templates` |
| `OUTPUT_DIRECTORY` | Default output directory | `output` |
| `BATCH_SIZE` | Batch processing size | `10` |
| `PARALLEL_PROCESSING` | Enable parallel processing | `false` |
| `INCLUDE_DATA_SOURCES` | Include data source migration | `true` |
| `GENERATE_DOCUMENTATION` | Generate migration docs | `true` |

### Template Customization

The tool uses PyBars3 templates for generating Power BI files. Templates are located in `bimigrator/templates/`:

- `database.tmdl` - Database definition template
- `Table.tmdl` - Table definition template
- `relationship.tmdl` - Relationships template
- `model.tmdl` - Model definition template
- `pbixproj.json` - Project file template
- `report.json` - Report definition template

You can customize these templates to match your specific requirements.

## Output Structure

The migration tool generates a complete Power BI project structure:

```
output/
└── report_<id>/
    ├── .pbixproj.json           # Project file
    ├── Version.txt              # Version information
    ├── DiagramLayout.json       # Model diagram layout
    ├── ReportMetadata.json      # Report metadata
    ├── ReportSettings.json      # Report settings
    ├── Model/                   # Data model files
    │   ├── database.tmdl
    │   ├── model.tmdl
    │   ├── relationships.tmdl
    │   ├── expressions.tmdl
    │   ├── cultures/
    │   │   └── en-US.tmdl
    │   └── tables/
    │       ├── Table1.tmdl
    │       └── Table2.tmdl
    ├── Report/                  # Report files
    │   ├── config.json
    │   ├── report.json
    │   └── sections/
    │       └── 000_Page1/
    ├── StaticResources/         # Static resources
    └── migration_report.md      # Migration documentation
```

## Migration Process

The migration follows these steps:

1. **Authentication**: Connect to Cognos Analytics using provided credentials
2. **Report Extraction**: Fetch report definition and metadata from Cognos
3. **Parsing**: Parse Cognos report specification (XML/JSON)
4. **Conversion**: Convert Cognos structures to Power BI equivalents
5. **Generation**: Generate Power BI project files using templates
6. **Documentation**: Create migration reports and documentation

## Supported Features

### Data Sources
- SQL databases (SQL Server, Oracle, DB2, etc.)
- File-based sources (CSV, Excel)
- Cloud data sources (with connection string mapping)

### Report Elements
- Tables and crosstabs
- Charts and visualizations
- Filters and parameters
- Basic formatting and styling

### Data Model
- Tables and columns
- Relationships (1:1, 1:many, many:many)
- Calculated fields and measures
- Hierarchies and folders

## Limitations

- Complex Cognos-specific features may require manual adjustment
- Custom visualizations need manual recreation in Power BI
- Advanced formatting may not transfer completely
- Cognos Framework Manager models require separate handling

## Examples

The `examples/` directory contains sample Power BI projects that demonstrate the expected output structure:

- `PUAT DataLoad Analysis/` - Data analysis dashboard
- `Sales Dashboard/` - Sales reporting dashboard

These examples show the file structure and content that the migration tool generates.

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify Cognos URL, username, and password
   - Check namespace configuration
   - Ensure user has appropriate permissions

2. **Template Errors**
   - Verify template directory exists
   - Check template syntax (PyBars3 format)
   - Ensure all required templates are present

3. **Migration Failures**
   - Check Cognos report accessibility
   - Verify output directory permissions
   - Review migration logs for specific errors

### Logging

The tool generates detailed logs in `migration.log`. Set log level using:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Project Structure

```
cognos_to_bimigrator/
├── cognos_migrator/         # Main package
├── bimigrator/             # Templates and resources
├── examples/               # Sample projects
├── main.py                 # CLI entry point
├── pyproject.toml          # Project configuration
├── .env                    # Environment variables
└── README.md               # This file
```

### Adding New Features

1. **New Data Sources**: Extend `client.py` and `parsers.py`
2. **New Templates**: Add templates to `bimigrator/templates/`
3. **New Report Types**: Extend `models.py` and `parsers.py`
4. **New Output Formats**: Extend `generators.py`

### Testing

Run the validation command to test your setup:

```bash
python main.py validate
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the migration logs
3. Create an issue in the repository
4. Provide detailed error information and logs

## Roadmap

- [ ] Support for Cognos Framework Manager models
- [ ] Advanced visualization mapping
- [ ] Incremental migration capabilities
- [ ] Power BI Service deployment integration
- [ ] Enhanced error handling and recovery
- [ ] GUI interface for non-technical users
