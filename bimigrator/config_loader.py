"""Utility functions for loading configuration files."""
from pathlib import Path
from typing import Any, Dict


def get_config_path(config_file: str) -> Path:
    """
    Get the path to a configuration file.

    This function looks for the config file in the following order:
    1. In the current working directory
    2. In a 'config' subdirectory of the current working directory
    3. In the package's config directory (when installed as a package)

    Args:
        config_file: The name of the config file to find

    Returns:
        Path to the config file

    Raises:
        FileNotFoundError: If the config file cannot be found
    """
    # Try current directory
    current_dir = Path.cwd()
    config_path = current_dir / config_file
    if config_path.exists():
        return config_path

    # Try config subdirectory
    config_dir = current_dir / 'config'
    config_path = config_dir / config_file
    if config_path.exists():
        return config_path

    # Try package config directory (when installed as a package)
    try:
        import importlib.resources as pkg_resources
        from . import config as pkg_config

        if pkg_resources.is_resource(pkg_config.__name__, config_file):
            # For package resources, we need to extract it to a temporary file
            import tempfile

            content = pkg_resources.read_text(pkg_config.__name__, config_file)
            temp_dir = Path(tempfile.gettempdir()) / 'bimigrator_config'
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / config_file
            temp_path.write_text(content)
            return temp_path
    except (ImportError, ModuleNotFoundError, FileNotFoundError):
        pass

    # If we get here, the file wasn't found
    raise FileNotFoundError(
        f"Could not find config file: {config_file}. "
        "Please make sure it exists in the current directory, 'config' subdirectory, "
        "or in the package's config directory."
    )


def load_config_file(config_file: str) -> Dict[str, Any]:
    """
    Load a configuration file.

    Args:
        config_file: The name of the config file to load

    Returns:
        The loaded configuration as a dictionary

    Raises:
        FileNotFoundError: If the config file cannot be found
        yaml.YAMLError: If there's an error parsing the YAML file
    """
    import yaml

    config_path = get_config_path(config_file)
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
