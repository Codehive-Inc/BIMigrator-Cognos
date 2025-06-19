
__version__ = "0.1.0"

# Export the main classes and functions to make them available at the package level
# from bimigrator.main import (
#     load_config,
#     migrate_to_tmdl,
#     main
# )

# __all__ = [
#     '__version__',
#     'main',
#     'load_config',
#     'migrate_to_tmdl'
# ]

from cognos_migrator.module_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    post_process_module_with_explicit_session
)

__all__ = [
    '__version__',
    'test_cognos_connection',
    'migrate_module_with_explicit_session',
    'post_process_module_with_explicit_session'
]