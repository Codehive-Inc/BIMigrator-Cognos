
__version__ = "0.1.0"

# Export the main classes and functions to make them available at the package level
from bimigrator.main import (
    load_config,
    migrate_to_tmdl,
    main
)

__all__ = [
    '__version__',
    'main',
    'load_config',
    'migrate_to_tmdl'
]
