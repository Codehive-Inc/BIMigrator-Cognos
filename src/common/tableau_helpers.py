import re
from typing import Optional, List, Dict, Any
from xml.etree.ElementTree import Element

def sanitize_identifier(name: str) -> str:
    """
    Sanitizes a Tableau identifier to be compatible with Power BI naming conventions.
    Removes brackets, special characters, and ensures valid Power BI naming.
    """
    # Remove brackets and leading/trailing spaces
    cleaned = name.strip('[]').strip()
    # Replace invalid characters with underscores
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned)
    # Ensure it doesn't start with a number
    if cleaned[0].isdigit():
        cleaned = f"Field_{cleaned}"
    return cleaned

def to_boolean(value: str) -> bool:
    """
    Converts a string value to boolean.
    """
    return value.lower() in ('true', '1', 'yes', 'on')

def map_tableau_format(format_code: str) -> str:
    """
    Maps Tableau format codes to Power BI format strings.
    """
    format_mappings = {
        'n0': '0',
        'n1': '0.0',
        'n2': '0.00',
        'p0': '0%',
        'p1': '0.0%',
        'c0': '$#,##0',
        'c2': '$#,##0.00',
        'd': 'Short Date',
        'D': 'Long Date',
    }
    return format_mappings.get(format_code, '')

def determine_summarize_by(role: str, datatype: str) -> str:
    """
    Determines the summarization method based on the field's role and datatype.
    """
    if role == 'measure' and datatype in ('integer', 'real'):
        return 'sum'
    elif role == 'dimension':
        return 'none'
    return 'none'

def extract_sort_column(sort_spec_node: Element) -> Optional[str]:
    """
    Extracts the sort column name from a sort specification node.
    """
    if sort_spec_node is None:
        return None
    sort_field = sort_spec_node.get('field')
    return sanitize_identifier(sort_field) if sort_field else None

def parse_semantic_role(role_string: str) -> Optional[str]:
    """
    Parses a semantic role string (e.g., '[Geo].[City]') into a Power BI data category.
    """
    if not role_string:
        return None
    
    role_mappings = {
        '[Geo].[City]': 'City',
        '[Geo].[Country/Region]': 'Country',
        '[Geo].[State/Province]': 'StateOrProvince',
        '[Geo].[Latitude]': 'Latitude',
        '[Geo].[Longitude]': 'Longitude',
        '[Geo].[PostalCode]': 'PostalCode',
        '[Url].[Url]': 'WebUrl'
    }
    return role_mappings.get(role_string)

def derive_summarization_set_by(summarize_by_value: str) -> str:
    """
    Derives the SummarizationSetBy property based on the summarize_by value.
    """
    if summarize_by_value == 'none':
        return 'Automatic'
    return 'User'

def derive_pbi_format_hint(format_string: str, global_locale: str) -> str:
    """
    Derives Power BI format hint based on format string and locale.
    """
    if not format_string:
        return ''
    # Add locale-specific formatting if needed
    return format_string

def get_join_table_name(join_relation_node: Element, side: str) -> Optional[str]:
    """
    Gets the table name from a join relation node for the specified side ('from' or 'to').
    """
    if join_relation_node is None or side not in ('from', 'to'):
        return None
    
    table_ref = join_relation_node.find(f'./{side}')
    if table_ref is not None:
        return sanitize_identifier(table_ref.get('table', ''))
    return None

def get_join_column_name(join_relation_node: Element, side: str) -> Optional[str]:
    """
    Gets the column name from a join relation node for the specified side ('from' or 'to').
    """
    if join_relation_node is None or side not in ('from', 'to'):
        return None
    
    column_ref = join_relation_node.find(f'./{side}')
    if column_ref is not None:
        return sanitize_identifier(column_ref.get('field', ''))
    return None

def infer_cardinality(join_info: Dict[str, Any]) -> str:
    """
    Infers the cardinality of a relationship based on join information.
    """
    # Default to many-to-one if we can't determine
    return 'manyToOne'

def find_hierarchy_levels(hierarchy_name: str, all_columns: List[Element]) -> List[Dict[str, str]]:
    """
    Finds all columns that belong to a specific hierarchy and orders them correctly.
    """
    hierarchy_columns = []
    for column in all_columns:
        if column.get('hierarchy') == hierarchy_name:
            level_name = column.get('name', '')
            hierarchy_columns.append({
                'name': sanitize_identifier(level_name),
                'column': sanitize_identifier(level_name)
            })
    return sorted(hierarchy_columns, key=lambda x: x['name'])

def generate_m_partition(connection_node: Element, relation_node: Element) -> Dict[str, Any]:
    """
    Generates a Power BI partition object based on connection and relation information.
    """
    name = relation_node.get('name', '')
    return {
        'name': sanitize_identifier(name),
        'source': 'm',
        'expression': generate_m_code(connection_node, relation_node)
    }

def generate_m_code(connection_node: Element, relation_node: Element) -> str:
    """
    Generates M code string for a table based on connection and relation information.
    """
    conn_class = connection_node.get('class', '')
    if conn_class == 'sqlserver':
        server = connection_node.get('server', '')
        database = connection_node.get('dbname', '')
        schema = connection_node.get('schema', 'dbo')
        table = relation_node.get('name', '')
        return f'let\n    Source = Sql.Database("{server}", "{database}"),\n    {schema}_{table} = Source{{[Schema="{schema}",Item="{table}"]}}\nin\n    {schema}_{table}'
    return ''

def determine_viz_type(worksheet_node: Element) -> str:
    """
    Determines the visualization type from a Tableau worksheet node.
    """
    viz_mappings = {
        'text-table': 'table',
        'discrete-bar': 'clusteredBarChart',
        'continuous-line': 'lineChart',
        'pie': 'pieChart',
        'map': 'map'
    }
    
    mark_type = worksheet_node.find('.//mark-type')
    if mark_type is not None:
        return viz_mappings.get(mark_type.text, 'table')
    return 'table'

def map_visual_shelves(worksheet_node: Element, pbi_viz_type: str) -> List[Dict[str, str]]:
    """
    Maps Tableau visual shelves to Power BI visual field mappings.
    """
    mappings = []
    shelf_mappings = {
        'rows': 'Values',
        'cols': 'Category',
        'color': 'Legend',
        'size': 'Size',
        'tooltip': 'Tooltips'
    }
    
    for shelf, pbi_role in shelf_mappings.items():
        shelf_node = worksheet_node.find(f'.//shelf[@name="{shelf}"]')
        if shelf_node is not None:
            field = shelf_node.get('field')
            if field:
                mappings.append({
                    'tableau_shelf': shelf,
                    'pbi_role': pbi_role,
                    'field': sanitize_identifier(field)
                })
    
    return mappings