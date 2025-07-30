"""
Migration strategies for Cognos to Power BI conversion
"""

from .fallback_strategy import FallbackStrategy, MigrationStrategyConfig

__all__ = [
    'FallbackStrategy',
    'MigrationStrategyConfig'
]