#!/usr/bin/env python
"""
Command-line tool for extracting metadata from Cognos Framework Manager .cpf files.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path

from cognos_migrator.cpf_parser import CPFParser

def setup_logging(verbose=False):
    """Configure logging"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract metadata from Cognos Framework Manager .cpf files'
    )
    
    parser.add_argument(
        'cpf_file',
        help='Path to the .cpf file to extract metadata from'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory for extracted metadata (default: ./output)',
        default='./output'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        help='Enable verbose logging',
        action='store_true'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate input file
    cpf_file = Path(args.cpf_file)
    if not cpf_file.exists():
        logger.error(f"CPF file not found: {cpf_file}")
        sys.exit(1)
    
    if not cpf_file.suffix.lower() == '.cpf':
        logger.warning(f"File does not have .cpf extension: {cpf_file}")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename
    output_file = output_dir / f"{cpf_file.stem}_metadata.json"
    
    # Parse CPF file and extract metadata
    logger.info(f"Extracting metadata from: {cpf_file}")
    parser = CPFParser(str(cpf_file))
    
    if parser.save_metadata_to_json(str(output_file)):
        logger.info(f"Metadata successfully extracted to: {output_file}")
    else:
        logger.error("Failed to extract metadata")
        sys.exit(1)

if __name__ == '__main__':
    main()
