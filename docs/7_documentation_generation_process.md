# Documentation Generation Process

## Overview

The documentation generation process creates migration reports and documentation to help users understand the migration results, including any issues or limitations encountered during the process.

## Process Flow

1. **Collect Migration Information**
   - Gather details about the migrated report
   - Collect statistics about converted elements
   - Identify any issues or limitations

2. **Generate Migration Report**
   - Create a structured report document
   - Include summary statistics
   - Document any issues or warnings

3. **Save Documentation**
   - Write documentation to the output directory
   - Format as HTML, Markdown, or JSON

## Key Components

### DocumentationGenerator Class

The `DocumentationGenerator` class in `generators.py` handles the generation of migration documentation:

```python
class DocumentationGenerator:
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_migration_report(self, project: PowerBIProject, output_path: str) -> bool:
        """Generate migration documentation"""
        try:
            # Build migration report content
            report_content = self._build_migration_report(project)
            
            # Write report to file
            report_path = Path(output_path) / "migration_report.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            
            self.logger.info(f"Generated migration report: {report_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {e}")
            return False
    
    def _build_migration_report(self, project: PowerBIProject) -> str:
        """Build migration report content"""
        # Create report header
        report = f"# Migration Report: {project.name}\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Add data model summary
        report += "## Data Model Summary\n\n"
        report += f"- Tables: {len(project.data_model.tables)}\n"
        report += f"- Relationships: {len(project.data_model.relationships)}\n"
        report += f"- Measures: {len(project.data_model.measures)}\n\n"
        
        # Add table details
        report += "### Tables\n\n"
        for table in project.data_model.tables:
            report += f"#### {table.name}\n\n"
            report += f"- Columns: {len(table.columns)}\n"
            report += "- Column Details:\n"
            for column in table.columns:
                report += f"  - {column.name} ({column.data_type})\n"
            report += "\n"
        
        # Add report summary
        if project.report:
            report += "## Report Summary\n\n"
            report += f"- Pages: {len(project.report.pages)}\n"
            report += f"- Visuals: {sum(len(page.visuals) for page in project.report.pages)}\n\n"
            
            # Add page details
            report += "### Pages\n\n"
            for page in project.report.pages:
                report += f"#### {page.name}\n\n"
                report += f"- Visuals: {len(page.visuals)}\n"
                report += "- Visual Details:\n"
                for visual in page.visuals:
                    report += f"  - {visual.type}: {visual.title or 'Untitled'}\n"
                report += "\n"
        
        # Add known limitations
        report += "## Known Limitations\n\n"
        report += "The following limitations were encountered during migration:\n\n"
        report += "- Some complex Cognos expressions may not be fully translated to DAX\n"
        report += "- Advanced formatting options may require manual adjustment\n"
        report += "- Custom JavaScript elements are not supported in Power BI\n"
        
        return report
```

### Migration Summary in CognosMigrator

The `CognosMigrator` class also generates a summary of the migration results:

```python
def _generate_migration_summary(self, results: Dict[str, bool], output_path: str):
    """Generate migration summary report"""
    try:
        summary_path = Path(output_path) / "migration_summary.json"
        
        # Calculate statistics
        total = len(results)
        successful = sum(1 for success in results.values() if success)
        failed = total - successful
        
        # Create summary
        summary = {
            "timestamp": str(datetime.now()),
            "total_reports": total,
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful / total) * 100:.2f}%" if total > 0 else "0%",
            "details": {
                report_id: "Success" if success else "Failed"
                for report_id, success in results.items()
            }
        }
        
        # Write summary to file
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Generated migration summary: {summary_path}")
        
    except Exception as e:
        self.logger.error(f"Failed to generate migration summary: {e}")
```

## Output Files

The documentation generation process produces the following files:

1. **migration_report.md**: Detailed report of the migration process, including data model and report structure information.

2. **migration_summary.json**: Summary statistics of batch migrations, including success rates and details for each report.

These documentation files help users understand the migration results and identify any issues that may require manual intervention.
