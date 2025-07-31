"""
Enhanced migration orchestrator with validation and fallback strategies

This module extends the existing main.py with advanced validation capabilities
to ensure 100% error-free PBIT generation.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.config.fallback_config import EnhancedMigrationConfig, ConfigurationManager
from cognos_migrator.strategies.fallback_strategy import FallbackStrategy
from cognos_migrator.validators import ExpressionValidator, MQueryValidator, FallbackValidator
from cognos_migrator.reporting.migration_reporter import MigrationReporter
from cognos_migrator.enhanced_migration_orchestrator import EnhancedMigrationOrchestrator
from .client import CognosClient, CognosAPIError
from .common.websocket_client import logging_helper, set_task_info

__all__ = [
    'test_cognos_connection_enhanced',
    'migrate_module_with_enhanced_validation',
    'migrate_single_report_with_enhanced_validation',
    'post_process_module_with_enhanced_validation'
]


def test_cognos_connection_enhanced(cognos_url: str, session_key: str, 
                                  enable_validation: bool = True) -> Dict[str, Any]:
    """Enhanced connection test with validation capability reporting
    
    Args:
        cognos_url: The Cognos base URL
        session_key: The session key to test
        enable_validation: Whether to test validation components
        
    Returns:
        Dict containing connection status and validation component status
    """
    result = {
        'connection_valid': False,
        'validation_framework_available': False,
        'fallback_strategy_available': False,
        'reporters_available': False,
        'enhanced_converters_available': False,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Test basic connection
        result['connection_valid'] = CognosClient.test_connection_with_session(cognos_url, session_key)
        
        if enable_validation:
            # Test validation components
            try:
                validator = ExpressionValidator()
                mquery_validator = MQueryValidator()
                fallback_validator = FallbackValidator()
                result['validation_framework_available'] = True
            except Exception as e:
                logging.warning(f"Validation framework not available: {e}")
            
            # Test fallback strategy
            try:
                strategy = FallbackStrategy()
                result['fallback_strategy_available'] = True
            except Exception as e:
                logging.warning(f"Fallback strategy not available: {e}")
            
            # Test reporting
            try:
                reporter = MigrationReporter()
                result['reporters_available'] = True
            except Exception as e:
                logging.warning(f"Reporting framework not available: {e}")
            
            # Test enhanced converters
            try:
                from cognos_migrator.converters.enhanced_expression_converter import EnhancedExpressionConverter
                from cognos_migrator.converters.enhanced_mquery_converter import EnhancedMQueryConverter
                result['enhanced_converters_available'] = True
            except Exception as e:
                logging.warning(f"Enhanced converters not available: {e}")
        
        return result
        
    except Exception as e:
        result['error'] = str(e)
        return result


def migrate_module_with_enhanced_validation(module_id: str,
                                          output_path: str,
                                          cognos_url: str, session_key: str,
                                          folder_id: str = None,
                                          cpf_file_path: str = None,
                                          task_id: Optional[str] = None,
                                          auth_key: str = "IBM-BA-Authorization",
                                          enable_enhanced_validation: bool = True,
                                          validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Enhanced module migration with validation and fallback strategies
    
    Args:
        module_id: ID of the Cognos module to migrate
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        folder_id: Optional folder ID containing reports to migrate
        cpf_file_path: Optional path to CPF file for enhanced metadata
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        enable_enhanced_validation: Whether to use enhanced validation (default: True)
        validation_config: Optional validation configuration override
        
    Returns:
        Dict containing migration results, validation reports, and statistics
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"enhanced_migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with enhanced steps (18 steps total)
    set_task_info(task_id, total_steps=18)
    
    # First verify the session is valid
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        raise CognosAPIError("Session key is expired or invalid")
    
    logger = logging.getLogger(__name__)
    
    logging_helper(
        message=f"Starting enhanced migration for module: {module_id}",
        progress=0,
        message_type="info"
    )
    
    try:
        # Initialize enhanced configuration
        logging_helper(
            message="Initializing enhanced migration configuration",
            progress=5,
            message_type="info"
        )
        
        if enable_enhanced_validation:
            # Create enhanced configuration
            config_manager = ConfigurationManager()
            if validation_config:
                config_manager.update_config(validation_config)
            
            enhanced_config = config_manager.get_current_config()
            
            # Override basic settings with enhanced ones
            migration_config = MigrationConfig(
                output_directory=output_path,
                preserve_structure=enhanced_config.preserve_structure,
                include_metadata=enhanced_config.include_metadata,
                generate_documentation=enhanced_config.generate_documentation,
                template_directory=str(Path(__file__).parent / "templates"),
                llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
                llm_service_enabled=enhanced_config.llm_service_enabled
            )
        else:
            # Use standard configuration
            migration_config = MigrationConfig(
                output_directory=output_path,
                preserve_structure=True,
                include_metadata=True,
                generate_documentation=True,
                template_directory=str(Path(__file__).parent / "templates"),
                llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
                llm_service_enabled=True
            )
        
        # Create Cognos config
        cognos_config = CognosConfig(
            base_url=cognos_url,
            auth_key=auth_key,
            auth_value=session_key,
            session_timeout=3600,
            max_retries=3,
            request_timeout=30
        )
        
        logging_helper(
            message="Configuration initialized successfully",
            progress=10,
            message_type="info"
        )
        
        if enable_enhanced_validation:
            # Use enhanced migration orchestrator
            logging_helper(
                message="Initializing enhanced migration orchestrator with validation",
                progress=15,
                message_type="info"
            )
            
            orchestrator = EnhancedMigrationOrchestrator(
                migration_config=migration_config,
                cognos_config=cognos_config,
                enhanced_config=enhanced_config,
                cognos_url=cognos_url,
                session_key=session_key,
                logger=logger,
                cpf_file_path=cpf_file_path
            )
            
            # Perform enhanced migration
            result = orchestrator.migrate_module_with_validation(
                module_id=module_id,
                output_path=output_path,
                folder_id=folder_id,
                cpf_file_path=cpf_file_path
            )
            
        else:
            # Fall back to standard migration
            logging_helper(
                message="Using standard migration (validation disabled)",
                progress=15,
                message_type="info"
            )
            
            from cognos_migrator.main import migrate_module_with_explicit_session
            success = migrate_module_with_explicit_session(
                module_id=module_id,
                output_path=output_path,
                cognos_url=cognos_url,
                session_key=session_key,
                folder_id=folder_id,
                cpf_file_path=cpf_file_path,
                task_id=task_id,
                auth_key=auth_key
            )
            
            result = {
                'success': success,
                'module_id': module_id,
                'output_path': output_path,
                'migration_type': 'standard',
                'validation_enabled': False,
                'timestamp': datetime.now().isoformat()
            }
        
        # Generate final report
        if result.get('success', False):
            logging_helper(
                message=f"Enhanced migration completed successfully: {module_id}",
                progress=100,
                message_type="info"
            )
        else:
            logging_helper(
                message=f"Enhanced migration failed: {module_id}",
                progress=100,
                message_type="error"
            )
        
        return result
        
    except CognosAPIError as e:
        # Re-raise API errors
        raise e
    except Exception as e:
        logger.error(f"Enhanced migration failed: {e}")
        logging_helper(
            message=f"Enhanced migration failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        return {
            'success': False,
            'error': str(e),
            'module_id': module_id,
            'timestamp': datetime.now().isoformat()
        }


def migrate_single_report_with_enhanced_validation(report_id: str,
                                                 output_path: str,
                                                 cognos_url: str, session_key: str,
                                                 task_id: Optional[str] = None,
                                                 auth_key: str = "IBM-BA-Authorization",
                                                 enable_enhanced_validation: bool = True,
                                                 validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Enhanced report migration with validation and fallback strategies
    
    Args:
        report_id: ID of the Cognos report to migrate
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        enable_enhanced_validation: Whether to use enhanced validation (default: True)
        validation_config: Optional validation configuration override
        
    Returns:
        Dict containing migration results, validation reports, and statistics
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"enhanced_report_migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with enhanced steps (12 steps total)
    set_task_info(task_id, total_steps=12)
    
    # First verify the session is valid
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        raise CognosAPIError("Session key is expired or invalid")
    
    logger = logging.getLogger(__name__)
    
    logging_helper(
        message=f"Starting enhanced report migration: {report_id}",
        progress=0,
        message_type="info"
    )
    
    try:
        if enable_enhanced_validation:
            # Initialize enhanced configuration
            logging_helper(
                message="Initializing enhanced validation for report migration",
                progress=10,
                message_type="info"
            )
            
            config_manager = ConfigurationManager()
            if validation_config:
                config_manager.update_config(validation_config)
            
            enhanced_config = config_manager.get_current_config()
            
            # Create enhanced migration config
            migration_config = MigrationConfig(
                output_directory=output_path,
                preserve_structure=enhanced_config.preserve_structure,
                include_metadata=enhanced_config.include_metadata,
                generate_documentation=enhanced_config.generate_documentation,
                template_directory=str(Path(__file__).parent / "templates"),
                llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
                llm_service_enabled=enhanced_config.llm_service_enabled
            )
            
            # Create Cognos config
            cognos_config = CognosConfig(
                base_url=cognos_url,
                auth_key=auth_key,
                auth_value=session_key,
                session_timeout=3600,
                max_retries=3,
                request_timeout=30
            )
            
            # Use enhanced migration orchestrator for reports
            logging_helper(
                message="Using enhanced orchestrator for report migration",
                progress=20,
                message_type="info"
            )
            
            orchestrator = EnhancedMigrationOrchestrator(
                migration_config=migration_config,
                cognos_config=cognos_config,
                enhanced_config=enhanced_config,
                cognos_url=cognos_url,
                session_key=session_key,
                logger=logger
            )
            
            # Perform enhanced report migration
            result = orchestrator.migrate_report_with_validation(
                report_id=report_id,
                output_path=output_path
            )
            
        else:
            # Fall back to standard report migration
            logging_helper(
                message="Using standard report migration (validation disabled)",
                progress=20,
                message_type="info"
            )
            
            from cognos_migrator.main import migrate_single_report_with_explicit_session
            success = migrate_single_report_with_explicit_session(
                report_id=report_id,
                output_path=output_path,
                cognos_url=cognos_url,
                session_key=session_key,
                task_id=task_id,
                auth_key=auth_key
            )
            
            result = {
                'success': success,
                'report_id': report_id,
                'output_path': output_path,
                'migration_type': 'standard',
                'validation_enabled': False,
                'timestamp': datetime.now().isoformat()
            }
        
        # Final status
        if result.get('success', False):
            logging_helper(
                message=f"Enhanced report migration completed successfully: {report_id}",
                progress=100,
                message_type="info"
            )
        else:
            logging_helper(
                message=f"Enhanced report migration failed: {report_id}",
                progress=100,
                message_type="error"
            )
        
        return result
        
    except CognosAPIError as e:
        # Re-raise API errors
        raise e
    except Exception as e:
        logger.error(f"Enhanced report migration failed: {e}")
        logging_helper(
            message=f"Enhanced report migration failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        return {
            'success': False,
            'error': str(e),
            'report_id': report_id,
            'timestamp': datetime.now().isoformat()
        }


def post_process_module_with_enhanced_validation(module_id: str, output_path: str,
                                               cognos_url: str, session_key: str,
                                               successful_report_ids: List[str] = None,
                                               auth_key: str = "IBM-BA-Authorization",
                                               generate_quality_report: bool = True) -> Dict[str, Any]:
    """Enhanced post-processing with validation quality reports
    
    Args:
        module_id: ID of the Cognos module
        output_path: Path where migration output is stored
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        successful_report_ids: List of successfully migrated report IDs
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        generate_quality_report: Whether to generate enhanced quality reports
        
    Returns:
        Dict containing post-processing results and quality metrics
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    # First verify the session is valid
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        raise CognosAPIError("Session key is expired or invalid")
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting enhanced post-processing for module {module_id}")
        
        logging_helper(
            message=f"Starting enhanced post-processing: {module_id}",
            progress=0,
            message_type="info"
        )
        
        # Perform standard post-processing first
        from cognos_migrator.main import post_process_module_with_explicit_session
        standard_success = post_process_module_with_explicit_session(
            module_id=module_id,
            output_path=output_path,
            cognos_url=cognos_url,
            session_key=session_key,
            successful_report_ids=successful_report_ids,
            auth_key=auth_key
        )
        
        result = {
            'standard_post_processing': standard_success,
            'module_id': module_id,
            'output_path': output_path,
            'timestamp': datetime.now().isoformat()
        }
        
        if generate_quality_report and standard_success:
            # Generate enhanced quality and validation reports
            logging_helper(
                message="Generating enhanced quality reports",
                progress=50,
                message_type="info"
            )
            
            try:
                output_dir = Path(output_path)
                
                # Initialize reporter
                reporter = MigrationReporter(
                    output_directory=str(output_dir),
                    module_id=module_id
                )
                
                # Generate comprehensive reports
                quality_report = reporter.generate_comprehensive_report(
                    migration_data={
                        'module_id': module_id,
                        'successful_reports': successful_report_ids or [],
                        'output_path': output_path
                    }
                )
                
                result['quality_report'] = quality_report
                result['enhanced_reports_generated'] = True
                
                logging_helper(
                    message="Enhanced quality reports generated successfully",
                    progress=80,
                    message_type="info"
                )
                
            except Exception as e:
                logger.warning(f"Failed to generate enhanced quality reports: {e}")
                result['enhanced_reports_generated'] = False
                result['quality_report_error'] = str(e)
        
        # Final status
        overall_success = result.get('standard_post_processing', False)
        
        if overall_success:
            logging_helper(
                message=f"Enhanced post-processing completed successfully: {module_id}",
                progress=100,
                message_type="info"
            )
        else:
            logging_helper(
                message=f"Enhanced post-processing had issues: {module_id}",
                progress=100,
                message_type="warning"
            )
        
        result['success'] = overall_success
        return result
        
    except CognosAPIError as e:
        # Re-raise API errors
        raise e
    except Exception as e:
        logger.error(f"Enhanced post-processing failed: {e}")
        logging_helper(
            message=f"Enhanced post-processing failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        return {
            'success': False,
            'error': str(e),
            'module_id': module_id,
            'timestamp': datetime.now().isoformat()
        }


# Example usage function
def example_enhanced_migration():
    """Example of how to use the enhanced migration functions"""
    
    # Configuration
    cognos_url = "http://your-cognos-server:9300/api/v1"
    session_key = "CAM AWkyOTE4..."
    module_id = "i5F34A7A52E2645C0AB03C34BA50941D7"
    output_path = "./output/enhanced_migration"
    
    # Custom validation configuration
    validation_config = {
        "validation_strictness": "medium",
        "enable_select_star_fallback": True,
        "fallback_threshold": 0.8,
        "generate_detailed_reports": True
    }
    
    try:
        # Test connection with enhanced capabilities
        connection_status = test_cognos_connection_enhanced(
            cognos_url=cognos_url,
            session_key=session_key,
            enable_validation=True
        )
        print("Connection Status:", connection_status)
        
        if connection_status['connection_valid']:
            # Perform enhanced migration
            migration_result = migrate_module_with_enhanced_validation(
                module_id=module_id,
                output_path=output_path,
                cognos_url=cognos_url,
                session_key=session_key,
                enable_enhanced_validation=True,
                validation_config=validation_config
            )
            
            print("Migration Result:", migration_result)
            
            if migration_result['success']:
                # Enhanced post-processing
                post_process_result = post_process_module_with_enhanced_validation(
                    module_id=module_id,
                    output_path=output_path,
                    cognos_url=cognos_url,
                    session_key=session_key,
                    generate_quality_report=True
                )
                
                print("Post-processing Result:", post_process_result)
        
    except CognosAPIError as e:
        print(f"Session error: {e}")
    except Exception as e:
        print(f"Migration error: {e}")


if __name__ == "__main__":
    # Run example if called directly
    example_enhanced_migration()