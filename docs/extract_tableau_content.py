#!/usr/bin/env python3
"""
Tableau File Structure Extractor

This script extracts content and metadata from Tableau (.twb and .twbx) files by:
1. Directly parsing .twb files
2. Extracting and parsing .twb files from .twbx archives (which are zip files)
3. Saving the extracted metadata as JSON files

Usage:
    python extract_tableau_content.py [input_tableau_file]

Example:
    python extract_tableau_content.py ./tableau-desktop-samples/sample.twbx
"""

import os
import sys
import json
import zipfile
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
import argparse
from typing import Dict, List, Any, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
        for ds in root.findall('.//datasource'):
            ds_info = {"name": ds.get('name'), "version": ds.get('version'), "caption": ds.get('caption')}
            connection = ds.find('.//connection')
            if connection is not None:
                ds_info["connection_type"] = connection.get('class')
                ds_info["server"] = connection.get('server')
                ds_info["dbname"] = connection.get('dbname')
                ds_info["authentication"] = connection.get('authentication')
                
                # Extract connection attributes
                conn_attrs = {}
                for attr_name, attr_value in connection.attrib.items():
                    conn_attrs[attr_name] = attr_value
                ds_info["connection_attributes"] = conn_attrs
                
                # Extract columns/fields
                columns = []
                for col in ds.findall('.//column'):
                    col_info = {
                        "name": col.get('name'),
                        "datatype": col.get('datatype'),
                        "role": col.get('role'),
                        "type": col.get('type')
                    }
                    columns.append(col_info)
                ds_info["columns"] = columns
                
            metadata["datasources"].append(ds_info)

        # --- Extract Calculations ---
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

def process_tableau_file(file_path, output_base_dir=None):
    """Processes a .twb or .twbx file.
    
    Args:
        file_path: Path to the Tableau file
        output_base_dir: Base output directory (defaults to 'output' if None)
    """
    p = Path(file_path)
    metadata = None
    extracted_data_paths = []  # Store paths to any extracted files
    
    # Set up output directories
    if output_base_dir is None:
        # If no output directory is provided, use the default
        output_base_dir = "output"
        output_dir = Path(output_base_dir) / p.stem
    else:
        # If an output directory is provided, use it directly
        output_dir = Path(output_base_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create data directory for extracted files
    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)

    if p.suffix.lower() == '.twb':
        logger.info(f"Processing .twb file: {p.name}")
        try:
            with open(p, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            metadata = parse_twb_metadata(xml_content)
        except UnicodeDecodeError:
            # Try with different encodings if UTF-8 fails
            try:
                with open(p, 'r', encoding='latin-1') as f:
                    xml_content = f.read()
                metadata = parse_twb_metadata(xml_content)
            except Exception as e:
                logger.error(f"Error reading/parsing .twb file with latin-1 encoding: {e}")
        except Exception as e:
            logger.error(f"Error reading/parsing .twb file: {e}")

    elif p.suffix.lower() == '.twbx':
        logger.info(f"Processing .twbx file: {p.name}")
        try:
            with zipfile.ZipFile(p, 'r') as zip_ref:
                twb_file_name = None
                data_files = []
                
                # List all files in the archive
                for member in zip_ref.namelist():
                    if member.lower().endswith('.twb'):
                        twb_file_name = member
                    elif member.lower().endswith('.hyper') or member.lower().endswith('.tde'):
                        data_files.append(member)
                        logger.info(f"Found data extract: {member}")
                
                # Extract and process the .twb file
                if twb_file_name:
                    logger.info(f"Extracting metadata from: {twb_file_name}")
                    xml_content = zip_ref.read(twb_file_name).decode('utf-8', errors='replace')
                    metadata = parse_twb_metadata(xml_content)
                    
                    # Save the .twb file directly to the data directory
                    file_name = os.path.basename(twb_file_name)
                    extract_path = data_dir / file_name
                    with open(extract_path, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    extracted_data_paths.append(str(extract_path))
                    logger.info(f"Saved .twb file to: {extract_path}")
                else:
                    logger.error("No .twb file found within the .twbx archive.")
                
                # Extract any data files directly to the data directory (without preserving structure)
                for data_file in data_files:
                    # Just use the filename without any directory structure
                    file_name = os.path.basename(data_file)
                    extract_path = data_dir / file_name
                    with open(extract_path, 'wb') as f:
                        f.write(zip_ref.read(data_file))
                    extracted_data_paths.append(str(extract_path))
                    logger.info(f"Extracted data file to: {extract_path}")

        except zipfile.BadZipFile:
            logger.error(f"Error: Invalid or corrupted .twbx file: {p.name}")
        except Exception as e:
            logger.error(f"Error processing .twbx file: {e}")

    else:
        logger.error(f"Unsupported file type: {p.suffix}")

    if metadata:
        # Create the required directory structure
        extracted_dir = output_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True, parents=True)
        
        # Ensure data directory exists
        data_dir = output_dir / "data"
        data_dir.mkdir(exist_ok=True, parents=True)
        
        # Save metadata components to separate JSON files in the extracted directory
        for component, data in metadata.items():
            if data:  # Only save non-empty components
                # Use standardized name without the tableau file prefix
                output_json_path = extracted_dir / f"{component}.json"
                try:
                    with open(output_json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{component.capitalize()} metadata extracted to: {output_json_path}")
                except Exception as e:
                    logger.error(f"Error writing {component} metadata JSON: {e}")
        
        # Save complete metadata to a single file in the extracted directory
        complete_output_path = extracted_dir / "complete_metadata.json"
        try:
            with open(complete_output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
            logger.info(f"Complete metadata extracted to: {complete_output_path}")
        except Exception as e:
            logger.error(f"Error writing complete metadata JSON: {e}")

    # Return metadata and paths to any extracted files
    return metadata, extracted_data_paths

def main():
    """Main function to run the script."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract metadata from Tableau files (.twb or .twbx)')
    parser.add_argument('file_path', help='Path to the Tableau file to process')
    parser.add_argument('--output-dir', '-o', help='Output directory for extracted files (default: output)')
    
    # If the script is called with arguments containing spaces, they might be split
    # Let's handle this by reconstructing the file path if needed
    if len(sys.argv) > 2 and not sys.argv[1].startswith('-'):
        # Check if this might be a file path with spaces
        potential_path = ' '.join([arg for arg in sys.argv[1:] if not arg.startswith('-')])
        if os.path.exists(potential_path):
            file_path = potential_path
            # Extract any options
            output_dir = None
            for i, arg in enumerate(sys.argv):
                if arg in ['--output-dir', '-o'] and i+1 < len(sys.argv):
                    output_dir = sys.argv[i+1]
        else:
            # Fall back to regular argument parsing
            args = parser.parse_args()
            file_path = args.file_path
            output_dir = args.output_dir
    elif len(sys.argv) > 1:
        # Parse arguments normally
        args = parser.parse_args()
        file_path = args.file_path
        output_dir = args.output_dir
    else:
        # No arguments provided
        parser.print_help()
        sys.exit(1)
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
        
    logger.info(f"Starting extraction process for: {file_path}")
    logger.info(f"Output directory: {output_dir if output_dir else 'output'} (default)")
    metadata_result, extracted_files = process_tableau_file(file_path, output_dir)

    if metadata_result:
        logger.info("\nExtraction Summary:")
        logger.info(f"- Found {len(metadata_result.get('datasources', []))} datasources")
        logger.info(f"- Found {len(metadata_result.get('calculations', []))} calculations")
        logger.info(f"- Found {len(metadata_result.get('worksheets', []))} worksheets")
        logger.info(f"- Found {len(metadata_result.get('dashboards', []))} dashboards")
        logger.info(f"- Found {len(metadata_result.get('parameters', []))} parameters")
    
    if extracted_files:
        logger.info(f"\nExtracted files: {len(extracted_files)}")
        for file in extracted_files:
            logger.info(f"- {file}")

if __name__ == "__main__":
    main()
