"""
Cognos to BI Migrator
A modular tool for migrating Cognos Analytics reports to Power BI format
"""

__version__ = "1.0.0"
__author__ = "Cognos Migration Team"

from .client import CognosClient
from .migrator import CognosToPowerBIMigrator
from .models import *

__all__ = [
    "CognosClient",
    "CognosToPowerBIMigrator",
]
