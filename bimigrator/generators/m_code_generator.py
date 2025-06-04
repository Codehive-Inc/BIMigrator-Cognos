"""Generator for M code in Power BI TMDL files."""
from typing import Dict, Any, List, Optional
import os
import httpx
from xml.etree.ElementTree import Element


def format_m_code_indentation(m_code: str, base_indent: int = 4) -> str:
    """Format M code with proper indentation for TMDL files.
    
    Args:
        m_code: The M code to format
        base_indent: Number of spaces for base indentation
        
    Returns:
        Properly indented M code
    """
    lines = m_code.split('\n')
    formatted_lines = []
    indent_level = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Decrease indent for closing brackets/braces
        if stripped and any(stripped.startswith(c) for c in [')', '}', ']']):
            indent_level = max(0, indent_level - 1)
            
        # Add line with current indentation
        formatted_lines.append(' ' * (base_indent + indent_level * 4) + stripped)
        
        # Increase indent for opening brackets/braces
        if stripped and any(stripped.endswith(c) for c in ['(', '{', '[']):
            indent_level += 1
            
    return '\n'.join(formatted_lines)


def generate_excel_m_code(
    filename: str,
    sheet_name: str,
    columns: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate M code for Excel connections using a standardized template.
    
    Args:
        filename: Path to the Excel file
        sheet_name: Name of the Excel sheet
        columns: List of column information including name and datatype
        
    Returns:
        Formatted M code for the Excel connection
    """
    # Create type conversion pairs based on column data
    type_conversions = "{}"
    if columns:
        # Map Power BI datatypes to M language types
        type_mapping = {
            "int64": "Int64.Type",
            "double": "type number",
            "string": "type text",
            "datetime": "type datetime",
            "boolean": "type logical",
            "decimal": "type number"
        }
        
        # Build type conversion pairs
        seen_columns = set()  # Track unique columns to avoid duplicates
        conversion_pairs = []
        for col in columns:
            source_name = col.get('source_name')
            # Skip internal Tableau columns and duplicates
            if not source_name or '__tableau_internal_object_id__' in source_name or source_name in seen_columns:
                continue
                
            datatype = col.get('datatype', 'string').lower()
            m_type = type_mapping.get(datatype, 'type text')
            # Format column name with proper quotes
            conversion_pairs.append(f'"{source_name}", {m_type}')
            seen_columns.add(source_name)
            
        if conversion_pairs:
            type_conversions = "{" + ", ".join("{" + pair + "}" for pair in conversion_pairs) + "}"
            
    # Create a standard Excel M query template with Promoted Headers and Changed Type steps
    excel_m_template = (
        "let\n"
        "    Source = Excel.Workbook(File.Contents(\"{filename}\"), null, true),\n"
        "    {sheet}_Sheet = Source{{[Item=\"{sheet}\",Kind=\"Sheet\"]}}[Data],\n"
        "    #\"Promoted Headers\" = Table.PromoteHeaders({sheet}_Sheet, [PromoteAllScalars=true]),\n"
        "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\", {type_conversions})\n"
        "in\n"
        "    #\"Changed Type\""
    )
    
    # Format the template with the connection info
    m_code = excel_m_template.format(
        filename=filename.replace('\\', '/'),
        sheet=sheet_name.replace('$', ''),
        type_conversions=type_conversions
    )
    
    return format_m_code_indentation(m_code)


def generate_m_code(
    connection_node: Element,
    relation_node: Element,
    config: Dict[str, Any]
) -> str:
    """Generate M code string for a table based on connection and relation information.
    Uses the FastAPI service for LLM-assisted M code generation for non-Excel sources.
    For Excel sources, uses a direct approach with a standardized template.
    
    Args:
        connection_node: XML Element containing connection information
        relation_node: XML Element containing relation information
        config: Configuration dictionary containing PowerBiPartition settings
        
    Returns:
        Generated M code string
    """
    # Use configuration if provided, otherwise use defaults
    m_code_config = config.get('PowerBiPartition', {}).get('m_code_generation', {})
    
    # Get API settings
    api_config = m_code_config.get('api', {})
    base_url = os.getenv('DAX_API_URL') or os.getenv('TABLEAU_TO_DAX_API_URL') or api_config.get('base_url', 'http://localhost:8000')
    
    # Ensure the URL has a protocol
    if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
        base_url = 'http://' + base_url
        
    api_base_url = base_url
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
        conn_info['table'] = relation_node.get('name')
        
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
                        
    return ""
