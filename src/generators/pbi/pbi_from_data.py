from typing import Any, Dict
from pybars import Compiler
import json
import yaml


class PbiFromData:
	def __init__(self):
		self.config_yaml_path = 'config/twb-to-pbi.yaml'
		self.template_dir = 'templates'
		self.sample_data_path = 'generators/pbi/data_template_mapping.json'

	@staticmethod
	def __generate_pbi_from_data(template: str, data: Dict[str, Any]) -> str:
		"""
		Render a pybars3 template string with the provided data dictionary.
		:param template: The pybars3 template string.
		:param data: The data dictionary to fill the template.
		:return: Rendered string output.
		"""
		compiler = Compiler()
		template_func = compiler.compile(template)
		output = template_func(data)
		return output.decode() if isinstance(output, bytes) else str(output)
	
	@staticmethod
	def __read_yaml(file_path: str) -> Dict[str, Any]:
		"""
		Read a YAML file and return its content as a dictionary.
		:param file_path: Path to the YAML file.
		:return: Dictionary representation of the YAML file.
		"""
		with open(file_path, 'r') as file:
			return yaml.safe_load(file)
	
	@staticmethod
	def __get_yaml_mappings_for_templates(yaml_content: dict) -> Dict[str, str]:
		"""
		Extract template mappings from the YAML content.
		:param yaml_content: The YAML content as a string.
		:return: A dictionary of template mappings.
		"""
		return yaml_content.get('Templates', {}).get('mappings', {})

	@staticmethod
	def __get_output_path(key:str, yaml_map: dict)-> str:
		"""
		Extract the output path for a given key from the YAML mappings.
		:param key: The key to look up in the YAML mappings.
		:param yaml_map: The dictionary containing YAML mappings.
		:return: The output path associated with the given key.
		"""
		return yaml_map[key].get('output', '')
	
	@staticmethod
	def __get_sample_json_content(key):
		"""
		Read the sample JSON file and return its content as a dictionary.
		:param key: The key to look up in the sample JSON.
		:return: The content associated with the given key.
		"""
		with open('src/generators/pbi/data_template_mapping.json', 'r') as file:
			data = json.load(file)
			return data.get(key, {})
		
