#!/usr/bin/env python3

import sys
import argparse
from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session
from cognos_migrator.migrations.module import migrate_module_with_explicit_session

def main():
    parser = argparse.ArgumentParser(description='Migrate Cognos reports and modules to Power BI')
    parser.add_argument('--type', required=True, choices=['report', 'module'], help='Type of object to migrate')
    parser.add_argument('--id', required=True, help='ID of the report or module to migrate')
    parser.add_argument('--output-path', required=True, help='Path where migration output will be saved')
    parser.add_argument('--cognos-url', required=True, help='The Cognos base URL')
    parser.add_argument('--session-key', required=True, help='The session key for authentication')
    
    args = parser.parse_args()
    
    # Run the migration
    if args.type == 'report':
        success = migrate_single_report_with_explicit_session(
            report_id=args.id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=args.session_key
        )
    else:  # module
        success = migrate_module_with_explicit_session(
            module_id=args.id,
            output_path=args.output_path,
            cognos_url=args.cognos_url,
            session_key=args.session_key
        )
    
    if success:
        print(f"Migration completed successfully. Output saved to: {args.output_path}")
        return 0
    else:
        print("Migration failed. Check logs for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
