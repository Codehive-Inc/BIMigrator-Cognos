"""
Migration Quality Dashboard Package

This package provides web-based dashboards for monitoring migration quality,
validation success rates, and performance metrics.
"""

from .quality_dashboard import QualityDashboard, MetricsDatabase, create_standalone_dashboard

__all__ = [
    'QualityDashboard',
    'MetricsDatabase', 
    'create_standalone_dashboard'
]