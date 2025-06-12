#!/usr/bin/env python3
"""
Test migration with LLM service integration
This script tests the integration of the LLM service during the migration process
"""

import sys
import os
import logging
from pathlib import Path

# Add the cognos_migrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cognos_migrator'))

from cognos_migrator.config import ConfigManager, MigrationConfig
# Import directly from the module that has the LLM integration
import cognos_migrator.generators as generators_module
from cognos_migrator.models import DataModel, Table, Column, DataType
from cognos_migrator.llm_service import LLMServiceClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to DEBUG level
logging.getLogger('cognos_migrator.llm_service').setLevel(logging.DEBUG)
logging.getLogger('cognos_migrator.generators').setLevel(logging.DEBUG)

def test_llm_integration():
    """Test LLM service integration during migration"""
    print("🔍 TESTING LLM SERVICE INTEGRATION DURING MIGRATION")
    print("=" * 80)
    
    # Create a custom configuration with LLM service enabled
    config = MigrationConfig(
        output_directory="output/llm_test",
        template_directory="cognos_migrator/templates",
        llm_service_enabled=True,
        llm_service_url="http://localhost:8080"
    )
    
    print(f"📋 Configuration:")
    print(f"   LLM Service Enabled: {config.llm_service_enabled}")
    print(f"   LLM Service URL: {config.llm_service_url}")
    
    # Create a simple data model with a table that has a source query
    print(f"\n📊 Creating test data model...")
    
    # Create a table with a source query that should trigger LLM service
    customer_table = Table(
        name="Customer",
        columns=[
            Column(name="CustomerID", data_type=DataType.INTEGER, source_column="customer_id"),
            Column(name="Name", data_type=DataType.STRING, source_column="customer_name"),
            Column(name="Email", data_type=DataType.STRING, source_column="email"),
            Column(name="Age", data_type=DataType.INTEGER, source_column="age")
        ],
        source_query="SELECT customer_id, customer_name, email, age FROM customers WHERE age > 18"
    )
    
    # Create the data model with the table
    data_model = DataModel(name="Test Model", tables=[customer_table])
    
    # Initialize the PowerBI project generator
    print(f"\n🛠️  Initializing PowerBI project generator...")
    # Use the PowerBIProjectGenerator class directly from the generators module
    generator = generators_module.PowerBIProjectGenerator(config)
    
    # Check if LLM service was initialized
    # The llm_service attribute should be set in the __init__ method
    print(f"   Config has llm_service_enabled: {hasattr(config, 'llm_service_enabled') and config.llm_service_enabled}")
    
    # Check if the generator has the llm_service attribute
    has_llm_service = hasattr(generator, 'llm_service')
    print(f"   Generator has llm_service attribute: {has_llm_service}")
    
    # Check if the llm_service is initialized (not None)
    if has_llm_service:
        print(f"   LLM Service initialized: {generator.llm_service is not None}")
    else:
        print(f"   ❌ Generator does not have llm_service attribute!")
        # Let's check the class definition
        import inspect
        print(f"   PowerBIProjectGenerator class definition:")
        print(inspect.getsource(PowerBIProjectGenerator.__init__)[:200] + "...")
        return
    
    if generator.llm_service:
        # Check LLM service health
        print(f"\n🔍 Checking LLM service health...")
        health_status = generator.llm_service.check_health()
        print(f"   Health status: {health_status}")
        
        # Generate M-query for the table
        print(f"\n🔍 Generating M-query for Customer table...")
        m_query = generator._build_m_expression(customer_table)
        print(f"\n📝 Generated M-query:")
        print("-" * 80)
        print(m_query)
        print("-" * 80)
        
        # Generate the project
        output_path = Path(config.output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🏗️  Generating Power BI project...")
        success = generator.generate_project(
            project=data_model.to_power_bi_project(),
            output_path=str(output_path)
        )
        
        if success:
            print(f"   ✅ PROJECT GENERATION SUCCESSFUL!")
        else:
            print(f"   ❌ PROJECT GENERATION FAILED!")
    else:
        print(f"   ❌ LLM SERVICE NOT INITIALIZED!")
        print(f"   Check configuration and LLM service availability")

if __name__ == "__main__":
    test_llm_integration()
