# Cognos to Power BI Migration System

A comprehensive, production-ready system for migrating IBM Cognos Analytics reports to Microsoft Power BI using the Cognos REST API.

## 🚀 Features

- **API-First Approach**: Direct integration with Cognos Analytics REST API (no XML parsing required)
- **Modular Architecture**: Clean, extensible codebase with separation of concerns
- **Template-Based Generation**: Flexible Power BI project file generation using templates
- **Batch Processing**: Support for migrating individual reports or entire folders
- **Error Handling**: Comprehensive error handling and logging
- **Configuration Management**: Environment-based configuration with validation
- **Production Ready**: Built with enterprise-grade patterns and practices

## 🏗️ Architecture

```
cognos_to_bimigrator/
├── cognos_migrator/           # Core migration package
│   ├── client.py             # Cognos API client
│   ├── config.py             # Configuration management
│   ├── generators.py         # Power BI file generators
│   ├── migrator.py           # Migration orchestrator
│   ├── models.py             # Data models
│   └── parsers.py            # Data parsers
├── bimigrator/
│   └── templates/            # Power BI project templates
├── examples/                 # Example Power BI projects
├── main.py                   # CLI interface
├── test_cognos_connection.py # Connection testing
└── demo_migration.py         # System demonstration
```

## 📋 Prerequisites

- Python 3.8+
- Access to IBM Cognos Analytics with REST API enabled
- Valid Cognos authentication credentials
- Power BI Desktop (for opening generated projects)

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cognos_to_bimigrator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or using uv
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Cognos credentials
   ```

## 🔧 Configuration

Create a `.env` file with your Cognos Analytics configuration:

```env
# Cognos App Base URL
BASE_URL=http://your-cognos-server:9300/api/v1

# Cognos API Authorization
KEY=IBM-BA-Authorization
VALUE=CAM your-session-token-here

# Migration Configuration
OUTPUT_DIR=output
TEMPLATE_DIR=bimigrator/templates
PRESERVE_STRUCTURE=true
INCLUDE_METADATA=true
GENERATE_DOCS=true
```

## 🚀 Usage

### Test Connection
```bash
python test_cognos_connection.py
```

### Migrate Single Report
```bash
python main.py migrate-report <report_id>
```

### Migrate Folder
```bash
python main.py migrate-folder <folder_id>
```

### Validate Configuration
```bash
python main.py validate
```

### Run System Demo
```bash
python demo_migration.py
```

## 📊 Generated Output

The system generates a complete Power BI project structure:

```
output/
└── <report_name>/
    ├── .pbixproj.json        # Project configuration
    ├── DiagramLayout.json    # Model diagram layout
    ├── ReportMetadata.json   # Report metadata
    ├── ReportSettings.json   # Report settings
    ├── Version.txt           # Version information
    ├── Model/
    │   ├── database.tmdl     # Database connection
    │   ├── model.tmdl        # Data model
    │   ├── relationships.tmdl # Table relationships
    │   ├── cultures/         # Localization
    │   └── tables/           # Table definitions
    ├── Report/
    │   ├── config.json       # Report configuration
    │   ├── report.json       # Report definition
    │   └── sections/         # Report pages
    └── StaticResources/      # Images and themes
```

## 🔌 API Integration

The system integrates with the following Cognos Analytics REST API endpoints:

- `/content` - Browse content hierarchy
- `/content/{id}` - Get specific content items
- `/content/{id}/items` - Get child items
- `/datasources` - Manage data sources
- `/modules` - Access report modules

## 🏛️ Architecture Patterns

### Client Layer (`client.py`)
- HTTP client for Cognos API
- Authentication management
- Request/response handling
- Connection pooling and retries

### Data Layer (`models.py`)
- Pydantic models for type safety
- Data validation and serialization
- Clean data structures

### Parser Layer (`parsers.py`)
- Transform Cognos data to Power BI format
- Handle data type conversions
- Extract metadata and relationships

### Generator Layer (`generators.py`)
- Template-based file generation
- Power BI project structure creation
- Asset management

### Orchestration Layer (`migrator.py`)
- End-to-end migration workflow
- Error handling and recovery
- Progress tracking and logging

## 🔍 Error Handling

The system includes comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Authentication Errors**: Clear error messages and guidance
- **Data Validation**: Type checking and validation at all layers
- **File System Errors**: Proper error handling for file operations
- **API Errors**: Detailed error reporting with context

## 📝 Logging

All operations are logged with appropriate levels:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Logs include:
- API requests and responses
- Migration progress
- Error details and stack traces
- Performance metrics

## 🧪 Testing

### Connection Testing
```bash
python test_cognos_connection.py
```

### System Testing
```bash
python test_system.py
```

### Integration Testing
```bash
python -m pytest tests/
```

## 🔒 Security

- Environment-based credential management
- No hardcoded secrets
- Secure API token handling
- Input validation and sanitization

## 📈 Performance

- Asynchronous API calls where possible
- Connection pooling and reuse
- Efficient data processing
- Memory-conscious design

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the documentation
2. Review the examples
3. Run the demo system
4. Check the logs for detailed error information

## 🔄 Migration Workflow

1. **Discovery**: Connect to Cognos and discover available reports
2. **Extraction**: Fetch report metadata and structure via API
3. **Transformation**: Convert Cognos data model to Power BI format
4. **Generation**: Create Power BI project files using templates
5. **Validation**: Verify generated files and structure
6. **Documentation**: Generate migration reports and documentation

## 🎯 Roadmap

- [ ] Advanced data source mapping
- [ ] Custom visualization migration
- [ ] Automated testing framework
- [ ] Performance optimization
- [ ] Multi-tenant support
- [ ] Cloud deployment options

---

**Built with ❤️ for enterprise data migration**
