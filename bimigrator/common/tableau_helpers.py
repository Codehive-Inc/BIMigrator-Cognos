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
        'source_type': 'm',  # Using lowercase 'm' to comply with PowerBI TMDL format requirements
        'expression': generate_m_code(connection_node, relation_node)
    }

def format_m_code_indentation(m_code: str, base_indent: int = 4) -> str:
    """
    Formats M code with proper indentation for TMDL files.
    Args:
        m_code: The M code to format
        base_indent: Number of spaces for base indentation (default: 4)
    Returns:
        Properly indented M code
    """
    if not m_code:
        return m_code

    # Split into lines
    lines = m_code.split('\n')
    
    # Use tabs for indentation to match PowerBI's TMDL format
    tab = '\t'
    
    # Process each line
    formatted_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # First line (let) gets indented with 1 tabs
        if i == 0 and stripped.startswith('let'):
            formatted_lines.append(f"{tab * 1}{stripped}")
        # Last line (in) gets 4 tabs
        elif stripped.startswith('in'):
            formatted_lines.append(f"{tab * 4}{stripped}")
        # All other lines get 5 tabs
        else:
            formatted_lines.append(f"{tab * 5}{stripped}")
    
    return '\n'.join(formatted_lines)

def generate_excel_m_code(filename: str, sheet_name: str) -> str:
    """
    Generates M code for Excel connections using a standardized template.
    
    Args:
        filename: Path to the Excel file
        sheet_name: Name of the Excel sheet
    
    Returns:
        Formatted M code for the Excel connection
    """
    # Create a standard Excel M query template with Promoted Headers and Changed Type steps
    excel_m_template = (
        "let\n"
        "    Source = Excel.Workbook(File.Contents(\"{filename}\"), null, true),\n"
        "    {sheet}_Sheet = Source{{[Item=\"{sheet}\",Kind=\"Sheet\"]}}[Data],\n"
        "    #\"Promoted Headers\" = Table.PromoteHeaders({sheet}_Sheet, [PromoteAllScalars=true]),\n"
        "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\", {{}})\n"
        "in\n"
        "    #\"Changed Type\""
    )
    
    # Format the template with the connection info
    m_code = excel_m_template.format(
        filename=filename.replace('\\', '/'),
        sheet=sheet_name.replace('$', '')
    )
    
    return format_m_code_indentation(m_code)

def generate_m_code(connection_node: Element, relation_node: Element, config: Dict = None) -> str:
    """
    Generates M code string for a table based on connection and relation information.
    Uses the FastAPI service for LLM-assisted M code generation for non-Excel sources.
    For Excel sources, uses a direct approach with a standardized template.
    
    Args:
        connection_node: XML Element containing connection information
        relation_node: XML Element containing relation information
        config: Configuration dictionary containing PowerBiPartition settings
    
    Returns:
        Generated M code string
    """
    import httpx
    import json
    from typing import Dict, Any
    import os

    # Use configuration if provided, otherwise use defaults
    config = config or {}
    m_code_config = config.get('PowerBiPartition', {}).get('m_code_generation', {})
    
    # Get API settings
    api_config = m_code_config.get('api', {})
    api_base_url = os.getenv('TABLEAU_TO_DAX_API_URL', api_config.get('base_url', 'http://localhost:8000'))
    timeout = api_config.get('timeout_seconds', 30)
    m_code_endpoint = api_config.get('endpoints', {}).get('m_code', '/convert/tableau-to-m-code')

    # Extract connection information based on configuration
    conn_types = m_code_config.get('connection_types', {})
    class_type = connection_node.get('class', '')
    
    # Build connection info based on configuration mapping
    conn_info_mapping = m_code_config.get('connection_info_mapping', {})
    standard_fields = conn_info_mapping.get('standard_fields', {})
    
    conn_info: Dict[str, Any] = {
        'class_type': class_type,
        'server': None,
        'database': None,
        'db_schema': None,
        'table': None,
        'sql_query': None,
        'filename': None,
        'additional_properties': {}
    }
    
    # Handle federated connections
    if class_type == 'federated':
        named_conns = connection_node.findall('.//named-connection')
        for named_conn in named_conns:
            conn = named_conn.find('.//connection')
            if conn is not None:
                # Get connection class (dremio, oracle, etc.)
                conn_class = conn.get('class')
                if conn_class:
                    conn_info['class_type'] = conn_class
                    conn_info['filename'] = conn.get('filename')
                    conn_info['server'] = conn.get('server')
                    conn_info['database'] = conn.get('dbname')
                    conn_info['db_schema'] = conn.get('schema')
                    # Add all attributes as additional properties
                    for key, value in conn.attrib.items():
                        conn_info['additional_properties'][key] = value
                    # Special handling for Excel files
                    if conn_class == 'excel-direct':
                        conn_info['class_type'] = 'excel'
                        conn_info['filename'] = conn.get('filename')
                    break
    
    # Handle SQL queries in relations
    if relation_node.get('type') == 'text':
        sql_query = relation_node.text
        if sql_query:
            conn_info['sql_query'] = sql_query.strip().replace('&#13;', '\n').replace('&apos;', "'")
    elif relation_node.get('type') == 'table':
        # Handle Excel table references
        table_ref = relation_node.get('table', '')
        table_name = relation_node.get('name', '')
        
        # Try to get sheet name from table reference first
        if table_ref and table_ref.startswith('[') and table_ref.endswith('$]'):
            # Extract sheet name from [Sheet1$]
            conn_info['table'] = table_ref[1:-2]  # Remove [ and $]
        # If no table reference but we have a name and it's an Excel connection
        elif table_name and conn_info['class_type'] == 'excel':
            conn_info['table'] = table_name
        else:
            conn_info['table'] = relation_node.get('name')

    # Direct handling for Excel connections - prioritized over API call
    if conn_info['class_type'] == 'excel' and conn_info['filename']:
        excel_filename = conn_info['filename']
        sheet_name = conn_info.get('table', 'Sheet1')
        return generate_excel_m_code(excel_filename, sheet_name)

    # For non-Excel connections, use the API service
    try:
        # Call the FastAPI service if LLM is enabled
        if m_code_config.get('llm', {}).get('enabled', True):
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{api_base_url}{m_code_endpoint}",
                    json=conn_info
                )
                response.raise_for_status()
                result = response.json()
                m_code = result.get('m_code', '')
                
                # Unescape HTML entities based on configuration
                if m_code_config.get('formatting', {}).get('html_unescape', {}).get('enabled', True):
                    entities = m_code_config.get('formatting', {}).get('html_unescape', {}).get('entities', [])
                    for entity_map in entities:
                        for entity, char in entity_map.items():
                            m_code = m_code.replace(entity, char)
                
                return format_m_code_indentation(m_code)
                
    except Exception as e:
        # Handle error based on configuration
        error_config = m_code_config.get('error_handling', {})
        if error_config.get('log_errors', True):
            print(f"Error generating M code: {e}")
            
        # Use fallback strategy from configuration
        fallback_strategy = error_config.get('fallback_strategy', 'template')
        if fallback_strategy == 'template':
            # Check fallback conditions
            for conn_type, conditions in error_config.get('fallback_conditions', {}).items():
                if all(eval(cond) for cond in conditions):
                    template = conn_types.get(conn_type, {}).get('fallback_template', '')
                    if template:
                        # Format SQL query for template
                        if conn_info.get('sql_query'):
                            conn_info['sql_query'] = conn_info['sql_query'].replace('"', '\\"')
                        m_code = template.format(**conn_info)
                        return format_m_code_indentation(m_code)
                        
        elif fallback_strategy == 'error':
            raise Exception(f"Failed to generate M code for {conn_info['class_type']} connection")
            
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