"""Parser for diagram layout."""
import re
import json
import uuid
import logging
from typing import Any, List, Optional

from bimigrator.models.power_bi_diagram_layout import (
    DiagramLayout,
    PowerBiDiagramLayout,
    ScrollPosition,
    Location,
    Size,
    Node
)
from bimigrator.models.tableau_layout import TableauDashboardLayout, TableauLayoutObject
from bimigrator.parsers.base_parser import BaseParser

# Configure logging
logger = logging.getLogger(__name__)


class DiagramLayoutParser(BaseParser):
    """Parser for diagram layout."""

    def _parse_layout_object(self, zone_elem: Optional[Any]) -> Optional[TableauLayoutObject]:
        """Parse a layout object from a zone element.
        
        Args:
            zone_elem: Zone XML element from Tableau workbook
            
        Returns:
            TableauLayoutObject or None if parsing fails
        """
        if zone_elem is None:
            return None
            
        try:
            # Get basic attributes
            object_id = zone_elem.get('id', '')
            object_type = zone_elem.get('type-v2', zone_elem.get('type', ''))
            object_name = zone_elem.get('name', '')
            
            # Map Tableau types to our types
            type_mapping = {
                'layout-basic': 'container',
                'layout-flow': 'container',
                'text': 'text',
                'color': 'legend',
                'dashboard-object': 'dashboard-object',
                'worksheet': 'worksheet',
                'bitmap': 'image',
                'web': 'webPage',
                'filter': 'filter',
                'parameter': 'parameter'
            }
            mapped_type = type_mapping.get(object_type, object_type)
            
            # Get position and size
            x = int(zone_elem.get('x', 0))
            y = int(zone_elem.get('y', 0))
            width = int(zone_elem.get('w', 300))
            height = int(zone_elem.get('h', 200))
            
            # Check if floating
            is_floating = zone_elem.get('mode') == 'floating'
            
            # Create layout object
            layout_obj = TableauLayoutObject(
                object_id=object_id,
                object_type=mapped_type,
                object_name=object_name,
                x=x,
                y=y,
                width=width,
                height=height,
                is_floating=is_floating
            )
            
            # Add type-specific attributes
            if mapped_type == 'worksheet':
                layout_obj.worksheet_ref = object_name
            elif mapped_type == 'container':
                # Handle both layout-basic and layout-flow
                layout_obj.container_type = zone_elem.get('param', '')
                
                # Recursively parse children
                for child_elem in zone_elem.findall('.//zone'):
                    child_obj = self._parse_layout_object(child_elem)
                    if child_obj:
                        layout_obj.children.append(child_obj)
            elif mapped_type == 'legend':
                # Store legend parameters
                layout_obj.legend_params = {
                    'pane_id': zone_elem.get('pane-specification-id', ''),
                    'field': zone_elem.get('param', '')
                }
            elif mapped_type == 'text':
                # Store text content if available
                formatted_text = zone_elem.find('.//formatted-text')
                if formatted_text is not None:
                    layout_obj.text_content = formatted_text.text
            
            # Add any additional Tableau parameters
            params = zone_elem.findall('param')
            if params:
                layout_obj.tableau_params = {p.get('name'): p.get('value') for p in params}
                
            return layout_obj
            
        except Exception as e:
            logger.warning(f"Error parsing layout object: {e}")
            return None

    def _process_zone(self, zone_elem: Optional[Any], parent_x: int = 0, parent_y: int = 0) -> List[TableauLayoutObject]:
        """Process a zone element and its children recursively.
        
        Args:
            zone_elem: Zone XML element
            parent_x: X coordinate of parent zone
            parent_y: Y coordinate of parent zone
            
        Returns:
            List of TableauLayoutObject
        """
        if zone_elem is None:
            return []
            
        layout_objects = []
        layout_obj = self._parse_layout_object(zone_elem)
        
        if layout_obj:
            # Adjust coordinates based on parent position
            layout_obj.x += parent_x
            layout_obj.y += parent_y
            layout_objects.append(layout_obj)
            
            # Process child zones
            for child_zone in zone_elem.findall('./zone'):
                child_objects = self._process_zone(child_zone, layout_obj.x, layout_obj.y)
                layout_objects.extend(child_objects)
                
        return layout_objects

    def extract_diagram_layout(self) -> PowerBiDiagramLayout:
        """Extract diagram layout from Tableau workbook."""
        # Get all dashboards
        dashboards = self.root.findall('.//dashboards/dashboard')
        if not dashboards:
            logger.warning("No dashboards found in workbook")
            return PowerBiDiagramLayout()

        # Process the first dashboard
        dashboard = dashboards[0]
        dashboard_name = dashboard.get('name', 'Dashboard')

        # Extract layout objects recursively
        layout_objects = []
        root_zone = dashboard.find('./zones/zone')
        if root_zone is not None:
            layout_objects = self._process_zone(root_zone)

        # Convert layout objects to nodes
        nodes = []
        for i, layout_obj in enumerate(layout_objects):
            # Skip container zones that are just for layout
            if layout_obj.object_type == 'container' and not layout_obj.object_name:
                continue
                
            node = {
                "location": {"x": layout_obj.x, "y": layout_obj.y},
                "size": {"height": layout_obj.height, "width": layout_obj.width},
                "zIndex": i
            }
            
            # Generate node index based on object type
            if layout_obj.object_type == 'worksheet':
                worksheet_elem = self.root.find(f".//worksheet[@name='{layout_obj.worksheet_ref}']")
                if worksheet_elem is not None:
                    # Get datasource name for the worksheet
                    datasource_name = None
                    for datasource in self.root.findall('.//datasources/datasource'):
                        if datasource.find(f".//worksheet[@name='{layout_obj.worksheet_ref}']"): 
                            datasource_name = datasource.get('caption') or datasource.get('name')
                            break
                    node["nodeIndex"] = f"worksheet:{datasource_name or layout_obj.worksheet_ref}"
                    
                    # Add worksheet-specific properties
                    visual_type = self._get_visual_type(worksheet_elem, layout_obj.worksheet_ref)
                    node["visualType"] = visual_type
                    node["visualConfig"] = self._generate_visual_config(worksheet_elem, visual_type, layout_obj.worksheet_ref)
            elif layout_obj.object_type == 'text':
                node["nodeIndex"] = f"text:{layout_obj.object_id}"
                node["textContent"] = layout_obj.text_content
            elif layout_obj.object_type == 'legend':
                node["nodeIndex"] = f"legend:{layout_obj.object_id}"
                if layout_obj.legend_params:
                    node["legendProperties"] = layout_obj.legend_params
            elif layout_obj.object_type == 'filter':
                node["nodeIndex"] = f"filter:{layout_obj.object_id}"
                if layout_obj.tableau_params:
                    node["filterProperties"] = layout_obj.tableau_params
            elif layout_obj.object_type == 'parameter':
                node["nodeIndex"] = f"parameter:{layout_obj.object_id}"
                if layout_obj.tableau_params:
                    node["parameterProperties"] = layout_obj.tableau_params
            else:
                node["nodeIndex"] = f"{layout_obj.object_type}:{layout_obj.object_id}"
            
            # Generate unique lineage tag
            node["nodeLineageTag"] = str(uuid.uuid4())
            nodes.append(node)

        # Create diagram layout
        diagram = DiagramLayout(
            ordinal=0,
            scroll_position=ScrollPosition(x=0, y=0),
            nodes=nodes,
            name=dashboard_name,
            zoom_value=100,
            pin_key_fields_to_top=False,
            show_extra_header_info=False,
            hide_key_fields_when_collapsed=False,
            tables_locked=False
        )

        return PowerBiDiagramLayout(
            version="1.1.0",
            diagrams=[diagram],
            selected_diagram=dashboard_name,
            default_diagram=dashboard_name
        )

    def _get_visual_type(self, worksheet_elem: Optional[Any], name: str) -> str:
        """Determine the PowerBI visual type based on the Tableau worksheet.
        
        Args:
            worksheet_elem: Tableau worksheet XML element
            name: Worksheet name
            
        Returns:
            PowerBI visual type string
        """
        if worksheet_elem is None:
            return "tableEx"

        # First check name-based mapping
        name_lower = name.lower()
        if 'bar' in name_lower:
            return "barChart"
        elif 'line' in name_lower:
            return "lineChart"
        elif 'pie' in name_lower:
            return "pieChart"
        elif 'list' in name_lower or 'table' in name_lower:
            return "tableEx"
        elif 'scatter' in name_lower:
            return "scatterChart"
        elif 'map' in name_lower:
            return "map"

        try:
            # Check for mark type
            mark_type_elem = worksheet_elem.find(".//mark-type")
            if mark_type_elem is not None:
                mark_type = mark_type_elem.text.lower() if mark_type_elem.text else "automatic"
                
                # Map Tableau mark types to PowerBI visual types
                if mark_type == "bar":
                    return "barChart"
                elif mark_type == "line":
                    return "lineChart"
                elif mark_type == "area":
                    return "areaChart"
                elif mark_type == "circle" or mark_type == "shape":
                    return "scatterChart"
                elif mark_type == "pie":
                    return "pieChart"
                elif mark_type == "text":
                    return "tableEx"
                elif mark_type == "map":
                    return "map"
            
            # Check for specific worksheet types based on structure
            panes_elem = worksheet_elem.find(".//panes")
            if panes_elem is not None:
                # Check if it's a matrix-like structure
                if len(panes_elem.findall(".//pane")) > 1:
                    return "matrix"
            
        except Exception as e:
            logger.warning(f"Error determining visual type: {e}")
        
        return "tableEx"

    def _generate_visual_config(self, worksheet_elem: Optional[Any], visual_type: str, name: str) -> str:
        """Generate visual configuration based on worksheet type.
        
        Args:
            worksheet_elem: Tableau worksheet XML element
            visual_type: PowerBI visual type
            name: Worksheet name
            
        Returns:
            Visual configuration as JSON string
        """
        if worksheet_elem is None:
            return "{}"

        try:
            config = {
                "name": visual_type,
                "title": name,
                "vcObjects": {
                    "title": True,
                    "labels": True,
                    "legend": True
                },
                "dataTransforms": {
                    "sorting": []
                }
            }

            # Add visual-specific configuration
            if visual_type == "barChart":
                config["visualSettings"] = {
                    "legend": {
                        "show": True,
                        "position": "right"
                    },
                    "categoryAxis": {
                        "show": True,
                        "labelRotation": 0
                    },
                    "valueAxis": {
                        "show": True
                    }
                }
            elif visual_type == "lineChart":
                config["visualSettings"] = {
                    "legend": {
                        "show": True,
                        "position": "right"
                    },
                    "lineStyles": {
                        "strokeWidth": 2
                    }
                }
            elif visual_type == "pieChart":
                config["visualSettings"] = {
                    "legend": {
                        "show": True,
                        "position": "right"
                    },
                    "labels": {
                        "show": True,
                        "showValues": True,
                        "showPercent": True
                    }
                }
            elif visual_type == "tableEx":
                config["visualSettings"] = {
                    "grid": {
                        "rowHeaders": True,
                        "columnHeaders": True
                    },
                    "totals": {
                        "rowTotals": True,
                        "columnTotals": True
                    }
                }

            return json.dumps(config)
        except Exception as e:
            logger.warning(f"Error generating visual config: {e}")
            return "{}"

    def _translate_filters(self, worksheet_elem: Optional[Any]) -> str:
        """Translate Tableau filters to PowerBI filters.
        
        Args:
            worksheet_elem: Tableau worksheet XML element
            
        Returns:
            Filters as JSON string
        """
        if worksheet_elem is None:
            return "[]"

        try:
            filters = []
            filter_elems = worksheet_elem.findall(".//filter")

            for filter_elem in filter_elems:
                # Extract filter information
                field = filter_elem.get('field', '')
                filter_type = filter_elem.get('type', '')
                column = filter_elem.get('column', field)

                # Create filter object
                filter_obj = {
                    "name": field,
                    "type": "basic",
                    "target": {
                        "table": "Sheet1 (sample_sales_data)",
                        "column": column
                    }
                }

                # Add filter-specific configuration
                if filter_type == "quantitative":
                    filter_obj["filterType"] = "numeric"
                    filter_obj["format"] = "decimal"
                    
                    # Get min/max values
                    quant_filter = filter_elem.find(".//quantitative-filter")
                    if quant_filter is not None:
                        min_elem = quant_filter.find(".//min")
                        if min_elem is not None:
                            filter_obj["min"] = float(min_elem.text)
                            
                        max_elem = quant_filter.find(".//max")
                        if max_elem is not None:
                            filter_obj["max"] = float(max_elem.text)
                            
                elif filter_type == "categorical":
                    filter_obj["filterType"] = "categorical"
                    filter_obj["selectionMode"] = "multiple"
                    
                    # Get selected values
                    cat_filter = filter_elem.find(".//categorical-filter")
                    if cat_filter is not None:
                        values = []
                        for member in cat_filter.findall(".//member"):
                            value = member.get("value")
                            if value:
                                values.append(value)
                        filter_obj["values"] = values
                        
                elif filter_type == "relative-date":
                    filter_obj["filterType"] = "dateRange"
                    filter_obj["format"] = "date"
                    
                    # Get date range
                    date_filter = filter_elem.find(".//relative-date-filter")
                    if date_filter is not None:
                        period = date_filter.get("period")
                        if period:
                            filter_obj["period"] = period

                filters.append(filter_obj)

            return json.dumps(filters)
        except Exception as e:
            logger.warning(f"Error translating filters: {e}")
            return "[]"
