"""
Example usage of the enhanced migration system
"""

import os
import logging
from pathlib import Path

from cognos_migrator.enhanced_migration_orchestrator import EnhancedMigrationOrchestrator
from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.models import Table, Column, DataType


def setup_logging():
    """Setup logging for the example"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def create_sample_table():
    """Create a sample table for testing"""
    columns = [
        Column(name="CustomerID", data_type=DataType.INTEGER),
        Column(name="CustomerName", data_type=DataType.STRING),
        Column(name="Revenue", data_type=DataType.DECIMAL),
        Column(name="OrderDate", data_type=DataType.DATETIME)
    ]
    
    table = Table(name="Sales", columns=columns)
    table.source_query = "SELECT * FROM Sales WHERE Revenue > 1000"
    
    return table


def example_basic_usage():
    """Example of basic enhanced migration usage"""
    logger = setup_logging()
    logger.info("Starting basic enhanced migration example")
    
    # Initialize orchestrator
    orchestrator = EnhancedMigrationOrchestrator(logger=logger)
    
    # Start migration
    orchestrator.start_migration()
    
    # Example expressions to convert
    expressions = [
        "total([Revenue])",
        "if ([Revenue] > 1000) then ([Revenue] * 0.1) else (0)",
        "count_distinct([CustomerID])",
        "runningSum([Revenue])",
        "[Revenue] / [Quantity]"  # This might fail validation
    ]
    
    # Convert expressions
    logger.info("Converting expressions with validation and fallback...")
    results = []
    for expr in expressions:
        result = orchestrator.migrate_expression(
            cognos_formula=expr,
            table_name="Sales",
            column_name="CalculatedField",
            available_columns=["CustomerID", "CustomerName", "Revenue", "OrderDate", "Quantity"]
        )
        results.append(result)
        logger.info(f"Expression: {expr[:30]}... -> Strategy: {result.get('strategy_used', 'Unknown')}")
    
    # Convert M-Query
    table = create_sample_table()
    mquery = orchestrator.migrate_table_mquery(table)
    logger.info(f"Generated M-Query length: {len(mquery)} characters")
    
    # Complete migration and generate reports
    output_dir = "./enhanced_migration_output"
    Path(output_dir).mkdir(exist_ok=True)
    
    summary = orchestrator.complete_migration(output_dir)
    logger.info(f"Migration completed. Reports saved to: {output_dir}")
    
    return summary


def example_with_configuration():
    """Example using custom configuration"""
    logger = setup_logging()
    logger.info("Starting enhanced migration with custom configuration")
    
    # Create sample configuration file
    config_path = "./sample_migration_config.json"
    orchestrator = EnhancedMigrationOrchestrator(logger=logger)
    orchestrator.create_sample_config(config_path)
    logger.info(f"Sample configuration created at: {config_path}")
    
    # Initialize with configuration
    orchestrator = EnhancedMigrationOrchestrator(
        config_file_path=config_path,
        logger=logger
    )
    
    # Show configuration summary
    config_summary = orchestrator.get_configuration_summary()
    logger.info(f"Configuration loaded: {config_summary['validation']['validation_level']}")
    
    # Validate configuration
    issues = orchestrator.validate_configuration()
    if issues:
        logger.warning(f"Configuration issues: {issues}")
    else:
        logger.info("Configuration validation passed")
    
    return config_summary


def example_with_llm_service():
    """Example with LLM service integration"""
    logger = setup_logging()
    
    # Initialize LLM service (requires API key)
    llm_client = None
    if os.getenv('DAX_API_URL'):
        llm_client = LLMServiceClient(base_url=os.getenv('DAX_API_URL'))
        logger.info("LLM service client initialized")
    else:
        logger.info("No LLM service configured, using fallback mode")
    
    # Initialize orchestrator with LLM service
    orchestrator = EnhancedMigrationOrchestrator(
        llm_service_client=llm_client,
        logger=logger
    )
    
    orchestrator.start_migration()
    
    # Test complex expression that would benefit from LLM
    complex_expr = """
    case 
        when [Region] = 'North' and [Revenue] > 10000 then [Revenue] * 0.15
        when [Region] = 'South' and [Revenue] > 5000 then [Revenue] * 0.12
        else [Revenue] * 0.10
    end
    """
    
    result = orchestrator.migrate_expression(
        cognos_formula=complex_expr,
        table_name="RegionalSales",
        column_name="Commission",
        available_columns=["Region", "Revenue", "CustomerID"]
    )
    
    logger.info(f"Complex expression conversion:")
    logger.info(f"  Strategy: {result.get('strategy_used')}")
    logger.info(f"  Confidence: {result.get('confidence', 0):.2f}")
    logger.info(f"  Fallback Applied: {result.get('fallback_applied', False)}")
    logger.info(f"  Requires Review: {result.get('requires_review', False)}")
    
    return result


def example_environment_configuration():
    """Example using environment variable configuration"""
    logger = setup_logging()
    
    # Set environment variables for configuration
    os.environ.update({
        'VALIDATION_LEVEL': 'strict',
        'FALLBACK_MODE': 'comprehensive',
        'CONFIDENCE_THRESHOLD': '0.8',
        'ENABLE_SELECT_ALL_FALLBACK': 'true',
        'QUERY_FOLDING_PREFERENCE': 'Strict',
        'GENERATE_REPORTS': 'true',
        'REPORT_OUTPUT_FORMATS': 'json,html,markdown'
    })
    
    # Initialize orchestrator (will use environment config)
    orchestrator = EnhancedMigrationOrchestrator(logger=logger)
    
    config_summary = orchestrator.get_configuration_summary()
    logger.info("Configuration from environment variables:")
    for section, settings in config_summary.items():
        logger.info(f"  {section}: {settings}")
    
    return config_summary


def main():
    """Run all examples"""
    print("🚀 Enhanced Cognos Migration Examples")
    print("=" * 50)
    
    try:
        print("\n1. Basic Usage Example")
        print("-" * 30)
        basic_result = example_basic_usage()
        print(f"✅ Basic example completed: {len(basic_result.get('report_files', {}))} reports generated")
        
        print("\n2. Configuration File Example")
        print("-" * 30)
        config_result = example_with_configuration()
        print(f"✅ Configuration example completed")
        
        print("\n3. Environment Configuration Example")
        print("-" * 30)
        env_result = example_environment_configuration()
        print(f"✅ Environment configuration example completed")
        
        print("\n4. LLM Service Integration Example")
        print("-" * 30)
        llm_result = example_with_llm_service()
        print(f"✅ LLM integration example completed")
        
        print(f"\n🎉 All examples completed successfully!")
        print(f"Check the './enhanced_migration_output' directory for generated reports.")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()