#!/usr/bin/env python3
"""
Script to extract CPF file information and save it to JSON files.
This is useful for testing and understanding the structure of CPF data.
"""

import os
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from cognos_migrator.cpf_parser import CPFParser
from cognos_migrator.cpf_extractor import CPFExtractor


def extract_cpf_to_json(cpf_file_path, output_dir):
    """
    Extract information from a CPF file and save it to JSON files.
    
    Args:
        cpf_file_path: Path to the CPF file
        output_dir: Directory to save the JSON files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize parser and parse the file
    parser = CPFParser(cpf_file_path)
    parser.parse()
    
    # Extract all metadata
    metadata = parser.extract_all()
    
    # Save the complete metadata
    with open(os.path.join(output_dir, "complete_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    # Extract and save individual components
    data_sources = parser.extract_data_sources()
    with open(os.path.join(output_dir, "data_sources.json"), "w", encoding="utf-8") as f:
        json.dump(data_sources, f, indent=2)
    
    query_subjects = parser.extract_query_subjects()
    with open(os.path.join(output_dir, "query_subjects.json"), "w", encoding="utf-8") as f:
        json.dump(query_subjects, f, indent=2)
    
    namespaces = parser.extract_namespaces()
    with open(os.path.join(output_dir, "namespaces.json"), "w", encoding="utf-8") as f:
        json.dump(namespaces, f, indent=2)
    
    # Initialize extractor and extract table schemas
    extractor = CPFExtractor(cpf_file_path)
    
    # Get all query subject names
    query_subject_names = [qs["name"] for qs in query_subjects]
    
    # Extract and save table schemas
    table_schemas = {}
    for name in query_subject_names:
        schema = extractor.get_table_schema(name)
        if schema:
            table_schemas[name] = schema
    
    with open(os.path.join(output_dir, "table_schemas.json"), "w", encoding="utf-8") as f:
        json.dump(table_schemas, f, indent=2)
    
    # Extract and save M-query contexts
    m_query_contexts = {}
    for name in query_subject_names:
        context = extractor.generate_m_query_context(name)
        if context:
            m_query_contexts[name] = context
    
    with open(os.path.join(output_dir, "m_query_contexts.json"), "w", encoding="utf-8") as f:
        json.dump(m_query_contexts, f, indent=2)
    
    print(f"Extracted CPF data from {cpf_file_path} to {output_dir}")
    print(f"Found {len(data_sources)} data sources, {len(query_subjects)} query subjects, and {len(namespaces)} namespaces")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_cpf_to_json.py <cpf_file_path> [output_dir]")
        sys.exit(1)
    
    cpf_file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "cpf_json_output"
    
    extract_cpf_to_json(cpf_file_path, output_dir)
