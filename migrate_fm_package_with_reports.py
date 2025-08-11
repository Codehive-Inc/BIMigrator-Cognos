#!/usr/bin/env python3
"""
Script to migrate a Cognos Framework Manager package file to Power BI with specific reports.
This script uses the enhanced migration function that filters tables based on report usage.
"""

import os
import sys
import argparse
from cognos_migrator.migrations import migrate_package_with_reports_explicit_session, migrate_package_with_local_reports
from cognos_migrator.common.logging import configure_logging

def main():
    parser = argparse.ArgumentParser(description='Migrate a Cognos Framework Manager package file to Power BI with specific reports')
    parser.add_argument('--package-file', required=True, help='Path to the FM package XML file')
    parser.add_argument('--output-path', required=True, help='Path where migration output will be saved')
    parser.add_argument('--cognos-url', required=True, help='The Cognos base URL')
    parser.add_argument('--session-key', required=True, help='The session key for authentication')
    
    # Mutually exclusive group for report source
    report_source_group = parser.add_mutually_exclusive_group(required=True)
    report_source_group.add_argument('--report-ids', help='Comma-separated list of report IDs to migrate with the package')
    report_source_group.add_argument('--report-file-paths', help='Comma-separated list of local report XML file paths to migrate')

    parser.add_argument('--cpf-file', help='Optional path to CPF file for enhanced metadata')
    parser.add_argument('--auth-key', default='IBM-BA-Authorization', help='The authentication header key')
    parser.add_argument('--log-module', default=None, help='Module name for log file generation (e.g., "package_migration")')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry run mode (skip actual Cognos API calls)')
    
    args = parser.parse_args()
    
    # Configure logging with module name if provided
    if args.log_module:
        configure_logging(args.log_module)
        print(f"Logging to file with module name: {args.log_module}")
    
    success = False
    if args.report_ids:
        # Parse report IDs from comma-separated string
        report_ids = [report_id.strip() for report_id in args.report_ids.split(',')]
        print(f"Migrating package with {len(report_ids)} reports by ID: {report_ids}")
        
        # Call the enhanced migration function for report IDs
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
    elif args.report_file_paths:
        # Parse report file paths from comma-separated string
        report_file_paths = [path.strip() for path in args.report_file_paths.split(',')]
        print(f"Migrating package with {len(report_file_paths)} local reports: {report_file_paths}")
        
        # Call the migration function for local report files
        success = migrate_package_with_local_reports(
            package_file_path=args.package_file,
            output_path=args.output_path,
            report_file_paths=report_file_paths,
            cognos_url=args.cognos_url,
            session_key=args.session_key,
        )

    if success:
        print("Migration completed successfully!")
        sys.exit(0)
    else:
        print("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
