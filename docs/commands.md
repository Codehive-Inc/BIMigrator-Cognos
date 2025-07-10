# Migration Commands

## Report Migration

```bash
# Migrate the original report
python -c "from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session; print(migrate_single_report_with_explicit_session('i85E7DF75D282452BAF5231C18F5B48A7', './output/report_migration_output', 'http://20.244.32.126:9300/api/v1', 'CAM MTsxMDE6ZmI3MTRmNDgtYmUxNi1iYWIwLTdjZWUtM2ViZDA5MDk0OWVlOjM3OTY2Njc2NDA7MDszOzA7'))"

# Migrate the new report
python -c "from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session; print(migrate_single_report_with_explicit_session('i8784E26F14594A03B0791EC6AD590BC4', './output/report_migration_output2', 'http://20.244.32.126:9300/api/v1', 'CAM MTsxMDE6ZmI3MTRmNDgtYmUxNi1iYWIwLTdjZWUtM2ViZDA5MDk0OWVlOjM3OTY2Njc2NDA7MDszOzA7'))"
```

## Module Migration

```bash
# Migrate the module
python -c "from cognos_migrator.migrations.module import migrate_module_with_explicit_session; print(migrate_module_with_explicit_session('i5F34A7A52E2645C0AB03C34BA50941D7', './output/module_migration_output', 'http://20.244.32.126:9300/api/v1', 'CAM MTsxMDE6ZmI3MTRmNDgtYmUxNi1iYWIwLTdjZWUtM2ViZDA5MDk0OWVlOjM3OTY2Njc2NDA7MDszOzA7'))"
```

## Create a CLI Script

For easier migration, you can create a simple CLI script:

```bash
# Create migration.py script
cat > migration.py << 'EOF'
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
EOF

# Make it executable
chmod +x migration.py
```

Then you can run migrations using:

```bash
# Migrate a report
./migration.py --type report --id i8784E26F14594A03B0791EC6AD590BC4 --output-path ./output/report_migration_output2 --cognos-url http://20.244.32.126:9300/api/v1 --session-key "CAM MTsxMDE6ZmI3MTRmNDgtYmUxNi1iYWIwLTdjZWUtM2ViZDA5MDk0OWVlOjM3OTY2Njc2NDA7MDszOzA7"

# Migrate a module
./migration.py --type module --id i5F34A7A52E2645C0AB03C34BA50941D7 --output-path ./output/module_migration_output --cognos-url http://20.244.32.126:9300/api/v1 --session-key "CAM MTsxMDE6ZmI3MTRmNDgtYmUxNi1iYWIwLTdjZWUtM2ViZDA5MDk0OWVlOjM3OTY2Njc2NDA7MDszOzA7"
```


