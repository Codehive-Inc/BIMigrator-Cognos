#!/usr/bin/env python
"""
Test script for LLM service integration
"""

import logging
import json
import requests
from cognos_migrator.llm_service import LLMServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_llm_service():
    """Test the LLM service client with a sample table"""
    
    # Create context for LLM service directly
    context = {
        'table_name': "Customers",
        'columns': [
            {'name': "CustomerID", 'data_type': "STRING"},
            {'name': "FirstName", 'data_type': "STRING"},
            {'name': "LastName", 'data_type': "STRING"},
            {'name': "Email", 'data_type': "STRING"},
            {'name': "Age", 'data_type': "INTEGER"},
            {'name': "RegistrationDate", 'data_type': "DATETIME"}
        ],
        'source_query': "SELECT * FROM Customers WHERE Age > 18",
        'report_spec': "<sample>This is a sample report specification</sample>"
    }
    
    # Test 1: Using the LLMServiceClient
    logger.info("Test 1: Using LLMServiceClient class")
    try:
        # Initialize LLM service client
        llm_client = LLMServiceClient(base_url="http://localhost:8080")
        
        # Test with debug logging
        logger.info(f"Context: {json.dumps(context, indent=2)}")
        
        # Generate M-query
        m_query = llm_client.generate_m_query(context)
        logger.info(f"Generated M-query: {m_query}")
    except Exception as e:
        logger.error(f"Error using LLMServiceClient: {e}")
    
    # Test 2: Check available endpoints
    logger.info("\nTest 2: Check available endpoints")
    try:
        # Make GET request to root endpoint to see available endpoints
        logger.info("Checking available endpoints at http://localhost:8080")
        response = requests.get(
            "http://localhost:8080",
            timeout=10
        )
        
        logger.info(f"Response status: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Root endpoint response: {response.text[:500]}...")
        else:
            logger.error(f"Error response: {response.text}")
        
        # Check docs endpoint
        logger.info("\nChecking docs endpoint at http://localhost:8080/docs")
        response = requests.get(
            "http://localhost:8080/docs",
            timeout=10
        )
        
        logger.info(f"Docs endpoint status: {response.status_code}")
        
        # Try the new /api/m-query endpoint
        logger.info("\nTrying the new /api/m-query endpoint")
        payload = {
            'context': context,
            'options': {
                'optimize_for_performance': True,
                'include_comments': True
            }
        }
        
        # Try /api/m-query endpoint
        logger.info("Making request to http://localhost:8080/api/m-query")
        response = requests.post(
            "http://localhost:8080/api/m-query",
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=10
        )
        
        logger.info(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            logger.error(f"Error response: {response.text}")
            return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.info("The FastAPI service might not be running at http://localhost:8080")
        return False
    except Exception as e:
        logger.error(f"Error making direct request: {e}")
        return False

if __name__ == "__main__":
    print("Testing LLM service integration...")
    success = test_llm_service()
    if success:
        print("✅ LLM service test completed successfully")
    else:
        print("❌ LLM service test failed")
