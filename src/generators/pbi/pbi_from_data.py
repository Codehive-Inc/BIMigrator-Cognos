from typing import Any, Dict
from pybars import Compiler
import json
import yaml
import os

class PbiFromData:
	def __init__(self, project_name: str):
		self.config_yaml_path = 'config/twb-to-pbi.yaml'
		self.template_dir = 'templates'
		self.sample_data_path = 'generators/pbi/data_template_mapping.json'
		self.output_dir = f'output/{project_name}'

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
		Read the sample JSON file for the given key and return its content as a dictionary.
		:param key: The key to look up in the sample JSON mapping.
		:return: The content of the sample JSON file.
		"""
		
		with open('src/generators/pbi/data_template_mapping.json', 'r') as file:
			mapping = json.load(file)
		entry = mapping.get(key, {})
		data_file = entry.get('data_file')
		if data_file and os.path.exists(data_file):
			with open(data_file, 'r') as f:
				return json.load(f)
		return {}

	@staticmethod
	def __get_template_content(key: str, yaml_map: str) -> str:
		"""
		Read the content of a template file.
		:param template_path: Path to the template file.
		:return: Content of the template file as a string.
		"""
		template_path = f'templates/{yaml_map[key].get('template', '')}'
		if os.path.exists(template_path):
			with open(template_path, 'r') as file:
				return file.read()
		return ''

	@staticmethod
	def __create_output_directory_if_not_exists(output_path: str) -> None:
		"""
		Create the output directory if it does not exist.
		:param output_path: Path to the output directory.
		"""
		if not os.path.exists(output_path):
			os.makedirs(output_path)

	@staticmethod
	def __write_output_file(output_path: str, content: str) -> None:
		"""
		Write the rendered content to the specified output file.
		:param output_path: Path to the output file.
		:param content: Content to write to the output file.
		"""
		output_dir = os.path.dirname(output_path)
		PbiFromData.__create_output_directory_if_not_exists(output_dir)
		with open(output_path, 'w') as file:
			file.write(content)


	def pbi_from_data(self):
		"""
		Main function to generate Power BI files from data.
		"""
		yaml_content = PbiFromData.__read_yaml(self.config_yaml_path)
		yaml_map = PbiFromData.__get_yaml_mappings_for_templates(yaml_content)

		for key in yaml_map.keys():
			template = PbiFromData.__get_template_content(key, yaml_map)
			sample_data = PbiFromData.__get_sample_json_content(key)
			output_path = self.output_dir + "/" + PbiFromData.__get_output_path(key, yaml_map)
			rendered_content = PbiFromData.__generate_pbi_from_data(template, sample_data)
			PbiFromData.__write_output_file(output_path, rendered_content)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Run PBI from data utility")

	parser.add_argument(
		"--project_name",
		type=str,
		required=False,
		help="Project name (optional)"
	)
	args = parser.parse_args()
	project_name = args.project_name if args.project_name else "default_project"
	pbi_generator = PbiFromData(project_name)
	pbi_generator.pbi_from_data()