#!/usr/bin/env python3
"""
Tableau File Structure Extractor

This script extracts content and metadata from Tableau (.twb and .twbx) files by:
1. Directly parsing .twb files
2. Extracting and parsing .twb files from .twbx archives (which are zip files)
3. Saving the extracted metadata as JSON files

Usage:
    python main.py [input_tableau_file]

Example:
    python main.py ./tableau-desktop-samples/sample.twbx
"""

import argparse
import os
import sys
from pathlib import Path

from src.common.logging import logger
from src.generators.tableu import process_tableau_file


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
                if arg in ['--output-dir', '-o'] and i + 1 < len(sys.argv):
                    output_dir = sys.argv[i + 1]
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
    path = Path(file_path)
    metadata_result, extracted_files = process_tableau_file(path, output_dir)

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
