# Adding a New File Type to BIMigrator

This guide explains how to add support for a new file type in the BIMigrator project. We'll use the `.pbixproj.json` implementation as an example.

## Overview

Adding a new file type requires:
1. Creating a data class
2. Creating a parser
3. Creating a generator
4. Adding template configuration
5. Creating a template file
6. Integrating with main.py

## Step-by-Step Guide

### 1. Create a Data Class

Add your data class to `config/data_classes.py`. Example:

```python
@dataclass
class PowerBiProject:
    """Project configuration."""
    version: str = '1.0'
    created: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
```

### 2. Create a Parser

Create a new parser in `src/parsers/` that inherits from `BaseParser`. Example (`pbixproj_parser.py`):

```python
from config.data_classes import PowerBiProject
from .base_parser import BaseParser

class PbixprojParser(BaseParser):
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        super().__init__(twb_path, config)
    
    def extract_pbixproj_info(self) -> PowerBiProject:
        """Extract information for the file"""
        now = datetime.now()
        return PowerBiProject(
            version="1.0",
            created=now,
            last_modified=now
        )
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all information and save intermediate file"""
        data = {
            'PowerBiProject': self.extract_pbixproj_info()
        }
        self.save_intermediate(data, 'project')
        return data
```

### 3. Create a Generator

Create a new generator in `src/generators/` that inherits from `BaseTemplateGenerator`. Example (`pbixproj_generator.py`):

```python
from pathlib import Path
from typing import Dict, Any, Optional
from config.data_classes import PowerBiProject
from .base_template_generator import BaseTemplateGenerator

class PbixprojGenerator(BaseTemplateGenerator):
    def __init__(self, config_path: str, input_path: str, output_dir: Path):
        super().__init__(config_path, input_path, output_dir)
    
    def generate_pbixproj(self, project_info: PowerBiProject, output_dir: Optional[Path] = None) -> Path:
        """Generate the file"""
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'
        
        return self.generate_file('pbixproj', project_info)
```

### 4. Add Template Configuration

Add your template configuration to `config/twb-to-pbi.yaml`:

```yaml
Templates:
  base_dir: templates
  mappings:
    your_file_type:
      template: template_file.ext  # Template file name
      output: path/to/output.ext   # Output path pattern
      config: ConfigClassName      # Class name in config
      dataclass: DataClassName    # Data class to use
```

### 5. Create Template File

Create a template file in the `templates/` directory. Use Jinja2 syntax for variable substitution:

```json
{
  "version": "{{version}}",
  "created": "{{created}}",
  "lastModified": "{{last_modified}}"
}
```

### 6. Integrate with Main Flow

Add your file generation to `main.py`:

```python
# Initialize parser
your_parser = YourParser(input_path, config)
parsed_info = your_parser.extract_info()

# Initialize generator
your_generator = YourGenerator(
    config_path=config_path,
    input_path=input_path,
    output_dir=structure_generator.base_dir
)

# Generate file
file_path = your_generator.generate_file(parsed_info, output_dir=structure_generator.base_dir)
```

## Best Practices

1. **Type Hints**: Always use type hints in your Python code
2. **Documentation**: Include docstrings for classes and methods
3. **Error Handling**: Implement proper error handling in parsers and generators
4. **Intermediate Files**: Use `save_intermediate()` in parsers for debugging
5. **Testing**: Add unit tests for your parser and generator

## Example PR

You can refer to PR #14_parser/#pbixproj for a complete example of adding the `.pbixproj.json` file type:
- Added PowerBiProject data class
- Created PbixprojParser
- Created PbixprojGenerator
- Added template configuration
- Created pbixproj.json template
- Integrated with main.py

## File Structure

```
BIMigrator/
├── config/
│   ├── data_classes.py     # Add your data class here
│   └── twb-to-pbi.yaml    # Add template configuration here
├── src/
│   ├── parsers/
│   │   └── your_parser.py  # Add your parser here
│   └── generators/
│       └── your_generator.py # Add your generator here
└── templates/
    └── your_template.ext   # Add your template here
```
