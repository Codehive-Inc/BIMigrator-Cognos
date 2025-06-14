# CPF Extraction Process

## Overview

The CPF (Cognos Package File) extraction process enhances the migration by incorporating metadata from Cognos Framework Manager model files. This metadata provides additional context about data sources, relationships, and business rules that may not be present in the report specification alone.

## Process Flow

1. **Load CPF File**
   - Parse the XML structure of the .cpf file
   - Extract metadata about namespaces, query subjects, and relationships

2. **Extract Metadata Components**
   - Extract data sources and connection information
   - Extract query subjects (tables) and query items (columns)
   - Extract relationships between query subjects
   - Extract calculations and business rules

3. **Enhance Migration with CPF Metadata**
   - Augment data model with additional metadata
   - Improve relationship detection
   - Enhance column data types and descriptions

## Key Components

### CPFExtractor Class

The `CPFExtractor` class in `cpf_extractor.py` handles the extraction and processing of CPF metadata:

```python
class CPFExtractor:
    def __init__(self, cpf_file_path: Optional[str] = None):
        self.cpf_file_path = cpf_file_path
        self.logger = logging.getLogger(__name__)
        self.metadata = {}
        self.parser = None
        
        if cpf_file_path:
            self.load_cpf(cpf_file_path)
    
    def load_cpf(self, cpf_file_path: str) -> bool:
        """Load and parse a CPF file"""
        try:
            self.cpf_file_path = cpf_file_path
            self.parser = CPFParser(cpf_file_path)
            
            if self.parser.parse():
                self.metadata = self.parser.extract_all()
                self.logger.info(f"Successfully loaded CPF file: {cpf_file_path}")
                return True
            else:
                self.logger.error(f"Failed to parse CPF file: {cpf_file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading CPF file: {e}")
            return False
    
    def get_query_subjects(self) -> List[Dict[str, Any]]:
        """Get all query subjects (tables) from the CPF metadata"""
        if not self.metadata:
            return []
        
        return self.metadata.get('query_subjects', [])
    
    def get_relationships(self) -> List[Dict[str, Any]]:
        """Get all relationships from the CPF metadata"""
        if not self.metadata:
            return []
        
        return self.metadata.get('relationships', [])
```

### CPFParser Class

The `CPFParser` class in `cpf_parser.py` handles the parsing of CPF files:

```python
class CPFParser:
    def __init__(self, cpf_file_path: str):
        self.cpf_file_path = cpf_file_path
        self.logger = logging.getLogger(__name__)
        self.root = None
        self.namespaces = {}
        
    def parse(self) -> bool:
        """Parse the CPF file"""
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the XML file
            tree = ET.parse(self.cpf_file_path)
            self.root = tree.getroot()
            
            # Extract namespaces
            self.namespaces = self._extract_namespaces()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing CPF file: {e}")
            return False
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all metadata from the CPF file"""
        if not self.root:
            return {}
        
        return {
            'namespaces': self.namespaces,
            'data_sources': self._extract_data_sources(),
            'query_subjects': self._extract_query_subjects(),
            'relationships': self._extract_relationships(),
            'calculations': self._extract_calculations()
        }
```

### Integration with Migration Process

The CPF metadata is integrated into the migration process in the `CognosMigrator` class:

```python
def __init__(self, config: MigrationConfig, base_url: str = None, session_key: str = None, cpf_file_path: str = None):
    # Initialize components
    # ...
    
    # Initialize CPF extractor if a CPF file path is provided
    self.cpf_extractor = None
    if cpf_file_path:
        self.cpf_extractor = CPFExtractor(cpf_file_path)
        if not self.cpf_extractor.metadata:
            self.logger.warning(f"Failed to load CPF file: {cpf_file_path}")
            self.cpf_extractor = None
        else:
            self.logger.info(f"Successfully loaded CPF file: {cpf_file_path}")

def migrate_report(self, report_id: str, output_path: str) -> bool:
    # ...
    
    # If CPF metadata is available, enhance the Power BI project with it
    if self.cpf_extractor:
        self._enhance_with_cpf_metadata(powerbi_project)
    
    # ...
```

## Benefits of CPF Extraction

1. **Improved Data Model Accuracy**: CPF files contain the complete data model definition, which helps create more accurate Power BI models.

2. **Enhanced Relationships**: CPF files define relationships between tables that might not be explicitly used in reports.

3. **Better Data Type Mapping**: CPF files contain precise data type information for columns.

4. **Business Logic Preservation**: Calculations and business rules defined in Framework Manager can be extracted and converted to DAX.

5. **Consistent Naming**: CPF files contain business-friendly names and descriptions that improve the usability of the migrated Power BI reports.

## Output

The CPF extraction process enhances the Power BI project with additional metadata, resulting in a more accurate and complete data model. The extracted metadata is also saved to the extracted folder as `cpf_metadata.json` for reference.
