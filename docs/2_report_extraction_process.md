# Report Extraction Process

## Overview

The report extraction process connects to the Cognos Analytics API, retrieves report specifications and metadata, and saves the raw data for further processing.

## Process Flow

1. **Initialize Cognos Client**
   - Connect to Cognos Analytics API using configuration settings
   - Authenticate using provided credentials or session key

2. **Fetch Report Data**
   - Retrieve report specification (XML)
   - Retrieve report metadata (JSON)
   - Extract report details (name, ID, path, type)

3. **Save Extracted Data**
   - Create output directory structure
   - Save report specification as XML
   - Save report metadata as JSON
   - Save report details as JSON

## Key Components

### CognosClient Class

The `CognosClient` class in `client.py` handles communication with the Cognos Analytics API:

```python
class CognosClient:
    def __init__(self, config: CognosConfig, base_url: str = None, session_key: str = None):
        # Initialize client with configuration
        
    def test_connection(self) -> bool:
        # Test connection to Cognos API
        
    def get_report(self, report_id: str) -> CognosReport:
        # Fetch report data from Cognos
        
    def list_root_objects(self) -> List[Dict]:
        # List available content at root level
        
    def list_child_objects(self, folder_id: str) -> List[Dict]:
        # List contents of a folder
        
    def list_reports_in_folder(self, folder_id: str, recursive: bool = True) -> List[CognosReport]:
        # List all reports in a folder
```

### Data Extraction in CognosMigrator

The `CognosMigrator` class in `migrator.py` orchestrates the extraction process:

```python
def migrate_report(self, report_id: str, output_path: str) -> bool:
    # Create output directory structure
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create extracted directory for raw extracted data
    extracted_dir = output_dir / "extracted"
    extracted_dir.mkdir(exist_ok=True)
    
    # Fetch Cognos report
    cognos_report = self.cognos_client.get_report(report_id)
    
    # Save raw Cognos report data to extracted folder
    self._save_extracted_data(cognos_report, extracted_dir)
```

### Saving Extracted Data

The `_save_extracted_data` method saves the raw extracted data:

```python
def _save_extracted_data(self, cognos_report, extracted_dir):
    # Save report specification XML
    spec_path = extracted_dir / "report_specification.xml"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(cognos_report.specification)
    
    # Save report metadata as JSON
    metadata_path = extracted_dir / "report_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(cognos_report.metadata, f, indent=2)
    
    # Save report details as JSON
    details_path = extracted_dir / "report_details.json"
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump({
            "id": cognos_report.id,
            "name": cognos_report.name,
            "path": cognos_report.path,
            "type": cognos_report.type,
            "extractionTime": str(datetime.now())
        }, f, indent=2)
```

## Output Structure

The extracted data is saved in the following structure:

```
output/
└── report_{report_id}/
    └── extracted/
        ├── report_specification.xml  # Cognos report XML specification
        ├── report_metadata.json      # Report metadata
        └── report_details.json       # Basic report details
```
