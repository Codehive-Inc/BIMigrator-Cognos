"""Base class for template generators."""
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import yaml
from pybars import Compiler
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class TemplateMapping:
    """Represents a template mapping configuration."""
    template: str
    output: str
    config: str
    dataclass: str
    multiple: bool = False
    name_from: Optional[str] = None

class BaseTemplateGenerator:
    """Base class for template generators."""
    
    def __init__(self, config_path: str, input_path: Optional[str] = None, output_dir: Optional[Path] = None):
        """Initialize with configuration file path.
        
        Args:
            config_path: Path to YAML configuration file
            input_path: Optional path to input file
            output_dir: Optional output directory override
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.template_dir = Path(self.config['Templates']['base_dir'])
        self.base_output_dir = output_dir or Path('output')
        self.intermediate_dir = Path(self.config.get('Output', {}).get('intermediate_dir', 'extracted'))
        self.validate_intermediate = self.config.get('Output', {}).get('validate_intermediate', True)
        self.compiler = Compiler()
        self._template_cache = {}
        
        # Set input name for output path
        self.input_name = Path(input_path).stem if input_path else None
        
        # Set output directory with input name
        self.output_dir = self.base_output_dir / self.input_name if self.input_name else self.base_output_dir
        self.pbit_dir = self.output_dir / 'pbit' if self.input_name else self.output_dir
        self.extracted_dir = self.output_dir / 'extracted' if self.input_name else self.output_dir / 'extracted'

    def _load_template_mappings(self) -> Dict[str, TemplateMapping]:
        """Load template mappings from configuration."""
        mappings = {}
        for key, mapping in self.config['Templates']['mappings'].items():
            mappings[key] = TemplateMapping(**mapping)
        return mappings
    
    def _get_template(self, template_name: str) -> Any:
        """Get compiled template, using cache if available."""
        if template_name not in self._template_cache:
            template_path = self.template_dir / template_name
            with open(template_path, 'r') as f:
                source = f.read()
            self._template_cache[template_name] = self.compiler.compile(source)
        return self._template_cache[template_name]
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with given context."""
        template = self._get_template(template_name)
        return template(context)
    
    def _ensure_dir(self, path: Path) -> None:
        """Ensure directory exists, creating it if necessary."""
        if not path.exists():
            path.mkdir(parents=True)
    
    def generate_file(self, template_type: str, context: Dict[str, Any], name: Optional[str] = None) -> Path:
        """Generate a file from a template.
        
        Args:
            template_type: Type of template to use
            context: Context data for template
            name: Optional name override for the output file
            
        Returns:
            Path to generated file
        """
        # Get template mapping
        mapping = self.config['Templates']['mappings'][template_type]
        
        # Save intermediate JSON
        if self.input_name:
            # Create intermediate dir in output/input_name/extracted
            self.extracted_dir.mkdir(parents=True, exist_ok=True)
            intermediate_file = self.extracted_dir / f"{template_type}.json"
            with open(intermediate_file, 'w') as f:
                if hasattr(context, '__dict__'):
                    json.dump(context.__dict__, f, indent=2)
                else:
                    json.dump(context, f, indent=2)
        
        # Render output path template if it contains variables
        if '{{' in mapping['output']:
            path_template = self.compiler.compile(mapping['output'])
            relative_path = path_template(context)
        else:
            relative_path = mapping['output']
            
        # Override name if provided
        if name:
            relative_path = relative_path.replace(mapping['name_from'], name)
        
        # Create full output path
        output_path = self.pbit_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render template
        content = self.render_template(mapping['template'], context)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(content)
            
        return output_path
