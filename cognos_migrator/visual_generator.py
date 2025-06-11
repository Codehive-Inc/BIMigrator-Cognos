"""
Visual Container Generator for Power BI
Generates all required JSON files for Power BI visual containers
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .report_parser import CognosVisual, VisualField, VisualType


@dataclass
class PowerBIVisualContainer:
    """Represents a complete Power BI visual container with all files"""
    name: str
    visual_type: VisualType
    position: Dict[str, float]
    config: Dict[str, Any] = field(default_factory=dict)
    query: Dict[str, Any] = field(default_factory=dict)
    data_transforms: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    visual_container: Dict[str, Any] = field(default_factory=dict)


class VisualContainerGenerator:
    """Generates Power BI visual container files from Cognos visuals"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_visual_defaults()
    
    def _init_visual_defaults(self):
        """Initialize default properties for each visual type"""
        self.visual_defaults = {
            VisualType.TABLE: {
                "name": "tableEx",
                "properties": {
                    "totals": {
                        "show": True
                    },
                    "grid": {
                        "outlineColor": "#B3B3B3",
                        "textSize": 8
                    }
                }
            },
            VisualType.COLUMN_CHART: {
                "name": "columnChart",
                "properties": {
                    "legend": {
                        "show": True,
                        "position": "Right"
                    },
                    "dataLabels": {
                        "show": False
                    }
                }
            },
            VisualType.PIE_CHART: {
                "name": "pieChart",
                "properties": {
                    "legend": {
                        "show": True,
                        "position": "Right"
                    },
                    "dataLabels": {
                        "show": True,
                        "labelStyle": "Data value, percent of total"
                    }
                }
            },
            VisualType.SLICER: {
                "name": "slicer",
                "properties": {
                    "selection": {
                        "selectAllCheckboxEnabled": True,
                        "singleSelect": False
                    }
                }
            },
            VisualType.CARD: {
                "name": "card",
                "properties": {
                    "categoryLabels": {
                        "show": True,
                        "color": "#666666"
                    }
                }
            }
        }
    
    def generate_visual_container(self, cognos_visual: CognosVisual, 
                                 index: int,
                                 table_mappings: Dict[str, str]) -> PowerBIVisualContainer:
        """
        Generate a complete Power BI visual container from Cognos visual
        
        Args:
            cognos_visual: The Cognos visual to convert
            index: Visual index on the page
            table_mappings: Mapping of field names to table names
            
        Returns:
            Complete PowerBIVisualContainer with all required files
        """
        try:
            # Create container name
            container_name = f"{index:05d}_{cognos_visual.power_bi_type.value} ({self._generate_id()})"
            
            container = PowerBIVisualContainer(
                name=container_name,
                visual_type=cognos_visual.power_bi_type,
                position=cognos_visual.position
            )
            
            # Generate each component
            container.config = self._generate_config(cognos_visual)
            container.query = self._generate_query(cognos_visual, table_mappings)
            container.data_transforms = self._generate_data_transforms(cognos_visual)
            container.filters = self._generate_filters(cognos_visual)
            container.visual_container = self._generate_visual_container(cognos_visual, container_name)
            
            return container
            
        except Exception as e:
            self.logger.error(f"Failed to generate visual container: {e}")
            raise
    
    def _generate_config(self, visual: CognosVisual) -> Dict[str, Any]:
        """Generate config.json for visual"""
        config = {
            "name": visual.name,
            "layouts": [
                {
                    "id": 0,
                    "position": {
                        "x": visual.position.get('x', 0),
                        "y": visual.position.get('y', 0),
                        "width": visual.position.get('width', 300),
                        "height": visual.position.get('height', 200),
                        "z": 0
                    }
                }
            ],
            "singleVisual": {
                "visualType": visual.power_bi_type.value,
                "projections": self._generate_projections(visual.fields),
                "prototypeQuery": {
                    "Version": 2,
                    "From": self._generate_from_clause(visual.fields),
                    "Select": self._generate_select_clause(visual.fields),
                    "OrderBy": self._generate_orderby_clause(visual.fields)
                }
            }
        }
        
        # Add visual-specific properties
        if visual.power_bi_type in self.visual_defaults:
            config["singleVisual"]["objects"] = self.visual_defaults[visual.power_bi_type]["properties"]
        
        return config
    
    def _generate_query(self, visual: CognosVisual, table_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Generate query.json for visual"""
        query = {
            "Version": 2,
            "From": [],
            "Select": [],
            "OrderBy": []
        }
        
        # Build From clause with table references
        tables_used = set()
        for field in visual.fields:
            table_name = table_mappings.get(field.name, field.source_table)
            if table_name not in tables_used:
                tables_used.add(table_name)
                query["From"].append({
                    "Name": table_name[0].lower(),
                    "Entity": table_name,
                    "Type": 0
                })
        
        # Build Select clause
        for i, field in enumerate(visual.fields):
            table_name = table_mappings.get(field.name, field.source_table)
            table_alias = table_name[0].lower()
            
            select_item = {
                "Column": {
                    "Expression": {
                        "SourceRef": {
                            "Source": table_alias
                        }
                    },
                    "Property": field.name
                },
                "Name": f"{table_name}.{field.name}"
            }
            
            # Add aggregation if specified
            if field.aggregation:
                select_item = {
                    "Aggregation": {
                        "Expression": select_item["Column"],
                        "Function": self._map_aggregation(field.aggregation)
                    },
                    "Name": f"{field.aggregation}({table_name}.{field.name})"
                }
            
            query["Select"].append(select_item)
        
        return query
    
    def _generate_data_transforms(self, visual: CognosVisual) -> Dict[str, Any]:
        """Generate dataTransforms.json for visual"""
        transforms = {
            "projectionOrdering": {
                "Values": [],
                "Category": [],
                "Series": [],
                "Y": [],
                "X": []
            },
            "queryMetadata": {
                "Select": []
            },
            "visualElements": []
        }
        
        # Map fields to projections
        for i, field in enumerate(visual.fields):
            role = self._map_data_role(field.data_role)
            if role in transforms["projectionOrdering"]:
                transforms["projectionOrdering"][role].append(i)
            
            # Add query metadata
            transforms["queryMetadata"]["Select"].append({
                "Restatement": field.name,
                "Type": 1 if field.aggregation else 0
            })
        
        return transforms
    
    def _generate_filters(self, visual: CognosVisual) -> Dict[str, Any]:
        """Generate filters.json for visual"""
        filters = []
        
        # Convert Cognos filters to Power BI format
        for cognos_filter in visual.filters:
            pbi_filter = {
                "name": cognos_filter.get("name", "Filter"),
                "type": "Categorical",
                "filter": {
                    "Version": 2,
                    "From": [{"Name": "t", "Entity": cognos_filter.get("table", "Table")}],
                    "Where": [
                        {
                            "Condition": {
                                "In": {
                                    "Expressions": [
                                        {
                                            "Column": {
                                                "Expression": {"SourceRef": {"Source": "t"}},
                                                "Property": cognos_filter.get("column", "Column")
                                            }
                                        }
                                    ],
                                    "Values": [[{"Literal": {"Value": f"'{v}'"}}] 
                                              for v in cognos_filter.get("values", [])]
                                }
                            }
                        }
                    ]
                }
            }
            filters.append(pbi_filter)
        
        return filters
    
    def _generate_visual_container(self, visual: CognosVisual, container_name: str) -> Dict[str, Any]:
        """Generate visualContainer.json for visual"""
        container = {
            "config": json.dumps({
                "name": container_name,
                "layouts": [{
                    "id": 0,
                    "position": visual.position
                }],
                "singleVisual": {
                    "visualType": visual.power_bi_type.value,
                    "projections": self._generate_projections(visual.fields)
                }
            }),
            "filters": "[]",  # JSON string
            "query": json.dumps({"Version": 2, "From": [], "Select": []}),
            "dataTransforms": json.dumps({"projectionOrdering": {}})
        }
        
        return container
    
    def _generate_projections(self, fields: List[VisualField]) -> Dict[str, List]:
        """Generate projections mapping for visual"""
        projections = {}
        
        for field in fields:
            role = self._map_data_role(field.data_role)
            if role not in projections:
                projections[role] = []
            
            projections[role].append({
                "queryRef": f"Query1.{field.name}",
                "active": True
            })
        
        return projections
    
    def _generate_from_clause(self, fields: List[VisualField]) -> List[Dict]:
        """Generate From clause for query"""
        tables = set()
        from_clause = []
        
        for field in fields:
            table = field.source_table
            if table not in tables:
                tables.add(table)
                from_clause.append({
                    "Name": table[0].lower(),
                    "Entity": table,
                    "Type": 0
                })
        
        return from_clause
    
    def _generate_select_clause(self, fields: List[VisualField]) -> List[Dict]:
        """Generate Select clause for query"""
        select_clause = []
        
        for field in fields:
            table_alias = field.source_table[0].lower()
            select_item = {
                "Column": {
                    "Expression": {
                        "SourceRef": {
                            "Source": table_alias
                        }
                    },
                    "Property": field.name
                },
                "Name": f"{field.source_table}.{field.name}"
            }
            select_clause.append(select_item)
        
        return select_clause
    
    def _generate_orderby_clause(self, fields: List[VisualField]) -> List[Dict]:
        """Generate OrderBy clause for query"""
        # Default: order by first field
        if fields:
            return [{
                "Direction": 1,  # Ascending
                "Expression": {
                    "Column": {
                        "Expression": {
                            "SourceRef": {
                                "Source": fields[0].source_table[0].lower()
                            }
                        },
                        "Property": fields[0].name
                    }
                }
            }]
        return []
    
    def _map_data_role(self, cognos_role: str) -> str:
        """Map Cognos data role to Power BI projection"""
        role_mapping = {
            'axis': 'Category',
            'legend': 'Series',
            'values': 'Values',
            'filters': 'Filters',
            'size': 'Size',
            'color': 'Color',
            'x-axis': 'X',
            'y-axis': 'Y'
        }
        return role_mapping.get(cognos_role, 'Values')
    
    def _map_aggregation(self, cognos_agg: str) -> int:
        """Map Cognos aggregation to Power BI function code"""
        agg_mapping = {
            'sum': 0,      # Sum
            'average': 1,  # Average
            'count': 3,    # Count
            'min': 4,      # Min
            'max': 5,      # Max
            'distinct': 6  # CountDistinct
        }
        return agg_mapping.get(cognos_agg.lower(), 0)
    
    def _generate_id(self) -> str:
        """Generate a short random ID for visual container"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    
    def save_visual_container(self, container: PowerBIVisualContainer, output_dir: Path):
        """Save all visual container files to disk"""
        try:
            # Create visual container directory
            visual_dir = output_dir / container.name
            visual_dir.mkdir(parents=True, exist_ok=True)
            
            # Save each file
            files = {
                'config.json': container.config,
                'query.json': container.query,
                'dataTransforms.json': container.data_transforms,
                'filters.json': container.filters,
                'visualContainer.json': container.visual_container
            }
            
            for filename, content in files.items():
                file_path = visual_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2)
            
            self.logger.info(f"Saved visual container: {container.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save visual container: {e}")
            raise


class VisualMapper:
    """Maps Cognos visual properties to Power BI visual properties"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_property_mappings()
    
    def _init_property_mappings(self):
        """Initialize property mappings between Cognos and Power BI"""
        self.property_mappings = {
            # Cognos property -> Power BI property path
            'title': 'title.text',
            'subtitle': 'subtitle.text',
            'showLegend': 'legend.show',
            'legendPosition': 'legend.position',
            'showDataLabels': 'dataLabels.show',
            'dataLabelFormat': 'dataLabels.labelDisplayUnits',
            'xAxisTitle': 'xAxis.title',
            'yAxisTitle': 'yAxis.title',
            'colorScheme': 'dataColors.colors'
        }
    
    def map_visual_properties(self, cognos_props: Dict[str, Any]) -> Dict[str, Any]:
        """Map Cognos visual properties to Power BI format"""
        pbi_props = {}
        
        for cognos_key, cognos_value in cognos_props.items():
            if cognos_key in self.property_mappings:
                pbi_path = self.property_mappings[cognos_key]
                self._set_nested_property(pbi_props, pbi_path, cognos_value)
        
        return pbi_props
    
    def _set_nested_property(self, obj: Dict, path: str, value: Any):
        """Set a nested property using dot notation"""
        keys = path.split('.')
        current = obj
        
        for i, key in enumerate(keys[:-1]):
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value