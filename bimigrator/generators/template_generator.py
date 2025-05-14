"""Generator for creating Power BI TMDL files."""
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base_template_generator import BaseTemplateGenerator
from .database_template_generator import DatabaseTemplateGenerator
from .model_template_generator import ModelTemplateGenerator


class TemplateGenerator(BaseTemplateGenerator):
    """Main template generator that coordinates specific generators."""

    def __init__(self, config_path: str, input_path: Optional[str] = None):
        """Initialize template generator.
        
        Args:
            config_path: Path to YAML configuration file
            input_path: Optional path to input file for output subdirectory
        """
        super().__init__(config_path, input_path)
        self.database_generator = DatabaseTemplateGenerator(config_path, input_path)
        self.model_generator = ModelTemplateGenerator(config_path, input_path)

    def generate_all(self, config_data: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, List[Path]]:
        """Generate all TMDL files.
        
        Args:
            config_data: Configuration data from parsers
            output_dir: Optional output directory override
            
        Returns:
            Dict mapping component types to lists of generated file paths
        """
        generated_files = defaultdict(list)

        # Generate database TMDL
        if 'PowerBiDatabase' in config_data:
            path = self.database_generator.generate_database_tmdl(
                config_data['PowerBiDatabase'],
                output_dir
            )
            generated_files['database'].append(path)

        # Generate model TMDL and table TMDLs
        if 'PowerBiModel' in config_data:
            paths = self.model_generator.generate_model_tmdl(
                config_data['PowerBiModel'],
                output_dir
            )
            generated_files['model'].append(paths)

            # Add table paths
            for table in config_data['PowerBiModel'].get('tables', []):
                table_path = self.model_generator.generate_table_tmdl(table)
                generated_files['tables'].append(table_path)

        return dict(generated_files)

    def _get_template(self, template_name: str):
        """Get a compiled template, using cache if available."""
        if template_name not in self._template_cache:
            template_path = self.template_dir / template_name
            with open(template_path, 'r') as f:
                source = f.read()
            self._template_cache[template_name] = self.compiler.compile(source)
        return self._template_cache[template_name]

    def _resolve_output_path(self, output_template: str, context: Dict[str, Any],
                             base_dir: Optional[str] = None) -> Path:
        """Resolve output path using context variables."""
        # Render the output path template
        path_template = self.compiler.compile(output_template)
        relative_path = path_template(context)

        # Start with base directory if provided
        base = Path(base_dir) if base_dir else Path('')

        # Add input name subdirectory if available
        if self.input_name:
            base = base / self.input_name

        # Add pbit subdirectory for TMDL files
        if relative_path.endswith('.tmdl'):
            base = base / 'pbit'

        return base / relative_path


def generate_project_files(
        config_path: str,
        config_data: Dict[str, Any],
        input_path: Optional[str] = None,
        output_dir: Optional[str] = None
) -> Dict[str, List[str]]:
    """Generate all project files using templates.
    
    Args:
        config_path: Path to YAML configuration file
        config_data: Complete configuration data
        input_path: Optional input file path
        output_dir: Optional output directory
        
    Returns:
        Dictionary mapping template types to generated file paths
    """
    generator = TemplateGenerator(config_path, input_path)
    output_path = Path(output_dir) if output_dir else None

    # Generate all files using coordinated generators
    generated_files = generator.generate_all(config_data, output_path)

    # Convert Path objects to strings for return value
    return {k: [str(p) for p in v] for k, v in generated_files.items()}


def main():
    """Example usage of template generator."""
    import argparse
    import yaml

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Path to YAML config file')
    parser.add_argument('--input', required=True, help='Path to input file')
    parser.add_argument('--output', help='Output directory')

    args = parser.parse_args()

    # Load configuration data
    with open(args.config, 'r') as f:
        config_data = yaml.safe_load(f)

    # Generate files
    files = generate_project_files(
        args.config,
        config_data,
        args.input,
        args.output
    )

    print('Generated files:')
    for template_type, paths in files.items():
        print(f'\n{template_type}:')
        for path in paths:
            print(f'  - {path}')


if __name__ == '__main__':

    import yaml
    import json
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from bimigrator.parsers import parse_workbook

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
