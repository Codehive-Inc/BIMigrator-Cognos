#!/usr/bin/env python3
"""
Enhanced CLI Entry Point (SOLID Version)

Entry point for the refactored CLI following SOLID principles.
This replaces the monolithic enhanced_cli.py with a modular approach.
"""

import sys
from cognos_migrator.cli import EnhancedCLI


def main():
    """Main entry point"""
    cli = EnhancedCLI()
    success = cli.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()