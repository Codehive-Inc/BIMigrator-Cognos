"""
Main entry point for Cognos to Power BI migration tool
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from bimigrator.common.websocket_client import logging_helper, set_task_info
from .config import ConfigManager
from .migrator import CognosToPowerBIMigrator, MigrationBatch


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
    return config_manager.get_migration_config()


def list_available_content():
    """List available reports and folders for migration"""
    print("🔍 DISCOVERING AVAILABLE CONTENT")
    print("=" * 50)

    try:
        from cognos_migrator.client import CognosClient

        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()

        print(f"Connecting to: {cognos_config.base_url}")
        client = CognosClient(cognos_config)

        if not client.test_connection():
            print("❌ Cannot connect to Cognos server")
            print("💡 Check your .env configuration")
            return False

        print("✅ Connected successfully!")
        print()

        # Get root content
        root_objects = client.list_root_objects()

        reports = []
        folders = []

        print("📋 Available Content:")
        print()

        for obj in root_objects:
            obj_type = obj.get('type', 'unknown')
            obj_id = obj.get('id', '')
            obj_name = obj.get('defaultName', 'Unknown')

            if obj_type == 'report':
                reports.append((obj_id, obj_name))
                print(f"📊 REPORT: {obj_name}")
                print(f"   ID: {obj_id}")
                print(f"   Command: python main.py migrate-report {obj_id}")
                print()

            elif obj_type == 'folder':
                folders.append((obj_id, obj_name))
                print(f"📁 FOLDER: {obj_name}")
                print(f"   ID: {obj_id}")
                print(f"   Command: python main.py migrate-folder {obj_id}")

                # Check folder contents
                try:
                    folder_items = client.list_child_objects(obj_id)
                    folder_reports = [item for item in folder_items if item.get('type') == 'report']
                    if folder_reports:
                        print(f"   📊 Contains {len(folder_reports)} reports:")
                        for item in folder_reports[:3]:  # Show first 3
                            item_name = item.get('defaultName', 'Unknown')
                            item_id = item.get('id', '')
                            reports.append((item_id, item_name))
                            print(f"      - {item_name} (ID: {item_id})")
                        if len(folder_reports) > 3:
                            print(f"      ... and {len(folder_reports) - 3} more")
                except:
                    print(f"   (Could not access folder contents)")
                print()

        # Summary
        print("=" * 50)
        print(f"📊 SUMMARY: Found {len(reports)} reports and {len(folders)} folders")

        if reports:
            print(f"\n💡 To test migration, try:")
            print(f"   python main.py migrate-report {reports[0][0]}")

        if folders:
            print(f"   python main.py migrate-folder {folders[0][0]}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# here is migrate single report method that takes session_key as an argument besides report_id and output_path.
# This is useful when you want to migrate a report by passing user credentials and main key.
def migrate_single_report_with_session_key(report_id: str, cognos_url: str, session_key: str,
                                           output_path: Optional[str] = None):
    """Migrate a single Cognos report using session key"""
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = load_config()

        # Create client with existing session
        migrator = CognosToPowerBIMigrator(config, base_url=cognos_url, session_key=session_key)

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

def migrate_module_with_session_key(module_id: str, cognos_url: str, session_key: str, 
                                   folder_id: str, output_path: Optional[str] = None):
    """Migrate a Cognos module using session key
    
    Args:
        module_id: ID of the Cognos module to migrate
        cognos_url: Base URL of the Cognos server
        session_key: Authentication session key
        folder_id: ID of the folder containing reports to migrate
        output_path: Optional path to store migration output
    
    Returns:
        Dict[str, bool]: Results of the migration process
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create client with existing session
        # set_task_info(task_name="Module Migration with Session", 
        #               task_description=f"Migrating module {module_id} with folder {folder_id}")
        logging_helper(message="Initializing Cognos to Power BI migration with session key", 
                       progress=0, 
                       message_type="info")
        migrator = CognosToPowerBIMigrator(config, base_url=cognos_url, session_key=session_key)
        logging_helper(message="Initialization complete!", 
                       progress=10,
                       message_type="info")
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            logging_helper(message="Migration prerequisites not met. Please check configuration.", 
                           progress=10,
                           message_type="error")
            return {}
        
        # Set output path
        if not output_path:
            output_path = Path(config.output_directory) / f"module_{module_id}"
        
        # Perform module migration
        logger.info(f"Starting migration of module: {module_id} with folder: {folder_id}")
        results = migrator.migrate_module(module_id, folder_id, str(output_path))
        
        if results:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            logger.info(f"✓ Module migration completed: {successful}/{total} reports successful")
            
            # Show migration status
            status = migrator.get_migration_status(str(output_path))
            logger.info(f"Migration status: {status}")
        else:
            logger.error(f"✗ Failed to migrate module {module_id}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during module migration: {e}")
        logging_helper(message=f"Error during module migration: {e}", 
                       progress=100,
                       message_type="error")
        return {}

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
        logger.info(f"  - Success rate: {(results['successful'] / results['total_reports'] * 100):.1f}%")

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


def migrate_module(module_id: str, folder_id: str, output_path: Optional[str] = None):
    """Migrate a Cognos module and associated folder
    
    This function performs a three-step migration process:
    1. Module-based implementation - Extracts module metadata and structure
    2. Folder-based execution - Migrates all reports in the specified folder
    3. Post-processing - Enhances the generated files with module-specific information
    
    Args:
        module_id: ID of the Cognos module to migrate
        folder_id: ID of the folder containing reports to migrate
        output_path: Optional path to store migration output
    
    Returns:
        Dict[str, bool]: Results of the migration process
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize migrator
        # set_task_info(task_name="Module Migration", task_description=f"Migrating module {module_id} with folder {folder_id}")
        logging_helper(message="Initializing Cognos to Power BI migration", 
                       progress=0, 
                       message_type="info")
        migrator = CognosToPowerBIMigrator(config)
        logging_helper(message="Initialization complete!", 
                       progress=10,
                       message_type="info")
        
        # Validate prerequisites
        if not migrator.validate_migration_prerequisites():
            logger.error("Migration prerequisites not met. Please check configuration.")
            logging_helper(message="Migration prerequisites not met. Please check configuration.", 
                       progress=10,
                       message_type="error")
            return {}
        
        # Delegate to the migrator's migrate_module method
        return migrator.migrate_module(module_id, folder_id, output_path)
        
    except Exception as e:
        logger.error(f"Error during module migration: {e}")
        return {}


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
            
        elif command == 'migrate-module' and len(sys.argv) > 3:
            module_id = sys.argv[2]
            folder_id = sys.argv[3]
            output_path = sys.argv[4] if len(sys.argv) > 4 else None
            migrate_module(module_id, folder_id, output_path)

        elif command == 'validate':
            config = load_config()
            migrator = CognosToPowerBIMigrator(config)
            if migrator.validate_migration_prerequisites():
                logger.info("✓ All prerequisites validated successfully")
            else:
                logger.error("✗ Prerequisites validation failed")

        elif command == 'list':
            list_available_content()

        else:
            print("Usage:")
            print("  python main.py demo                                    # Run demonstration")
            print("  python main.py list                                    # List available reports and folders")
            print("  python main.py migrate-report <report_id> [output]    # Migrate single report")
            print("  python main.py migrate-folder <folder_id> [output]    # Migrate folder")
            print("  python main.py migrate-module <module_id> <folder_id> [output]  # Migrate module and folder")
            print("  python main.py validate                               # Validate prerequisites")

    else:
        folder_id = "i6765AFC28C0C471082E951F89A28C230"
        output_path = None
        recursive = True
        # migrate_folder(folder_id, output_path, recursive)
        # Run demo by default
        # demo_migration()
        report_id = "i8E32D9D255FA4361A2D8BDF980837E3D"
        cognos_url = "http://20.244.32.126:9300/api/v1"
        session_key = "CAM MTsxMDE6NzhmNDVlZjQtMTMzMS0zMmU3LTVhZWUtMmY3NzEyNzNiOWU1OjA5ODQ1OTI1MDc7MDszOzA7"
        migrate_single_report_with_session_key(report_id, cognos_url, session_key, output_path)


if __name__ == "__main__":
    main()
