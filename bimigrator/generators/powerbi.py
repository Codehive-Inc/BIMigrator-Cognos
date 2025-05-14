import json
from pathlib import Path

from bimigrator.mapping.powerbi import parse_datasources, write_table_files


def generate_powerbi_content(directory_path):
    datasources_path = Path(directory_path) / 'extracted' / 'datasources.json'
    with open(datasources_path, 'r',encoding='utf-8') as file:
        datasources = json.load(file)
        parsed_datasources = parse_datasources(datasources)
        write_table_files(parsed_datasources)
