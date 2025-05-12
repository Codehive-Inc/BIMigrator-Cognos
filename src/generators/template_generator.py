"""Generator for rendering templates and creating Power BI TMDL files."""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import yaml
from pybars import Compiler
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TemplateMapping:
    """Represents a template mapping configuration."""
    template: str
    output: str
    config: str
    dataclass: str
    multiple: bool = False
    name_from: Optional[str] = None

class TemplateGenerator:
    """Handles template rendering and file generation."""
    
    def __init__(self, config_path: str):
        """Initialize with configuration file path."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.template_dir = Path(self.config['Templates']['base_dir'])
        self.intermediate_dir = Path(self.config.get('Output', {}).get('intermediate_dir', 'intermediate'))
        self.validate_intermediate = self.config.get('Output', {}).get('validate_intermediate', True)
        self.mappings = self._load_template_mappings()
        self.compiler = Compiler()
        self._template_cache = {}
    
    def _load_template_mappings(self) -> Dict[str, TemplateMapping]:
        """Load template mappings from configuration."""
        mappings = {}
        for key, mapping in self.config['Templates']['mappings'].items():
            mappings[key] = TemplateMapping(**mapping)
        return mappings
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context."""
        template = self._get_template(template_name)
        return template(context)
    
    def generate_files(
        self,
        config_data: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Generate all files based on template mappings and configuration.
        
        Args:
            config_data: Complete configuration data for all templates
            output_dir: Optional base output directory
        
        Returns:
            Dictionary mapping template types to lists of generated file paths
        """
        generated_files = defaultdict(list)
        
        # Create intermediate directory if needed
        if output_dir:
            intermediate_dir = Path(output_dir) / self.intermediate_dir
        else:
            intermediate_dir = self.intermediate_dir
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        for mapping_key, mapping in self.mappings.items():
            # Get the configuration data for this template
            config_key = mapping.config
            context = self._get_context_for_template(config_key, config_data)
            
            if context is not None:
                # Save intermediate JSON
                intermediate_file = intermediate_dir / f"{mapping_key}.json"
                with open(intermediate_file, 'w') as f:
                    if hasattr(context, '__dict__'):
                        json.dump(context.__dict__, f, indent=2)
                    else:
                        json.dump(context, f, indent=2)
                
                # Validate if required
                if self.validate_intermediate:
                    self._validate_intermediate(mapping_key, context)
                
                # Generate files based on the mapping type
                if mapping.multiple:
                    if not isinstance(context, list):
                        context = [context]
                    
                    for item in context:
                        paths = self._generate_single_file(mapping, item, output_dir)
                        generated_files[mapping_key].extend(paths)
                else:
                    paths = self._generate_single_file(mapping, context, output_dir)
                    generated_files[mapping_key].extend(paths)
        
        return dict(generated_files)
    
    def _validate_intermediate(self, mapping_key: str, context: Any) -> None:
        """Validate intermediate data against expected schema.
        
        Args:
            mapping_key: Key of the template mapping
            context: Data to validate
        
        Raises:
            ValueError: If validation fails
        """
        mapping = self.mappings[mapping_key]
        
        # For now, just check if required fields are present
        if hasattr(context, '__dict__'):
            data = context.__dict__
        else:
            data = context
        
        # Basic validation - ensure all required fields are present and non-None
        if mapping.dataclass in globals():
            dataclass = globals()[mapping.dataclass]
            required_fields = {
                f.name for f in dataclass.__dataclass_fields__.values()
                if f.default == f.default_factory == None
            }
            
            missing = required_fields - set(data.keys())
            if missing:
                raise ValueError(
                    f"Missing required fields for {mapping_key}: {missing}")
    
    def _generate_single_file(
        self,
        mapping: TemplateMapping,
        context: Dict[str, Any],
        base_output_dir: Optional[str] = None
    ) -> List[str]:
        """Generate a single file from a template mapping."""
        if mapping.name_from and mapping.name_from not in context:
            raise ValueError(f"Required name field {mapping.name_from} not found in context")
        
        output_path = self._resolve_output_path(mapping.output, context, base_output_dir)
        self._write_file(mapping.template, output_path, context)
        return [str(output_path)]
    
    def _get_context_for_template(
        self,
        config_key: str,
        config_data: Dict[str, Any]
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract context data for a template from the configuration."""
        # Handle nested keys (e.g., 'model.tables')
        keys = config_key.split('.')
        current = config_data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None
    
    def _write_file(
        self,
        template_name: str,
        output_path: Path,
        context: Dict[str, Any]
    ) -> None:
        """Write rendered template to file."""
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render template
        content = self.render_template(template_name, context)
        
        # Handle different file types
        if output_path.suffix == '.json':
            # Format JSON files
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                # If JSON parsing fails, write as is (might be a template with variables)
                pass
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(content)
    
    def _get_template(self, template_name: str):
        """Get a compiled template, using cache if available."""
        if template_name not in self._template_cache:
            template_path = self.template_dir / template_name
            with open(template_path, 'r') as f:
                source = f.read()
            self._template_cache[template_name] = self.compiler.compile(source)
        return self._template_cache[template_name]

    def _resolve_output_path(self, output_template: str, context: Dict[str, Any], base_dir: Optional[str] = None) -> Path:
        """Resolve output path using context variables."""
        # Render the output path template
        path_template = self.compiler.compile(output_template)
        relative_path = path_template(context)
        
        # Combine with base directory if provided
        if base_dir:
            return Path(base_dir) / relative_path
        return Path(relative_path)
    
    def _get_template(self, template_name: str):
        """Get a compiled template, using cache if available."""
        if template_name not in self._template_cache:
            template_path = self.template_dir / template_name
            with open(template_path, 'r') as f:
                source = f.read()
            self._template_cache[template_name] = self.compiler.compile(source)
        return self._template_cache[template_name]


def generate_project_files(
    config_path: str,
    config_data: Dict[str, Any],
    output_dir: Optional[str] = None
) -> Dict[str, List[str]]:
    """Generate all project files using templates.
    
    Args:
        config_path: Path to the YAML configuration file
        config_data: Complete configuration data for all templates
        output_dir: Optional base output directory
    
    Returns:
        Dictionary mapping template types to lists of generated file paths
    """
    generator = TemplateGenerator(config_path)
    return generator.generate_files(config_data, output_dir)


def main():
    """Example usage of the template generator."""
    import argparse
    import json
    import yaml
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.parsers import parse_workbook
    
    parser = argparse.ArgumentParser(description='Generate Power BI TMDL files from templates')
    parser.add_argument('--config', required=True, help='Path to YAML configuration file')
    parser.add_argument('--input', required=True, help='Path to input file (.twb, .json, or .yaml)')
    parser.add_argument('--output', help='Output directory')
    
    args = parser.parse_args()
    
    # Load YAML config
    with open(args.config, 'r') as f:
        yaml_config = yaml.safe_load(f)

    # Load input data based on file type
    input_path = args.input
    if input_path.endswith('.twb'):
        config_data = parse_workbook(input_path, yaml_config)
    else:
        # Load JSON/YAML data
        with open(input_path, 'r') as f:
            if input_path.endswith('.json'):
                config_data = json.load(f)
            else:
                config_data = yaml.safe_load(f)
    
    # Generate files
    generated = generate_project_files(
        config_path=args.config,
        config_data=config_data,
        output_dir=args.output
    )
    
    # Print summary
    print('\nGenerated files:\n')
    for template_type, files in generated.items():
        print(f'{template_type}:')
        for file in files:
            print(f'  - {file}')


if __name__ == '__main__':
    main()
