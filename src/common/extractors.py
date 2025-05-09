from xml.etree import ElementTree as Et


def extract_datasource_columns(datasource: Et.Element):
    # Extract columns/fields
    columns = []
    for col in datasource.findall('.//column'):
        col_info = {
            "name": col.get('name'),
            "datatype": col.get('datatype'),
            "role": col.get('role'),
            "type": col.get('type')
        }
        columns.append(col_info)
    return columns


def extract_datasource_connections(datasource: Et.Element):
    connection = datasource.find('connection')
    connection_data = {
        'class': connection.get('class'),
    }
    named_connections = connection.findall('.//named-connection')
    named_connections_data = []
    for named_connection in named_connections:
        connection = named_connection.find('.//connection')
        named_connection_data = {
            'caption': named_connection.get('caption'),
            'name': named_connection.get('name'),
            'class': connection.get('class'),
            'cleaning': connection.get('cleaning'),
            'compat': connection.get('compat'),
            'data_refresh_time': connection.get('dataRefreshTime'),
            'filename': connection.get('filename'),
            'interpretation_mode': connection.get('interpretationMode'),
            'password': connection.get('password'),
            'server': connection.get('server'),
            'validate': connection.get('validate'),
        }
        named_connections_data.append(named_connection_data)
    connection_data['connections'] = named_connections_data
    return connection_data


def extract_data_sources(root: Et.Element):
    datasources = root.find('datasources')
    datasources_data = []
    for datasource in datasources.findall('.//datasource'):
        datasource_data = {
            'version': datasource.get('version'),
            'name': datasource.get('name'),
            'caption': datasource.get('caption'),
            'inline': datasource.get('inline'),
            'connections': extract_datasource_connections(datasource),
            'columns': extract_datasource_columns(datasource)
        }
        datasources_data.append(datasource_data)
    return datasources_data
