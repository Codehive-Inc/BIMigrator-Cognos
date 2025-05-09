from pathlib import Path

from config.data_classes import PowerBiColumn
from src.common.yaml import parse_yaml

YAML_CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'twb-to-pbi.yaml'


def convert_column(column):
    yaml_content = open(YAML_CONFIG_PATH, encoding='utf-8').read()
    datatype_mapping = parse_yaml(yaml_content)['tableau_datatype_to_tmdl']
    power_bi_column = PowerBiColumn(
        pbi_name=column['name'],
        pbi_datatype=datatype_mapping.get(column['datatype']),
        source_name=''
    )
    return power_bi_column


def convert_data_sources_to_pbi(datasources):
    data = []
    for ds in datasources:
        main_caption = ds.get('caption', '').strip()
        connections = ds.get('connections', {})
        connection_class = connections.get('class')
        captions_list = []
        if connection_class == 'federated':
            connection_data = connections.get('connections', [])
            for connection in connection_data:
                caption = connection.get('caption')
                captions_list.append(caption)
        # Sanitize the caption to get name
        for cp in captions_list:
            main_caption = main_caption.replace(cp, "")
        main_caption = main_caption.replace("(", "").replace(")", "").strip()
        columns = ds.get('columns', [])
        pb_columns = []
        for column in columns:
            pb_column = convert_column(column)
            pb_columns.append(pb_column)
        data.append({
            "filename": main_caption,
            "columns": pb_columns
        })
    return data


def write_tmdl_files(twb_tables):
    for twb_table in twb_tables:
        table_name = twb_table['filename']
        with open(table_name + ".tmdl", 'w', encoding='utf-8') as table_file:
            table_file.write("table " + table_name + "\n")
            indent_level = 1
            indent = "\t" * indent_level
            for column in twb_table['columns']:
                column_name = f"'{column.pbi_name}'" if " " in column.pbi_name else f"{column.pbi_name}"
                formatted_data = [
                    r"column {}".format(column_name),
                    "\tdataType: {}".format(column.pbi_datatype),
                ]

                table_file.write(indent + "\n\t".join(formatted_data))
                table_file.write("\n")
