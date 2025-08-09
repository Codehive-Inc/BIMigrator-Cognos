#!/usr/bin/env python3
"""
Script to migrate a Cognos Framework Manager package file to Power BI with specific reports.
This script uses the enhanced migration function that filters tables based on report usage.
"""

import os
import sys
import argparse
from cognos_migrator.migrations import migrate_package_with_reports_explicit_session
from cognos_migrator.common.logging import configure_logging

def main():
    parser = argparse.ArgumentParser(description='Migrate a Cognos Framework Manager package file to Power BI with specific reports')
    parser.add_argument('--package-file', required=True, help='Path to the FM package XML file')
    parser.add_argument('--output-path', required=True, help='Path where migration output will be saved')
    parser.add_argument('--cognos-url', required=True, help='The Cognos base URL')
    parser.add_argument('--session-key', required=True, help='The session key for authentication')
    parser.add_argument('--report-ids', required=True, help='Comma-separated list of report IDs to migrate with the package')
    parser.add_argument('--cpf-file', help='Optional path to CPF file for enhanced metadata')
    parser.add_argument('--auth-key', default='IBM-BA-Authorization', help='The authentication header key')
    parser.add_argument('--log-module', default=None, help='Module name for log file generation (e.g., "package_migration")')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry run mode (skip actual Cognos API calls)')
    
    args = parser.parse_args()
    
    # Configure logging with module name if provided
    if args.log_module:
        configure_logging(args.log_module)
        print(f"Logging to file with module name: {args.log_module}")
    
    # Parse report IDs from comma-separated string
    report_ids = [report_id.strip() for report_id in args.report_ids.split(',')]
    print(f"Migrating package with {len(report_ids)} reports: {report_ids}")
    
    # Call the enhanced migration function
    success = migrate_package_with_reports_explicit_session(
        package_file_path=args.package_file,
        output_path=args.output_path,
        cognos_url=args.cognos_url,
        session_key=args.session_key,
        report_ids=report_ids,
        cpf_file_path=args.cpf_file,
        auth_key=args.auth_key,
        dry_run=args.dry_run
    )
    
    if success:
        print("Migration completed successfully!")
        sys.exit(0)
    else:
        print("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
