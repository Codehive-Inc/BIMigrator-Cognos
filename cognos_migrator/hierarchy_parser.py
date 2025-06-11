"""
Hierarchy Parser for Cognos to Power BI Migration
Handles dimension hierarchies and drill-down structures
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class HierarchyType(Enum):
    """Types of hierarchies"""
    NATURAL = "natural"      # Date hierarchies (Year -> Quarter -> Month -> Day)
    BALANCED = "balanced"    # Geography (Country -> State -> City)
    UNBALANCED = "unbalanced"  # Organization charts
    PARENT_CHILD = "parent_child"  # Self-referencing hierarchies


@dataclass
class HierarchyLevel:
    """Represents a level in a hierarchy"""
    name: str
    column_name: str
    ordinal: int
    source_column: Optional[str] = None
    name_column: Optional[str] = None
    key_column: Optional[str] = None
    parent_column: Optional[str] = None
    is_hidden: bool = False
    sort_by_column: Optional[str] = None


@dataclass 
class CognosHierarchy:
    """Represents a Cognos dimension hierarchy"""
    name: str
    display_name: str
    table_name: str
    hierarchy_type: HierarchyType
    levels: List[HierarchyLevel] = field(default_factory=list)
    is_hidden: bool = False
    default_member: Optional[str] = None
    all_member_name: Optional[str] = None


class CognosHierarchyParser:
    """Parses Cognos dimension hierarchies and converts to Power BI format"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_hierarchies_from_module(self, module_metadata: Dict) -> List[CognosHierarchy]:
        """Extract hierarchies from module metadata"""
        hierarchies = []
        
        try:
            # Method 1: Parse explicit hierarchy definitions
            if 'hierarchies' in module_metadata:
                for hier_data in module_metadata['hierarchies']:
                    hierarchy = self._parse_explicit_hierarchy(hier_data)
                    if hierarchy:
                        hierarchies.append(hierarchy)
            
            # Method 2: Parse dimension structures
            if 'dimensions' in module_metadata:
                for dim_data in module_metadata['dimensions']:
                    hierarchy = self._parse_dimension_hierarchy(dim_data)
                    if hierarchy:
                        hierarchies.append(hierarchy)
            
            # Method 3: Auto-detect date hierarchies
            date_hierarchies = self._auto_detect_date_hierarchies(module_metadata)
            hierarchies.extend(date_hierarchies)
            
            # Method 4: Auto-detect geographical hierarchies
            geo_hierarchies = self._auto_detect_geographical_hierarchies(module_metadata)
            hierarchies.extend(geo_hierarchies)
            
            self.logger.info(f"Found {len(hierarchies)} hierarchies in module")
            
        except Exception as e:
            self.logger.error(f"Failed to parse hierarchies: {e}")
        
        return hierarchies
    
    def _parse_explicit_hierarchy(self, hier_data: Dict) -> Optional[CognosHierarchy]:
        """Parse explicitly defined hierarchy"""
        try:
            hierarchy = CognosHierarchy(
                name=hier_data.get('name', 'Unknown_Hierarchy'),
                display_name=hier_data.get('displayName', hier_data.get('name', 'Unknown')),
                table_name=hier_data.get('tableName', 'Unknown_Table'),
                hierarchy_type=HierarchyType(hier_data.get('type', 'balanced')),
                is_hidden=hier_data.get('isHidden', False),
                default_member=hier_data.get('defaultMember'),
                all_member_name=hier_data.get('allMemberName')
            )
            
            # Parse levels
            if 'levels' in hier_data:
                for i, level_data in enumerate(hier_data['levels']):
                    level = HierarchyLevel(
                        name=level_data.get('name', f'Level{i+1}'),
                        column_name=level_data.get('columnName', ''),
                        ordinal=level_data.get('ordinal', i),
                        source_column=level_data.get('sourceColumn'),
                        name_column=level_data.get('nameColumn'),
                        key_column=level_data.get('keyColumn'),
                        parent_column=level_data.get('parentColumn'),
                        is_hidden=level_data.get('isHidden', False),
                        sort_by_column=level_data.get('sortByColumn')
                    )
                    hierarchy.levels.append(level)
            
            return hierarchy
            
        except Exception as e:
            self.logger.warning(f"Failed to parse explicit hierarchy: {e}")
            return None
    
    def _parse_dimension_hierarchy(self, dim_data: Dict) -> Optional[CognosHierarchy]:
        """Parse hierarchy from dimension structure"""
        try:
            dim_name = dim_data.get('name', 'Unknown_Dimension')
            
            hierarchy = CognosHierarchy(
                name=f"{dim_name}_Hierarchy",
                display_name=dim_data.get('displayName', dim_name),
                table_name=dim_data.get('tableName', dim_name),
                hierarchy_type=HierarchyType.BALANCED
            )
            
            # Parse levels from dimension attributes
            if 'attributes' in dim_data:
                for i, attr in enumerate(dim_data['attributes']):
                    level = HierarchyLevel(
                        name=attr.get('name', f'Level{i+1}'),
                        column_name=attr.get('columnName', attr.get('name', '')),
                        ordinal=i,
                        source_column=attr.get('sourceColumn')
                    )
                    hierarchy.levels.append(level)
            
            return hierarchy if hierarchy.levels else None
            
        except Exception as e:
            self.logger.warning(f"Failed to parse dimension hierarchy: {e}")
            return None
    
    def _auto_detect_date_hierarchies(self, module_metadata: Dict) -> List[CognosHierarchy]:
        """Auto-detect date hierarchies from date columns"""
        hierarchies = []
        
        # Get all columns from module
        columns = self._extract_all_columns(module_metadata)
        
        # Find date columns
        date_columns = [col for col in columns if self._is_date_column(col)]
        
        for date_col in date_columns:
            hierarchy = self._create_date_hierarchy(date_col, module_metadata)
            if hierarchy:
                hierarchies.append(hierarchy)
        
        return hierarchies
    
    def _auto_detect_geographical_hierarchies(self, module_metadata: Dict) -> List[CognosHierarchy]:
        """Auto-detect geographical hierarchies"""
        hierarchies = []
        
        columns = self._extract_all_columns(module_metadata)
        
        # Common geographical patterns
        geo_patterns = {
            'country': ['country', 'nation', 'ctry'],
            'state': ['state', 'province', 'region', 'st'],
            'city': ['city', 'town', 'municipality'],
            'postal': ['postal', 'zip', 'postcode']
        }
        
        geo_columns = {}
        for col in columns:
            col_lower = col.get('name', '').lower()
            for geo_type, patterns in geo_patterns.items():
                if any(pattern in col_lower for pattern in patterns):
                    geo_columns[geo_type] = col
                    break
        
        # Create geography hierarchy if we have multiple geo levels
        if len(geo_columns) >= 2:
            hierarchy = self._create_geography_hierarchy(geo_columns, module_metadata)
            if hierarchy:
                hierarchies.append(hierarchy)
        
        return hierarchies
    
    def _extract_all_columns(self, module_metadata: Dict) -> List[Dict]:
        """Extract all column information from module metadata"""
        columns = []
        
        # Look in various possible locations
        column_sources = [
            module_metadata.get('columns', []),
            module_metadata.get('queryItems', []),
            module_metadata.get('dataItems', [])
        ]
        
        # Check querySubject structure
        if 'querySubject' in module_metadata:
            for qs in module_metadata['querySubject']:
                if 'item' in qs:
                    for item in qs['item']:
                        if 'queryItem' in item:
                            columns.append(item['queryItem'])
        
        # Add other column sources
        for col_list in column_sources:
            if col_list:
                columns.extend(col_list)
        
        return columns
    
    def _is_date_column(self, column: Dict) -> bool:
        """Check if a column is a date column"""
        col_name = column.get('name', '').lower()
        data_type = column.get('dataType', '').lower()
        
        # Check data type
        if any(dt in data_type for dt in ['date', 'time', 'datetime', 'timestamp']):
            return True
        
        # Check column name patterns
        date_patterns = ['date', 'time', 'created', 'modified', 'start', 'end', 'day', 'month', 'year']
        if any(pattern in col_name for pattern in date_patterns):
            return True
        
        return False
    
    def _create_date_hierarchy(self, date_column: Dict, module_metadata: Dict) -> Optional[CognosHierarchy]:
        """Create a date hierarchy for a date column"""
        try:
            col_name = date_column.get('name', 'Date')
            table_name = self._get_table_name(module_metadata)
            
            hierarchy = CognosHierarchy(
                name=f"{col_name}_Hierarchy",
                display_name=f"{col_name} Hierarchy",
                table_name=table_name,
                hierarchy_type=HierarchyType.NATURAL
            )
            
            # Standard date hierarchy levels
            date_levels = [
                HierarchyLevel(name="Year", column_name=f"{col_name}_Year", ordinal=0),
                HierarchyLevel(name="Quarter", column_name=f"{col_name}_Quarter", ordinal=1),
                HierarchyLevel(name="Month", column_name=f"{col_name}_Month", ordinal=2),
                HierarchyLevel(name="Day", column_name=f"{col_name}_Day", ordinal=3)
            ]
            
            hierarchy.levels = date_levels
            return hierarchy
            
        except Exception as e:
            self.logger.warning(f"Failed to create date hierarchy: {e}")
            return None
    
    def _create_geography_hierarchy(self, geo_columns: Dict, module_metadata: Dict) -> Optional[CognosHierarchy]:
        """Create a geography hierarchy"""
        try:
            table_name = self._get_table_name(module_metadata)
            
            hierarchy = CognosHierarchy(
                name="Geography_Hierarchy",
                display_name="Geography",
                table_name=table_name,
                hierarchy_type=HierarchyType.BALANCED
            )
            
            # Order geographical levels from largest to smallest
            geo_order = ['country', 'state', 'city', 'postal']
            ordinal = 0
            
            for geo_type in geo_order:
                if geo_type in geo_columns:
                    col = geo_columns[geo_type]
                    level = HierarchyLevel(
                        name=geo_type.title(),
                        column_name=col.get('name', ''),
                        ordinal=ordinal,
                        source_column=col.get('name', '')
                    )
                    hierarchy.levels.append(level)
                    ordinal += 1
            
            return hierarchy if hierarchy.levels else None
            
        except Exception as e:
            self.logger.warning(f"Failed to create geography hierarchy: {e}")
            return None
    
    def _get_table_name(self, module_metadata: Dict) -> str:
        """Extract table name from module metadata"""
        return (module_metadata.get('name') or 
                module_metadata.get('defaultName') or 
                'Unknown_Table')
    
    def convert_to_powerbi_hierarchies(self, hierarchies: List[CognosHierarchy]) -> List[Dict]:
        """Convert Cognos hierarchies to Power BI hierarchy definitions"""
        powerbi_hierarchies = []
        
        for hierarchy in hierarchies:
            powerbi_hierarchy = {
                "name": hierarchy.name,
                "displayName": hierarchy.display_name,
                "isHidden": hierarchy.is_hidden,
                "levels": []
            }
            
            for level in hierarchy.levels:
                powerbi_level = {
                    "name": level.name,
                    "column": level.column_name,
                    "ordinal": level.ordinal
                }
                
                if level.sort_by_column:
                    powerbi_level["sortByColumn"] = level.sort_by_column
                
                powerbi_hierarchy["levels"].append(powerbi_level)
            
            powerbi_hierarchies.append(powerbi_hierarchy)
        
        return powerbi_hierarchies
    
    def generate_hierarchy_dax_columns(self, hierarchies: List[CognosHierarchy]) -> List[Dict]:
        """Generate DAX calculated columns for hierarchy levels"""
        dax_columns = []
        
        for hierarchy in hierarchies:
            if hierarchy.hierarchy_type == HierarchyType.NATURAL:
                # Generate DAX for date hierarchy levels
                for level in hierarchy.levels:
                    if 'Year' in level.name:
                        dax_expr = f"YEAR([{hierarchy.name.replace('_Hierarchy', '')}])"
                    elif 'Quarter' in level.name:
                        dax_expr = f"\"Q\" & QUARTER([{hierarchy.name.replace('_Hierarchy', '')}])"
                    elif 'Month' in level.name:
                        dax_expr = f"FORMAT([{hierarchy.name.replace('_Hierarchy', '')}], \"MMM\")"
                    elif 'Day' in level.name:
                        dax_expr = f"DAY([{hierarchy.name.replace('_Hierarchy', '')}])"
                    else:
                        continue
                    
                    dax_column = {
                        "name": level.column_name,
                        "expression": dax_expr,
                        "dataType": "string" if "FORMAT" in dax_expr or "Q" in dax_expr else "int64",
                        "isHidden": level.is_hidden,
                        "summarizeBy": "none"
                    }
                    
                    dax_columns.append(dax_column)
        
        return dax_columns