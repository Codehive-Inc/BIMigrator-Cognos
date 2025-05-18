from pathlib import Path
from typing import Any

import yaml

from bimigrator.configdata_classes import PowerBiColumn

YAML_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config' / 'twb-to-pbi.yaml'


def convert_column(column):
    yaml_content = open(YAML_CONFIG_PATH, encoding='utf-8').read()
    datatype_mapping = yaml.safe_load(yaml_content)['tableau_datatype_to_tmdl']
    power_bi_column = PowerBiColumn(
        pbi_name=column['name'],
        pbi_datatype=datatype_mapping.get(column['datatype']),
        source_name='',
        source_column=column['name']
    )
    return power_bi_column


def parse_datasources(datasources: list[dict[str, Any]]):
    data = []
    for ds in datasources:
        relation = ds.get('relation')
        columns = ds.get('columns', [])
        pb_columns = []
        for column in columns:
            pb_column = convert_column(column)
            pb_columns.append(pb_column)
        data.append({
            "filename": relation.get('name'),
            "columns": pb_columns
        })
    return data


transform_column_maps = {
    "int64": "Int64.Type",
    "date": "Int64.Type",
    "double": "type number",
    'string': "type text"
}


def generate_column_strings(columns):
    column_strings = []
    for c in columns:
        if c.pbi_datatype:
            column_type = transform_column_maps[c.pbi_datatype]
            column_strings.append("\t\t\t\t{" + f"\"{c.pbi_name}\"" + "," + column_type + "},")
    return column_strings


def generate_partition_code(
        source_table_name, column_strings, file_path
):
    code = [
        f"\tpartition {source_table_name} = m",
        "\tmode: import",
        "\tsource =",
        "\t\tlet",
        f"\t\t\tSource = Excel.Workbook(File.Contents(\"{file_path}\"), null, true),",
        f"\t\t\t{source_table_name}_Sheet = Source{{[Item=\"{source_table_name}\",Kind=\"Sheet\"]}}[Data],",
        f"\t\t\t#\"Promoted Headers\" = Table.PromoteHeaders({source_table_name}_Sheet, [PromoteAllScalars=true]),",
        "\t\t\t#\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\",{",
        *column_strings,
        "\t\t\t})",
        "\t\tin",
        "\t\t\t#\"Changed Type\"",
        "",
        "\tannotation PBI_ResultType = Table"
    ]

    return "\n".join(code)


def write_table_files(twb_tables, destination_dir=None):
    output_path = Path('output/PowerBI/Model/tables')
    output_path.mkdir(exist_ok=True, parents=True)
    for twb_table in twb_tables:
        table_name = twb_table['filename']
        filepath = twb_table['filepath']
        with open(str(output_path.resolve() / table_name) + ".tmdl", 'w', encoding='utf-8') as table_file:
            table_file.write("table " + table_name + "\n")
            indent_level = 1
            indent = "\t" * indent_level
            for column in twb_table['columns']:
                column_name = f"'{column.pbi_name}'" if " " in column.pbi_name else f"{column.pbi_name}"
                formatted_data = [
                    r"column {}".format(column_name),
                    "\tdataType: {}".format(column.pbi_datatype),
                    "\tsourceColumn: {}".format(column.source_column)
                ]
                table_file.write(indent + "\n\t".join(formatted_data))
                table_file.write("\n")
            column_strings = generate_column_strings(twb_table['columns'])
            partition_string = generate_partition_code(table_name, column_strings, filepath)
            table_file.write(partition_string)
