from xml.etree import ElementTree as ET

from bimigrator.common.extractors import extract_data_sources
from bimigrator.common.logging import logger


def parse_twb_metadata(xml_content):
    """Parses XML content from a .twb file to extract metadata."""
    metadata = {
        "datasources": [],
        "worksheets": [],
        "dashboards": [],
        "calculations": [],
        "parameters": [],
        "filters": [],
        "actions": []
    }

    try:
        root = ET.fromstring(xml_content)

        # --- Extract Datasources ---
        # for ds in root.findall('.//datasource'):
        #     ds_info = {"name": ds.get('name'), "version": ds.get('version'), "caption": ds.get('caption')}
        #     connection = ds.find('.//connection')
        #     if connection is not None:
        #         ds_info["connection_type"] = connection.get('class')
        #         ds_info["server"] = connection.get('server')
        #         ds_info["dbname"] = connection.get('dbname')
        #         ds_info["authentication"] = connection.get('authentication')
        #
        #         # Extract connection attributes
        #         conn_attrs = {}
        #         for attr_name, attr_value in connection.attrib.items():
        #             conn_attrs[attr_name] = attr_value
        #         ds_info["connection_attributes"] = conn_attrs
        #
        #         # Extract columns/fields
        #         columns = []
        #         for col in ds.findall('.//column'):
        #             col_info = {
        #                 "name": col.get('name'),
        #                 "datatype": col.get('datatype'),
        #                 "role": col.get('role'),
        #                 "type": col.get('type')
        #             }
        #             columns.append(col_info)
        #         ds_info["columns"] = columns
        #
        #     metadata["datasources"].append(ds_info)

        # --- Extract Calculations ---
        metadata['datasources'] = extract_data_sources(root)
        for calc in root.findall('.//calculation'):
            formula = calc.get('formula')
            calc_info = {
                "name": calc.get('name') or calc.get('caption'),
                "formula": formula,
                "datatype": calc.get('datatype'),
                "class": calc.get('class')
            }
            metadata["calculations"].append(calc_info)

        # --- Extract Worksheets ---
        for ws in root.findall('.//worksheet'):
            ws_info = {
                "name": ws.get('name'),
                "fields": []
            }

            # Extract fields used in the worksheet
            for field in ws.findall('.//field'):
                field_info = {
                    "name": field.get('name'),
                    "role": field.get('role')
                }
                ws_info["fields"].append(field_info)

            # Extract style information
            style = ws.find('.//style')
            if style is not None:
                ws_info["style"] = {attr: style.get(attr) for attr in style.attrib}

            metadata["worksheets"].append(ws_info)

        # --- Extract Dashboards ---
        for db in root.findall('.//dashboard'):
            db_info = {
                "name": db.get('name'),
                "worksheets": [],
                "size": {}
            }

            # Get dashboard size
            size = db.find('.//size')
            if size is not None:
                db_info["size"] = {
                    "width": size.get('width'),
                    "height": size.get('height'),
                    "minwidth": size.get('minwidth'),
                    "minheight": size.get('minheight')
                }

            # Get worksheets in dashboard
            for zone in db.findall('.//zone'):
                if zone.get('name'):
                    db_info["worksheets"].append(zone.get('name'))

            metadata["dashboards"].append(db_info)

        # --- Extract Parameters ---
        for param in root.findall('.//parameter'):
            param_info = {
                "name": param.get('name'),
                "datatype": param.get('datatype'),
                "value": param.get('value')
            }

            # Get parameter domain values if available
            domain = param.find('.//domain')
            if domain is not None:
                values = []
                for member in domain.findall('.//member'):
                    value = member.get('value')
                    if value:
                        values.append(value)
                param_info["domain_values"] = values

            metadata["parameters"].append(param_info)

        # --- Extract Filters ---
        for filter_elem in root.findall('.//filter'):
            filter_info = {
                "name": filter_elem.get('name'),
                "field": filter_elem.get('field'),
                "type": filter_elem.get('type')
            }
            metadata["filters"].append(filter_info)

        # --- Extract Actions ---
        for action in root.findall('.//action'):
            action_info = {
                "name": action.get('name'),
                "type": action.get('type'),
                "source": action.get('source'),
                "target": action.get('target')
            }
            metadata["actions"].append(action_info)

    except ET.ParseError as e:
        logger.error(f"Error parsing XML: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during XML parsing: {e}")
        return None

    return metadata
