"""
Package extractors for Cognos Framework Manager packages.

This package contains extractors for parsing Cognos Framework Manager (FM) package files.
"""

from .package_extractor import PackageExtractor
from .base_package_extractor import BasePackageExtractor
from .package_structure_extractor import PackageStructureExtractor
from .package_query_subject_extractor import PackageQuerySubjectExtractor
from .package_relationship_extractor import PackageRelationshipExtractor
from .package_calculation_extractor import PackageCalculationExtractor
from .package_filter_extractor import PackageFilterExtractor
from .consolidated_package_extractor import ConsolidatedPackageExtractor

__all__ = [
    'PackageExtractor',  # Legacy extractor (for backward compatibility)
    'BasePackageExtractor',
    'PackageStructureExtractor',
    'PackageQuerySubjectExtractor',
    'PackageRelationshipExtractor',
    'PackageCalculationExtractor',
    'PackageFilterExtractor',
    'ConsolidatedPackageExtractor',
]
