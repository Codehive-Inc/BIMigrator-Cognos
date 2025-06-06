"""
Main entry point for Cognos to Power BI migration tool
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

from cognos_migrator.config import ConfigManager
from cognos_migrator.migrator import CognosToPowerBIMigrator, MigrationBatch


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('migration.log')
        ]
    )


def load_config():
    """Load migration configuration"""
    config_manager = ConfigManager()
    return config_manager.load_config()


def migrate_single_report(report_id: str, output_path: Optional[str] = None):
    """Migrate a single Cognos report"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize migrator
        migrator = CognosToPowerBIMigrator(config)
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            return False
        
        # Set output path
        if not output_path:
            output_path = Path(config.output_directory) / f"report_{report_id}"
        
        # Perform migration
        logger.info(f"Starting migration of report: {report_id}")
        success = migrator.migrate_report(report_id, str(output_path))
        
        if success:
            logger.info(f"✓ Successfully migrated report {report_id} to {output_path}")
            
            # Show migration status
            status = migrator.get_migration_status(str(output_path))
            logger.info(f"Migration status: {status}")
            
        else:
            logger.error(f"✗ Failed to migrate report {report_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False


def migrate_multiple_reports(report_ids: List[str], output_base_path: Optional[str] = None):
    """Migrate multiple Cognos reports"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize migrator
        migrator = CognosToPowerBIMigrator(config)
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            return {}
        
        # Set output path
        if not output_base_path:
            output_base_path = config.output_directory
        
        # Perform migrations
        logger.info(f"Starting migration of {len(report_ids)} reports")
        results = migrator.migrate_multiple_reports(report_ids, output_base_path)
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"Migration completed: {successful}/{total} reports successful")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during batch migration: {e}")
        return {}


def migrate_folder(folder_id: str, output_path: Optional[str] = None, recursive: bool = True):
    """Migrate all reports in a Cognos folder"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize migrator
        migrator = CognosToPowerBIMigrator(config)
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            return {}
        
        # Set output path
        if not output_path:
            output_path = Path(config.output_directory) / f"folder_{folder_id}"
        
        # Perform migration
        logger.info(f"Starting migration of folder: {folder_id}")
        results = migrator.migrate_folder(folder_id, str(output_path), recursive)
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"Folder migration completed: {successful}/{total} reports successful")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during folder migration: {e}")
        return {}


def create_and_execute_migration_plan(source_config: dict, output_path: Optional[str] = None):
    """Create and execute a migration plan"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize migrator and batch processor
        migrator = CognosToPowerBIMigrator(config)
        batch_processor = MigrationBatch(migrator)
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            return {}
        
        # Set output path
        if not output_path:
            output_path = config.output_directory
        
        # Create migration plan
        logger.info("Creating migration plan...")
        plan = batch_processor.create_migration_plan(source_config)
        
        logger.info(f"Migration plan created:")
        logger.info(f"  - Plan ID: {plan['migration_id']}")
        logger.info(f"  - Total reports: {len(plan['reports'])}")
        logger.info(f"  - Estimated duration: {plan['estimated_duration']}")
        
        # Execute migration plan
        logger.info("Executing migration plan...")
        results = batch_processor.execute_migration_plan(plan, output_path)
        
        logger.info(f"Migration plan execution completed:")
        logger.info(f"  - Successful: {results['successful']}")
        logger.info(f"  - Failed: {results['failed']}")
        logger.info(f"  - Success rate: {(results['successful']/results['total_reports']*100):.1f}%")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during planned migration: {e}")
        return {}


def demo_migration():
    """Demonstrate migration capabilities with sample data"""
    logger = logging.getLogger(__name__)
    
    logger.info("=== Cognos to Power BI Migration Demo ===")
    
    # Example 1: Single report migration
    logger.info("\n1. Single Report Migration Example")
    logger.info("This would migrate a single report with ID 'sample_report_1'")
    # Uncomment to run actual migration:
    # migrate_single_report('sample_report_1')
    
    # Example 2: Multiple reports migration
    logger.info("\n2. Multiple Reports Migration Example")
    sample_report_ids = ['report_1', 'report_2', 'report_3']
    logger.info(f"This would migrate reports: {sample_report_ids}")
    # Uncomment to run actual migration:
    # migrate_multiple_reports(sample_report_ids)
    
    # Example 3: Folder migration
    logger.info("\n3. Folder Migration Example")
    logger.info("This would migrate all reports in folder 'sample_folder_id'")
    # Uncomment to run actual migration:
    # migrate_folder('sample_folder_id')
    
    # Example 4: Planned migration
    logger.info("\n4. Planned Migration Example")
    sample_plan_config = {
        'report_ids': ['report_1', 'report_2'],
        'folder_ids': ['folder_1']
    }
    logger.info(f"This would execute a migration plan with config: {sample_plan_config}")
    # Uncomment to run actual migration:
    # create_and_execute_migration_plan(sample_plan_config)
    
    logger.info("\n=== Demo completed ===")
    logger.info("To run actual migrations, uncomment the relevant function calls above")
    logger.info("and ensure your .env file contains valid Cognos Analytics credentials")


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check if we have command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'demo':
            demo_migration()
        
        elif command == 'migrate-report' and len(sys.argv) > 2:
            report_id = sys.argv[2]
            output_path = sys.argv[3] if len(sys.argv) > 3 else None
            migrate_single_report(report_id, output_path)
        
        elif command == 'migrate-folder' and len(sys.argv) > 2:
            folder_id = sys.argv[2]
            output_path = sys.argv[3] if len(sys.argv) > 3 else None
            recursive = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
            migrate_folder(folder_id, output_path, recursive)
        
        elif command == 'validate':
            config = load_config()
            migrator = CognosToPowerBIMigrator(config)
            if migrator.validate_migration_prerequisites():
                logger.info("✓ All prerequisites validated successfully")
            else:
                logger.error("✗ Prerequisites validation failed")
        
        else:
            print("Usage:")
            print("  python main.py demo                                    # Run demonstration")
            print("  python main.py migrate-report <report_id> [output]    # Migrate single report")
            print("  python main.py migrate-folder <folder_id> [output]    # Migrate folder")
            print("  python main.py validate                               # Validate prerequisites")
    
    else:
        # Run demo by default
        demo_migration()


if __name__ == "__main__":
    main()
