#!/usr/bin/env python3
"""
Standalone Enhanced CLI Entry Point (SOLID Version)

Standalone entry point that avoids circular imports by not importing the main cognos_migrator module.
This script adds the project root to the Python path and imports directly from cli modules.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import the CLI directly without going through cognos_migrator.__init__
from cognos_migrator.cli.main_cli import EnhancedCLI


def main():
    """Main entry point"""
    cli = EnhancedCLI()
    success = cli.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()