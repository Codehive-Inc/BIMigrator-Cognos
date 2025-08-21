"""
Cognos Report Specification Parser
Extracts report structure, visualizations, and layout from Cognos report specifications
"""

import json
import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class VisualType(Enum):
    """Power BI visual types"""
    TABLE = "tableEx"
    MATRIX = "matrix"
    COLUMN_CHART = "columnChart"
    BAR_CHART = "barChart"
    LINE_CHART = "lineChart"
    PIE_CHART = "pieChart"
    DONUT_CHART = "donutChart"
    SCATTER_CHART = "scatterChart"
    MAP = "map"
    CARD = "card"
    MULTI_ROW_CARD = "multiRowCard"
    SLICER = "slicer"
    TEXTBOX = "textbox"
    IMAGE = "image"
    GAUGE = "gauge"
    KPI = "kpi"


@dataclass
class VisualField:
    """Represents a field used in a visual"""
    name: str
    source_table: str
    data_role: str  # axis, legend, values, etc.
    aggregation: Optional[str] = None
    format_string: Optional[str] = None


@dataclass
class CognosVisual:
    """Represents a Cognos report visual"""
    name: str
    cognos_type: str
    power_bi_type: VisualType
    position: Dict[str, float]  # x, y, width, height
    fields: List[VisualField] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    filters: List[Dict] = field(default_factory=list)


@dataclass
class ReportPage:
    """Represents a report page with visuals"""
    name: str
    display_name: str
    width: float = 1280
    height: float = 720
    visuals: List[CognosVisual] = field(default_factory=list)
    filters: List[Dict] = field(default_factory=list)
    header: Optional[str] = None


@dataclass
class CognosReportStructure:
    """Complete Cognos report structure"""
    name: str
    report_id: str
    pages: List[ReportPage] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    parameters: List[Dict] = field(default_factory=list)
    themes: Dict[str, Any] = field(default_factory=dict)


class CognosReportSpecificationParser:
    """Parses Cognos report specifications and converts to Power BI structure"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_visual_mappings()
    
    def _load_visual_mappings(self):
        """Load mappings from Cognos visuals to Power BI visuals"""
        self.visual_mappings = {
            # Cognos Object Type -> Power BI Visual Type
            'list': VisualType.TABLE,
            'table': VisualType.TABLE,
            'crosstab': VisualType.MATRIX,
            'chart': VisualType.COLUMN_CHART,  # Default, refined by chart type
            'columnChart': VisualType.COLUMN_CHART,
            'barChart': VisualType.BAR_CHART,
            'lineChart': VisualType.LINE_CHART,
            'pieChart': VisualType.PIE_CHART,
            'scatterChart': VisualType.SCATTER_CHART,
            'text': VisualType.TEXTBOX,
            'textItem': VisualType.TEXTBOX,
            'image': VisualType.IMAGE,
            'map': VisualType.MAP,
            'gauge': VisualType.GAUGE,
            'prompt': VisualType.SLICER,
            'conditionalBlock': VisualType.CARD
        }
    
    def parse_report_specification(self, report_spec: str, report_metadata: Dict) -> CognosReportStructure:
        """
        Parse Cognos report specification
        
        Args:
            report_spec: Report specification (XML or JSON)
            report_metadata: Report metadata from API
            
        Returns:
            Parsed report structure
        """
        try:
            # Determine if specification is XML or JSON
            if report_spec.strip().startswith('<'):
                return self._parse_xml_specification(report_spec, report_metadata)
            elif report_spec.strip().startswith('{'):
                return self._parse_json_specification(report_spec, report_metadata)
            else:
                self.logger.warning("Unknown specification format")
                return self._create_default_structure(report_metadata)
                
        except Exception as e:
            self.logger.error(f"Failed to parse report specification: {e}")
            return self._create_default_structure(report_metadata)
    
    def _parse_xml_specification(self, xml_spec: str, metadata: Dict) -> CognosReportStructure:
        """Parse XML-based report specification"""
        try:
            root = ET.fromstring(xml_spec)
            
            report_structure = CognosReportStructure(
                name=metadata.get('defaultName', 'Unknown Report'),
                report_id=metadata.get('id', '')
            )
            
            # Extract pages (layouts in Cognos)
            pages = self._extract_pages_from_xml(root)
            report_structure.pages = pages
            
            # Extract data sources
            data_sources = self._extract_data_sources_from_xml(root)
            report_structure.data_sources = data_sources
            
            # Extract parameters
            parameters = self._extract_parameters_from_xml(root)
            report_structure.parameters = parameters
            
            return report_structure
            
        except ET.ParseError as e:
            self.logger.error(f"XML parse error: {e}")
            return self._create_default_structure(metadata)
    
    def _parse_json_specification(self, json_spec: str, metadata: Dict) -> CognosReportStructure:
        """Parse JSON-based report specification"""
        try:
            spec_data = json.loads(json_spec)
            
            report_structure = CognosReportStructure(
                name=metadata.get('defaultName', 'Unknown Report'),
                report_id=metadata.get('id', '')
            )
            
            # Extract pages from JSON structure
            if 'pages' in spec_data:
                for page_data in spec_data['pages']:
                    page = self._parse_json_page(page_data)
                    report_structure.pages.append(page)
            
            return report_structure
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            return self._create_default_structure(metadata)
    
    def _extract_pages_from_xml(self, root: ET.Element) -> List[ReportPage]:
        """Extract pages from XML specification"""
        pages = []
        
        # Get report name for page naming
        report_name = self._extract_report_name(root)
        
        # Look for page elements within reportPages
        report_pages = root.findall('.//reportPages/page')
        
        if report_pages:
            for i, page_elem in enumerate(report_pages):
                page_name = page_elem.get('name', f'Page{i+1}')
                
                # Create display name using report name + page name convention
                display_name = f"{report_name} - {page_name}" if report_name else page_name
                
                page = ReportPage(
                    name=page_name,
                    display_name=display_name
                )
                
                # Extract page header if present
                page_header = self._extract_page_header(page_elem)
                if page_header:
                    page.header = page_header
                
                # Extract filters for this page
                page_filters = self._extract_page_filters(root, page_elem)
                page.filters = page_filters
                
                # Extract visuals from this page
                visuals = self._extract_visuals_from_xml_layout(page_elem)
                page.visuals = visuals
                
                pages.append(page)
        else:
            # Fallback: look for layout elements
            layouts = root.findall('.//layout') + root.findall('.//page')
        
        for i, layout in enumerate(layouts):
            page_name = layout.get("name", f"Page{i+1}")
            display_name = f"{report_name} - {page_name}" if report_name else page_name
            
            page = ReportPage(
                name=page_name,
                display_name=display_name
            )
            
            # Extract visuals from this layout
            visuals = self._extract_visuals_from_xml_layout(layout)
            page.visuals = visuals
            
            pages.append(page)
        
        # If no layouts found, create a default page
        if not pages:
            display_name = f"{report_name} - Page1" if report_name else "Report Page"
            default_page = ReportPage(name="Page1", display_name=display_name)
            
            # Extract filters from root
            page_filters = self._extract_page_filters(root)
            default_page.filters = page_filters
            
            # Extract all visuals into default page
            all_visuals = self._extract_visuals_from_xml_layout(root)
            default_page.visuals = all_visuals
            
            pages.append(default_page)
        
        return pages
    
    def _extract_report_name(self, root: ET.Element) -> str:
        """Extract report name from XML"""
        # Try to find reportName element
        report_name_elem = root.find('.//reportName')
        if report_name_elem is not None and report_name_elem.text:
            return report_name_elem.text.strip()
        
        # Fallback: look for name attribute on root
        if root.get('name'):
            return root.get('name')
            
        return "Report"
    
    def _extract_page_header(self, page_elem: ET.Element) -> Optional[str]:
        """Extract page header text"""
        page_header = page_elem.find('.//pageHeader')
        if page_header is not None:
            # Look for text content in pageHeader
            text_items = page_header.findall('.//textItem')
            for text_item in text_items:
                static_value = text_item.find('.//staticValue')
                if static_value is not None and static_value.text:
                    return static_value.text.strip()
        return None
    
    def _extract_page_filters(self, root: ET.Element, page_elem: ET.Element = None) -> List[Dict]:
        """Extract filters from detailFilters in queries section"""
        filters = []
        
        # Find detailFilters in queries
        detail_filters = root.findall('.//detailFilters/detailFilter')
        
        for filter_elem in detail_filters:
            filter_expr_elem = filter_elem.find('filterExpression')
            if filter_expr_elem is not None and filter_expr_elem.text:
                filter_expression = filter_expr_elem.text.strip()
                
                # Parse filter expression to extract field and operator
                filter_info = self._parse_filter_expression(filter_expression)
                if filter_info:
                    filters.append(filter_info)
        
        return filters
    
    def _parse_filter_expression(self, expression: str) -> Optional[Dict]:
        """Parse Cognos filter expression into Power BI filter format"""
        import re
        
        # Pattern to match expressions like [SITE_NUMBER]= ?SiteNumber?
        pattern = r'\[([^\]]+)\]\s*([=<>!]+)\s*\?([^?]+)\?'
        match = re.match(pattern, expression)
        
        if match:
            field_name, operator, parameter_name = match.groups()
            
            # Convert Cognos operator to Power BI filter format
            pbi_operator = self._convert_operator_to_powerbi(operator)
            
            filter_info = {
                "target": {
                    "table": None,  # Will be determined later
                    "column": field_name
                },
                "operator": pbi_operator,
                "values": [],  # Empty for parameter-based filters
                "displayName": f"{field_name} filter",
                "type": "ColumnFilter",
                "isParameter": True,
                "parameterName": parameter_name
            }
            
            return filter_info
        
        return None
    
    def _convert_operator_to_powerbi(self, cognos_operator: str) -> str:
        """Convert Cognos filter operators to Power BI equivalents"""
        operator_map = {
            '=': 'In',
            '==': 'In', 
            '!=': 'NotIn',
            '<>': 'NotIn',
            '>': 'GreaterThan',
            '>=': 'GreaterThanOrEqual',
            '<': 'LessThan',
            '<=': 'LessThanOrEqual'
        }
        return operator_map.get(cognos_operator.strip(), 'In')
    
    def _extract_visuals_from_xml_layout(self, layout: ET.Element) -> List[CognosVisual]:
        """Extract visual elements from XML layout"""
        visuals = []
        
        # Common Cognos visual element names
        visual_elements = [
            'list', 'crosstab', 'chart', 'text', 'textItem', 
            'image', 'map', 'gauge', 'table', 'block'
        ]
        
        for visual_type in visual_elements:
            elements = layout.findall(f'.//{visual_type}')
            
            for element in elements:
                visual = self._parse_xml_visual_element(element, visual_type)
                if visual:
                    visuals.append(visual)
        
        return visuals
    
    def _parse_xml_visual_element(self, element: ET.Element, visual_type: str) -> Optional[CognosVisual]:
        """Parse individual visual element from XML"""
        try:
            # Get visual name
            name = element.get('name', f'{visual_type}_{id(element)}')
            
            # Map to Power BI visual type
            power_bi_type = self._map_cognos_to_powerbi_visual(visual_type, element)
            
            # Extract position information
            position = self._extract_position_from_xml(element)
            
            # Extract fields/data items
            fields = self._extract_fields_from_xml(element)
            
            # Extract properties
            properties = self._extract_properties_from_xml(element)
            
            visual = CognosVisual(
                name=name,
                cognos_type=visual_type,
                power_bi_type=power_bi_type,
                position=position,
                fields=fields,
                properties=properties
            )
            
            return visual
            
        except Exception as e:
            self.logger.warning(f"Failed to parse visual element {visual_type}: {e}")
            return None
    
    def _map_cognos_to_powerbi_visual(self, cognos_type: str, element: ET.Element) -> VisualType:
        """Map Cognos visual type to Power BI visual type"""
        # Get base mapping
        base_type = self.visual_mappings.get(cognos_type, VisualType.TABLE)
        
        # Refine chart types based on chart properties
        if cognos_type == 'chart':
            chart_type = element.get('chartType') or element.get('type', '')
            
            chart_mappings = {
                'column': VisualType.COLUMN_CHART,
                'bar': VisualType.BAR_CHART,
                'line': VisualType.LINE_CHART,
                'pie': VisualType.PIE_CHART,
                'scatter': VisualType.SCATTER_CHART,
                'area': VisualType.LINE_CHART,  # Area charts as line charts in Power BI
                'combination': VisualType.COLUMN_CHART  # Default for combination charts
            }
            
            return chart_mappings.get(chart_type.lower(), base_type)
        
        return base_type
    
    def _extract_position_from_xml(self, element: ET.Element) -> Dict[str, float]:
        """Extract position and size information"""
        position = {'x': 0, 'y': 0, 'width': 300, 'height': 200}
        
        # Look for positioning attributes
        if element.get('x'):
            position['x'] = float(element.get('x', 0))
        if element.get('y'):
            position['y'] = float(element.get('y', 0))
        if element.get('width'):
            position['width'] = float(element.get('width', 300))
        if element.get('height'):
            position['height'] = float(element.get('height', 200))
        
        # Look for style information
        style_elem = element.find('.//style')
        if style_elem is not None:
            # Parse style attributes for positioning
            pass
        
        return position
    
    def _extract_fields_from_xml(self, element: ET.Element) -> List[VisualField]:
        """Extract data fields from visual element"""
        fields = []
        
        # Look for data items
        data_items = element.findall('.//dataItem') + element.findall('.//dataItemValue')
        
        for item in data_items:
            field = self._parse_data_item(item)
            if field:
                fields.append(field)
        
        # Look for query items
        query_items = element.findall('.//queryItem')
        for item in query_items:
            field = self._parse_query_item(item)
            if field:
                fields.append(field)
        
        return fields
    
    def _parse_data_item(self, item: ET.Element) -> Optional[VisualField]:
        """Parse a data item into a visual field"""
        try:
            name = item.get('name', '')
            if not name:
                # Try to get from nested elements
                name_elem = item.find('.//name')
                if name_elem is not None:
                    name = name_elem.text or ''
            
            # Determine data role based on parent context
            parent = item.getparent()
            data_role = self._determine_data_role(parent, item)
            
            # Extract aggregation information
            aggregation = item.get('aggregate') or item.get('aggregation')
            
            field = VisualField(
                name=name,
                source_table='Unknown',  # Would need more context to determine
                data_role=data_role,
                aggregation=aggregation
            )
            
            return field
            
        except Exception as e:
            self.logger.warning(f"Failed to parse data item: {e}")
            return None
    
    def _parse_query_item(self, item: ET.Element) -> Optional[VisualField]:
        """Parse a query item into a visual field"""
        try:
            name = item.get('name', '')
            ref = item.get('ref', '')
            
            # Use ref if name is not available
            if not name and ref:
                name = ref.split('.')[-1] if '.' in ref else ref
            
            field = VisualField(
                name=name,
                source_table='Unknown',
                data_role='values'  # Default role
            )
            
            return field
            
        except Exception as e:
            self.logger.warning(f"Failed to parse query item: {e}")
            return None
    
    def _determine_data_role(self, parent: ET.Element, item: ET.Element) -> str:
        """Determine the data role of a field based on context"""
        if parent is None:
            return 'values'
        
        parent_tag = parent.tag.lower()
        
        # Map parent context to data roles
        role_mappings = {
            'rows': 'axis',
            'columns': 'legend', 
            'measures': 'values',
            'filters': 'filters',
            'categories': 'axis',
            'series': 'legend',
            'values': 'values',
            'x-axis': 'axis',
            'y-axis': 'values',
            'color': 'legend',
            'size': 'size'
        }
        
        return role_mappings.get(parent_tag, 'values')
    
    def _extract_properties_from_xml(self, element: ET.Element) -> Dict[str, Any]:
        """Extract visual properties"""
        properties = {}
        
        # Extract style properties
        style_elem = element.find('.//style')
        if style_elem is not None:
            properties['style'] = self._parse_style_element(style_elem)
        
        # Extract other properties
        for attr_name, attr_value in element.attrib.items():
            if attr_name not in ['name', 'x', 'y', 'width', 'height']:
                properties[attr_name] = attr_value
        
        return properties
    
    def _parse_style_element(self, style_elem: ET.Element) -> Dict[str, Any]:
        """Parse style element"""
        style_props = {}
        
        for prop in style_elem:
            style_props[prop.tag] = prop.text or prop.attrib
        
        return style_props
    
    def _extract_data_sources_from_xml(self, root: ET.Element) -> List[str]:
        """Extract data source references from XML"""
        data_sources = []
        
        # Look for query references
        queries = root.findall('.//query')
        for query in queries:
            ds_name = query.get('dataSource') or query.get('datasource')
            if ds_name and ds_name not in data_sources:
                data_sources.append(ds_name)
        
        return data_sources
    
    def _extract_parameters_from_xml(self, root: ET.Element) -> List[Dict]:
        """Extract parameters from XML"""
        parameters = []
        
        # Look for parameter definitions
        params = root.findall('.//parameter') + root.findall('.//prompt')
        
        for param in params:
            param_info = {
                'name': param.get('name', ''),
                'type': param.get('type', 'string'),
                'required': param.get('required', 'false').lower() == 'true'
            }
            parameters.append(param_info)
        
        return parameters
    
    def _parse_json_page(self, page_data: Dict) -> ReportPage:
        """Parse a page from JSON data"""
        page = ReportPage(
            name=page_data.get('name', 'Page1'),
            display_name=page_data.get('displayName', 'Report Page')
        )
        
        # Parse visuals from JSON
        if 'visuals' in page_data:
            for visual_data in page_data['visuals']:
                visual = self._parse_json_visual(visual_data)
                if visual:
                    page.visuals.append(visual)
        
        return page
    
    def _parse_json_visual(self, visual_data: Dict) -> Optional[CognosVisual]:
        """Parse a visual from JSON data"""
        try:
            visual = CognosVisual(
                name=visual_data.get('name', 'Visual'),
                cognos_type=visual_data.get('type', 'unknown'),
                power_bi_type=VisualType.TABLE,  # Default
                position=visual_data.get('position', {}),
                properties=visual_data.get('properties', {})
            )
            
            return visual
            
        except Exception as e:
            self.logger.warning(f"Failed to parse JSON visual: {e}")
            return None
    
    def _create_default_structure(self, metadata: Dict) -> CognosReportStructure:
        """Create a default report structure when parsing fails"""
        return CognosReportStructure(
            name=metadata.get('defaultName', 'Unknown Report'),
            report_id=metadata.get('id', ''),
            pages=[ReportPage(name="Page1", display_name="Report Page")]
        )
    
    def convert_to_powerbi_report(self, cognos_structure: CognosReportStructure) -> Dict[str, Any]:
        """Convert Cognos report structure to Power BI report JSON"""
        power_bi_report = {
            "version": "5.0",
            "dataModelSchema": {
                "name": cognos_structure.name,
                "tables": []
            },
            "sections": []
        }
        
        # Convert pages to sections
        for i, page in enumerate(cognos_structure.pages):
            section = self._convert_page_to_section(page, i)
            power_bi_report["sections"].append(section)
        
        return power_bi_report
    
    def _convert_page_to_section(self, page: ReportPage, index: int) -> Dict[str, Any]:
        """Convert a Cognos page to Power BI section"""
        section = {
            "name": f"{index:03d}_{page.name}",
            "displayName": page.display_name,
            "visualContainers": []
        }
        
        # Convert visuals to visual containers
        for i, visual in enumerate(page.visuals):
            container = self._convert_visual_to_container(visual, i)
            section["visualContainers"].append(container)
        
        return section
    
    def _convert_visual_to_container(self, visual: CognosVisual, index: int) -> Dict[str, Any]:
        """Convert Cognos visual to Power BI visual container"""
        container = {
            "name": f"{index:05d}_{visual.power_bi_type.value}",
            "position": {
                "x": visual.position.get('x', 0),
                "y": visual.position.get('y', 0),
                "width": visual.position.get('width', 300),
                "height": visual.position.get('height', 200)
            },
            "visual": {
                "visualType": visual.power_bi_type.value,
                "projections": self._convert_fields_to_projections(visual.fields),
                "properties": visual.properties
            }
        }
        
        return container
    
    def _convert_fields_to_projections(self, fields: List[VisualField]) -> Dict[str, List]:
        """Convert visual fields to Power BI projections"""
        projections = {
            "Category": [],
            "Values": [],
            "Series": []
        }
        
        for field in fields:
            projection = {
                "queryRef": f"Query1.{field.name}",
                "active": True
            }
            
            # Map data roles to projection categories
            role_mapping = {
                'axis': 'Category',
                'legend': 'Series', 
                'values': 'Values',
                'filters': 'Filters'
            }
            
            category = role_mapping.get(field.data_role, 'Values')
            if category in projections:
                projections[category].append(projection)
        
        return projections