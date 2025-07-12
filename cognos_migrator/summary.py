"""
Migration summary generation functionality

This module provides functionality for generating migration summary reports
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict


class MigrationSummaryGenerator:
    """Generator for migration summary reports"""

    def __init__(self, logger=None):
        """Initialize the migration summary generator
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)

    def generate_migration_summary(self, results: Dict[str, bool], output_path: str):
        """Generate migration summary report
        
        Args:
            results: Dictionary mapping report IDs to success status
            output_path: Base output path for the migration
        """
        try:
            summary_path = Path(output_path) / "migration_summary.md"
            
            total_reports = len(results)
            successful_reports = sum(1 for success in results.values() if success)
            failed_reports = total_reports - successful_reports
            
            # Calculate success rate with check for division by zero
            success_rate = 0.0
            if total_reports > 0:
                success_rate = (successful_reports / total_reports) * 100
            
            summary_content = f"""# Migration Summary Report

## Overview
- **Total Reports**: {total_reports}
- **Successful Migrations**: {successful_reports}
- **Failed Migrations**: {failed_reports}
- **Success Rate**: {success_rate:.1f}%

## Migration Results

### Successful Migrations
"""
            
            for report_id, success in results.items():
                if success:
                    summary_content += f"- ✓ {report_id}\n"
            
            summary_content += "\n### Failed Migrations\n"
            
            for report_id, success in results.items():
                if not success:
                    summary_content += f"- ✗ {report_id}\n"
            
            summary_content += f"""

## Migration Details
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Output Directory**: {output_path}

## Next Steps
1. Review failed migrations and check logs for error details
2. Validate successful migrations by opening in Power BI Desktop
3. Test data connections and refresh capabilities
4. Review and adjust visual layouts as needed
"""
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            self.logger.info(f"Generated migration summary: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration summary: {e}")
