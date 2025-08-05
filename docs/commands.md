# Cognos Migration Commands

## Report Migration

```bash
# Migrate a single report with explicit session
python -c "from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session; print(migrate_single_report_with_explicit_session('REPORT_ID', './output/report_migration_output', 'COGNOS_URL', 'SESSION_KEY'))"
```

## Module Migration

```bash
# Migrate a module with explicit session
python -c "from cognos_migrator.migrations.module import migrate_module_with_explicit_session; print(migrate_module_with_explicit_session('MODULE_ID', './output/module_migration_output', 'COGNOS_URL', 'SESSION_KEY'))"

# Migrate a module with reports from a folder
python -c "from cognos_migrator.migrations.module import migrate_module_with_explicit_session; print(migrate_module_with_explicit_session('MODULE_ID', './output/module_migration_output', 'COGNOS_URL', 'SESSION_KEY', folder_id='FOLDER_ID'))"

# Migrate a module with CPF metadata
python -c "from cognos_migrator.migrations.module import migrate_module_with_explicit_session; print(migrate_module_with_explicit_session('MODULE_ID', './output/module_migration_output', 'COGNOS_URL', 'SESSION_KEY', cpf_file_path='./path/to/cpf_file.cpf'))"
```

## Folder Migration

```bash
# Migrate all reports in a folder (recursive)
python -c "from cognos_migrator.migrations.folder import migrate_folder_with_explicit_session; print(migrate_folder_with_explicit_session('FOLDER_ID', './output/folder_migration_output', 'COGNOS_URL', 'SESSION_KEY'))"

# Migrate all reports in a folder (non-recursive)
python -c "from cognos_migrator.migrations.folder import migrate_folder_with_explicit_session; print(migrate_folder_with_explicit_session('FOLDER_ID', './output/folder_migration_output', 'COGNOS_URL', 'SESSION_KEY', recursive=False))"
```

## Post-Processing

```bash
# Post-process a module after migration
python -c "from cognos_migrator.main import post_process_module_with_explicit_session; print(post_process_module_with_explicit_session('MODULE_ID', './output/module_migration_output', 'COGNOS_URL', 'SESSION_KEY'))"

# Post-process a module with specific successful report IDs
python -c "from cognos_migrator.main import post_process_module_with_explicit_session; print(post_process_module_with_explicit_session('MODULE_ID', './output/module_migration_output', 'COGNOS_URL', 'SESSION_KEY', successful_report_ids=['REPORT_ID1', 'REPORT_ID2']))"
```

## Package Migration

```bash
# Migrate a Framework Manager package
python -c "from cognos_migrator.migrations.package import migrate_package_with_explicit_session; print(migrate_package_with_explicit_session('./path/to/package.xml', './output/package_migration_output', 'COGNOS_URL', 'SESSION_KEY'))"

# Migrate a Framework Manager package with reports from a folder
python -c "from cognos_migrator.migrations.package import migrate_package_with_explicit_session; print(migrate_package_with_explicit_session('./path/to/package.xml', './output/package_migration_output', 'COGNOS_URL', 'SESSION_KEY', folder_id='FOLDER_ID'))"

# Migrate a Framework Manager package with CPF metadata
python -c "from cognos_migrator.migrations.package import migrate_package_with_explicit_session; print(migrate_package_with_explicit_session('./path/to/package.xml', './output/package_migration_output', 'COGNOS_URL', 'SESSION_KEY', cpf_file_path='./path/to/cpf_file.cpf'))"

# Migrate a Framework Manager package with specific reports
python -c "from cognos_migrator.migrations.package import migrate_package_with_reports_explicit_session; print(migrate_package_with_reports_explicit_session('./path/to/package.xml', './output/package_migration_output', 'COGNOS_URL', 'SESSION_KEY', report_ids=['REPORT_ID1', 'REPORT_ID2']))"


worrking

python3 -c "from cognos_migrator.migrations.package import migrate_package_with_explicit_session; migrate_package_with_explicit_session(package_file_path='examples/packages/CAM Dmail Reporting.xml', output_path='output/package_migration_output', cognos_url='http://localhost:9300', session_key='CAM MTsxMDE6OGY2NmJiMDUtMDFhZS04ZDA1LTk1ZDYtZTkyZjI4ZDg5N2VkOjE4MjEyNzU0MDI7MDszOzA7')"

python migrate_fm_package.py --package-file examples/packages/Shared\ OFS\ Reporting.xml --output-path output/package_migration_output --cognos-url http://localhost:9300 --session-key "CAM MTsxMDE6OGY2NmJiMDUtMDFhZS04ZDA1LTk1ZDYtZTkyZjI4ZDg5N2VkOjE4MjEyNzU0MDI7MDszOzA7" --log-module package_migration