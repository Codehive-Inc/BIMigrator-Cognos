#!/usr/bin/env python3
"""
Script to clean Python cache files (__pycache__ directories and .pyc files)
"""

import os
import shutil
import sys
from pathlib import Path


def clean_pycache(directory):
    """
    Recursively remove __pycache__ directories and .pyc files from the given directory
    
    Args:
        directory (str): Path to the directory to clean
    
    Returns:
        tuple: (int, int) - Number of directories and files removed
    """
    dir_count = 0
    file_count = 0
    
    # Convert to Path object for easier handling
    directory = Path(directory)
    
    # Find and remove __pycache__ directories
    for pycache_dir in directory.glob('**/__pycache__'):
        if pycache_dir.is_dir():
            print(f"Removing directory: {pycache_dir}")
            shutil.rmtree(pycache_dir)
            dir_count += 1
    
    # Find and remove .pyc files
    for pyc_file in directory.glob('**/*.pyc'):
        if pyc_file.is_file():
            print(f"Removing file: {pyc_file}")
            pyc_file.unlink()
            file_count += 1
    
    # Find and remove .pyo files (optimized Python files)
    for pyo_file in directory.glob('**/*.pyo'):
        if pyo_file.is_file():
            print(f"Removing file: {pyo_file}")
            pyo_file.unlink()
            file_count += 1
            
    return dir_count, file_count


if __name__ == "__main__":
    # Use the current directory if no directory is specified
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    print(f"Cleaning Python cache files in: {os.path.abspath(target_dir)}")
    dir_count, file_count = clean_pycache(target_dir)
    
    print(f"\nCleanup complete!")
    print(f"Removed {dir_count} __pycache__ directories")
    print(f"Removed {file_count} .pyc/.pyo files")
