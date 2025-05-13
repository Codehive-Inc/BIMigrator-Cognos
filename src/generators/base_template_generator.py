"""Base class for template generators."""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import yaml
from pybars import Compiler
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
    
    def __init__(self, config_path: str, input_path: Optional[str] = None):
        """Initialize base template generator.
        
        Args:
            config_path: Path to YAML configuration file
            input_path: Optional path to input file for output subdirectory
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.template_dir = Path(self.config['Templates']['base_dir'])
        self.intermediate_dir = Path(self.config.get('Output', {}).get('intermediate_dir', 'extracted'))
        self.validate_intermediate = self.config.get('Output', {}).get('validate_intermediate', True)
        self.mappings = self._load_template_mappings()
        self.compiler = Compiler()
        self._template_cache = {}
        self.input_name = Path(input_path).stem if input_path else None
    
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
    
    def _get_output_path(self, template_type: str, name: Optional[str] = None) -> Path:
        """Get output path for a template type."""
        mapping = self.mappings[template_type]
        output_path = mapping.output
        
        if name and '{{name}}' in output_path:
            output_path = output_path.replace('{{name}}', name)
        elif name and '{{id}}' in output_path:
            output_path = output_path.replace('{{id}}', name)
            
        return Path(output_path)
    
    def generate_file(self, template_type: str, context: Dict[str, Any], name: Optional[str] = None) -> Path:
        """Generate a file from a template.
        
        Args:
            template_type: Type of template to use
            context: Context data for template
            name: Optional name for output file
            
        Returns:
            Path to generated file
        """
        mapping = self.mappings[template_type]
        output_path = self._get_output_path(template_type, name)
        
        # Ensure output directory exists
        self._ensure_dir(output_path.parent)
        
        # Render template and write to file
        content = self.render_template(mapping.template, context)
        with open(output_path, 'w') as f:
            f.write(content)
            
        return output_path
