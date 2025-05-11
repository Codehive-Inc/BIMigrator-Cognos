"""Generator for creating Power BI TMDL project structure."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Set
from dataclasses import dataclass

@dataclass
class DirectoryStructure:
    """Represents a directory in the project structure."""
    path: str
    required: bool = True

class ProjectStructureGenerator:
    """Generates the Power BI TMDL project structure based on configuration."""
    
    def __init__(self, config_path: str):
        """Initialize with configuration file path."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load template mappings to determine required directories
        self.template_mappings = self.config['Templates']['mappings']
        self.base_dir = Path(self.config['Templates'].get('output_dir', 'output'))
    
    def create_directory_structure(self) -> Set[Path]:
        """Create the directory structure based on template mappings.
        
        Returns:
            Set of created directory paths
        """
        directories = self._get_required_directories()
        created_dirs = set()
        
        for directory in directories:
            dir_path = self.base_dir / directory.path
            if directory.required or self._should_create_directory(dir_path):
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.add(dir_path)
        
        return created_dirs
    
    def _get_required_directories(self) -> List[DirectoryStructure]:
        """Analyze template mappings to determine required directories."""
        directories = set()
        
        # Add base directories
        directories.add(DirectoryStructure('Model'))
        directories.add(DirectoryStructure('Report'))
        
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
                    directories.add(DirectoryStructure(
                        path=current_path,
                        required=not any(c in part for c in '{}[]()'
                    ))
        
        return sorted(directories, key=lambda d: d.path)
        
    def _should_create_directory(self, dir_path: Path) -> bool:
        """Determine if a directory should be created based on configuration."""
        # Check if any template outputs to this directory or its subdirectories
        dir_str = str(dir_path.relative_to(self.base_dir))
        
        for mapping in self.template_mappings.values():
            output = mapping['output']
            if output.startswith(dir_str + '/') or output == dir_str:
                return True
        
        return False

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

def generate_project_structure(
    output_path: str,
    model_config: Dict[str, Any],
    report_config: Dict[str, Any]
def create_project_structure(
    config_path: str,
    output_dir: Optional[str] = None
) -> Set[Path]:
    """Create the project directory structure based on configuration.
    
    Args:
        config_path: Path to YAML configuration file
        output_dir: Optional output directory (overrides config)
    
    Returns:
        Set of created directory paths
    """
    generator = ProjectStructureGenerator(config_path)
    
    if output_dir:
        generator.base_dir = Path(output_dir)
    
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
