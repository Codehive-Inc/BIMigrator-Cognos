"""
Cognos to BI Migrator
A modular tool for migrating Cognos Analytics reports to Power BI format
"""

__version__ = "1.0.0"
__author__ = "Cognos Migration Team"

from .client import CognosClient
from .migrator import CognosToPowerBIMigrator
from .models import *

from .explicit_session_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    migrate_single_report_with_explicit_session,
    post_process_module_with_explicit_session
)

__all__ = [
    '__version__',
	"CognosClient",
    "CognosToPowerBIMigrator",
    'test_cognos_connection',
    'migrate_module_with_explicit_session',
    'migrate_single_report_with_explicit_session',
    'post_process_module_with_explicit_session'
]
