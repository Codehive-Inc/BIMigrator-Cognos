#!/usr/bin/env python3
"""
Test script to run an actual migration with the sample Cognos report
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from cognos_migrator.config import ConfigManager
from cognos_migrator.migrator import CognosToPowerBIMigrator
from cognos_migrator.parsers import CognosReportParser

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('actual_migration.log'),
            logging.StreamHandler()
        ]
    )

def test_sample_report_migration():
    """Test migration with the sample Cognos report"""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize configuration
        config = ConfigManager()
        logger.info("Configuration loaded successfully")
        
        # Initialize migrator
        migrator = CognosToPowerBIMigrator(config)
        logger.info("Migrator initialized successfully")
        
        # Check if sample report exists
        sample_report_path = Path("cognos_sample_report.xml")
        if not sample_report_path.exists():
            logger.error(f"Sample report not found: {sample_report_path}")
            return False
        
        logger.info(f"Found sample report: {sample_report_path}")
        
        # Parse the sample report
        parser = CognosReportParser()
        with open(sample_report_path, 'r', encoding='utf-8') as f:
            report_xml = f.read()
        
        logger.info("Parsing sample Cognos report...")
        cognos_report = parser.parse_report_xml(report_xml, "sample_report")
        logger.info(f"Successfully parsed report: {cognos_report.name}")
        logger.info(f"Report contains {len(cognos_report.queries)} queries")
        logger.info(f"Report contains {len(cognos_report.data_items)} data items")
        
        # Generate Power BI project
        logger.info("Generating Power BI project...")
        output_dir = Path("output") / "sample_migration"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        powerbi_project = migrator.migrate_report(cognos_report, str(output_dir))
        logger.info(f"Successfully generated Power BI project: {powerbi_project.name}")
        logger.info(f"Output directory: {output_dir}")
        
        # List generated files
        if output_dir.exists():
            logger.info("Generated files:")
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    logger.info(f"  - {file_path.relative_to(output_dir)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main test function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== Testing Actual Migration with Sample Report ===")
    
    if test_sample_report_migration():
        logger.info("✅ Migration test completed successfully!")
        return 0
    else:
        logger.error("❌ Migration test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
