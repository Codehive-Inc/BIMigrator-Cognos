import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from bimigrator.common.helpers import zip_directory
from bimigrator.common.logging import logger
from bimigrator.parsers.metadata import parse_twb_metadata


def process_tableau_file(file_input, output_base_dir=None):
    """Processes a .twb or .twbx file.

    Args:
        file_input: Either a path string to the Tableau file or a bytes IO object
        output_base_dir: Base output directory (defaults to 'output' if None)
    """
    metadata = None
    extracted_data_paths = []  # Store paths to any extracted files

    # Handle the file input type
    if isinstance(file_input, str):
        p = Path(file_input)
        file_name = p.name
        file_stem = p.stem
    else:
        # Assume it's a bytes IO object with a name attribute
        file_name = getattr(file_input, 'name', 'tableau_file')
        file_stem = Path(file_name).stem

    # Set up output directories
    if output_base_dir is None:
        output_base_dir = "output"
        output_dir = Path(output_base_dir) / file_stem
    else:
        output_dir = Path(output_base_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create data directory for extracted files
    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # Determine file type from name
    is_twb = file_name.lower().endswith('.twb')
    is_twbx = file_name.lower().endswith('.twbx')

    if is_twb:
        logger.info(f"Processing .twb file: {file_name}")
        print("FILE INPUT: ", file_input)
        try:
            if isinstance(file_input, (str, Path)):
                with open(file_input, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            else:
                xml_content = file_input.read().decode('utf-8')
            metadata = parse_twb_metadata(xml_content)
        except UnicodeDecodeError:
            # Try with different encodings if UTF-8 fails
            try:
                if isinstance(file_input, (str, Path)):
                    with open(file_input, 'r', encoding='latin-1') as f:
                        xml_content = f.read()
                else:
                    file_input.seek(0)
                    xml_content = file_input.read().decode('latin-1')
                metadata = parse_twb_metadata(xml_content)
            except Exception as e:
                logger.error(f"Error reading/parsing .twb file with latin-1 encoding: {e}")
        except Exception as e:
            logger.error(f"Error reading/parsing .twb file: {e}")

    elif is_twbx:
        logger.info(f"Processing .twbx file: {file_name}")
        try:
            if isinstance(file_input, (str, Path)):
                zip_file = zipfile.ZipFile(file_input, 'r')
            else:
                import io
                zip_file = zipfile.ZipFile(io.BytesIO(file_input.read()))

            with zip_file as zip_ref:
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

                # Extract any data files
                for data_file in data_files:
                    file_name = os.path.basename(data_file)
                    extract_path = data_dir / file_name
                    with open(extract_path, 'wb') as f:
                        f.write(zip_ref.read(data_file))
                    extracted_data_paths.append(str(extract_path))
                    logger.info(f"Extracted data file to: {extract_path}")

        except zipfile.BadZipFile:
            logger.error(f"Error: Invalid or corrupted .twbx file: {file_name}")
        except Exception as e:
            logger.error(f"Error processing .twbx file: {e}")

    else:
        logger.error(f"Unsupported file type: {Path(file_name).suffix}")

    # Return metadata and paths to any extracted files
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

    return metadata, extracted_data_paths


def process_tableau_file_buffer(file):
    """
    Process a .twb or .twbx file.

    Args:
         file: binary file.
    """
    zipped = io.BytesIO()
    file_stem = Path(file.name).stem
    with tempfile.TemporaryDirectory() as tempdir:
        path = Path(tempdir).resolve() / file_stem
        process_tableau_file(file, path)
        zipped = zip_directory(path)
    return zipped
