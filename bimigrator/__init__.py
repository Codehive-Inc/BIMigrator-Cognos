"""
BIMigrator - A tool for migrating Tableau workbooks to Power BI TMDL format.

This package provides functionality to convert Tableau workbooks (.twb, .twbx) into
Power BI TMDL format, including data model transformations, calculations, and visualizations.

Source code for BIMigrator package.
"""

# Import all subpackages to make them accessible
# Only import what's necessary to avoid circular imports
from . import common
# The following imports are commented out to avoid circular dependencies
# from . import cim
# from . import converters
# from . import exceptions
# from . import mapping
# from . import parsers
# from . import transformation
# from . import utils
