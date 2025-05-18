"""Generator for creating Power BI TMDL project structure."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

import yaml


@dataclass(frozen=True)
class DirectoryStructure:
    """Represents a directory in the project structure."""
    path: str
    required: bool = True


class ProjectStructureGenerator:
    """Generates the Power BI TMDL project structure based on configuration."""

    def __init__(self, config: Dict[str, Any], output_dir: str):
        """Initialize with configuration.
        
        Args:
            config: Configuration dictionary
            output_dir: Base output directory
        """
        self.config = config
        self.template_mappings = self.config['Templates']['mappings']
        self.base_dir = Path(output_dir) / 'pbit'  # TMDL files go in pbit subdirectory
        self.extracted_dir = Path(output_dir) / 'extracted'  # Parser output goes in extracted subdirectory

    def create_directory_structure(self) -> Set[Path]:
        """Create the directory structure based on template mappings.
        
        Returns:
            Set of created directory paths
        """
        directories = self._get_required_directories()
        created_dirs = set()

        # Create all directories under pbit
        for directory in directories:
            dir_path = self.base_dir / directory.path
            if directory.required or self._should_create_directory(dir_path):
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.add(dir_path)

        # Create extracted directory
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        created_dirs.add(self.extracted_dir)

        return created_dirs

    def _get_required_directories(self) -> List[DirectoryStructure]:
        """Analyze template mappings to determine required directories.
        
        Extracts required directories from the output paths in template mappings.
        For example, if a mapping has output 'Model/tables/{{name}}.tmdl',
        this will create directories for 'Model' and 'Model/tables'.
        
        Returns:
            List of DirectoryStructure objects representing required directories
        """
        directories = set()

        # Analyze template mappings
        for mapping in self.template_mappings.values():
            output_path = mapping['output']
            # Extract directory path from output template
            # Handle both static paths and templated paths (e.g., Model/tables/{{name}}.tmdl)
            parts = output_path.split('/')
            current_path = ''

            for part in parts[:-1]:  # Skip filename
                if '{{' not in part:  # Only add static directory paths
                    current_path = str(Path(current_path) / part)
                    # Mark as required if path has no template variables
                    required = not any(c in current_path for c in '{}[]()')
                    directories.add(DirectoryStructure(
                        path=current_path,
                        required=required
                    ))

        return sorted(list(directories), key=lambda d: d.path)

    def _should_create_directory(self, dir_path: Path) -> bool:
        """Determine if a directory should be created based on configuration."""
        # Check if any template outputs to this directory or its subdirectories
        try:
            dir_str = str(dir_path.relative_to(self.base_dir))
        except ValueError:
            # If the path is not relative to base_dir, use full path
            dir_str = str(dir_path)

        for mapping in self.template_mappings.values():
            output = mapping['output']
            # Handle template variables in path
            clean_output = output.split('{{')[0].rstrip('/')
            if clean_output.startswith(dir_str + '/') or clean_output == dir_str:
                return True

        return False


def create_project_structure(config_path: str, input_path: Optional[str] = None, output_dir: Optional[str] = None) -> \
        Set[Path]:
    """Create project directory structure based on configuration.
    
    Args:
        config_path: Path to configuration file
        input_path: Optional path to input file
        output_dir: Optional output directory
    
    Returns:
        Set of created directory paths
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Set output directory and add input file name subdirectory
    if not output_dir:
        output_dir = config['Templates'].get('output_dir', 'output')
    input_name = Path(input_path).stem if input_path else None
    project_dir = str(Path(output_dir) / input_name) if input_name else output_dir

    # Create project structure
    generator = ProjectStructureGenerator(config=config, output_dir=project_dir)
    return generator.create_directory_structure()


def main():
    """Command line interface for project structure generation."""
    import argparse

    parser = argparse.ArgumentParser(description='Create Power BI TMDL project structure')
    parser.add_argument('--config', required=True, help='Path to YAML configuration file')
    parser.add_argument('--output', help='Output directory')

    args = parser.parse_args()

    # Create directory structure
    created_dirs = create_project_structure(
        config_path=args.config,
        output_dir=args.output
    )

    # Print summary
    print("\nCreated directories:")
    for directory in sorted(created_dirs):
        print(f"  - {directory}")


if __name__ == '__main__':
    main()
