#!/usr/bin/env python3
"""
Test script to trace M-query flow through the migration process.
This script will run a package migration and analyze the logs to identify
where the M-query is being simplified.
"""

import os
import sys
import logging
import json
import tempfile
import datetime
from pathlib import Path

# Import the package migration function directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cognos_migrator.migrations.package import migrate_package_with_explicit_session
from cognos_migrator.common.logging import configure_logging

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Generate a timestamp for the log file
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"mquery_tracking_{timestamp}.log"

# Configure logging with both file and console output
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configure the cognos_migrator logger to also write to our file
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    if isinstance(handler, logging.FileHandler):
        # Add this handler to the cognos_migrator logger
        cognos_logger = logging.getLogger("cognos_migrator")
        cognos_logger.addHandler(handler)

logger = logging.getLogger("mquery_tracer")
logger.info(f"Logging to file: {log_file}")

def main():
    """Run a test migration and analyze the logs"""
    logger.info("Starting M-query flow test")
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Look for test data
    test_data_dir = project_root / "test_data"
    if test_data_dir.exists():
        logger.info(f"Using test data directory: {test_data_dir}")
    else:
        # Create a test directory if it doesn't exist
        test_data_dir = project_root / "test_data"
        test_data_dir.mkdir(exist_ok=True)
        logger.info(f"Created test data directory: {test_data_dir}")
    
    # Output directory for the migration
    output_dir = project_root / "output" / "mquery_test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output will be saved to: {output_dir}")
    
    # Create a simple test package file if needed
    # This is a placeholder - in a real scenario, you would use an actual package file
    test_package_file = test_data_dir / "test_package.xml"
    
    # Check if we have a real sample package file to use
    sample_dir = project_root / "samples"
    if sample_dir.exists():
        sample_files = list(sample_dir.glob("**/*.xml"))
        if sample_files:
            test_package_file = sample_files[0]
            logger.info(f"Using existing sample package file: {test_package_file}")
    
    # If no sample file exists, create a minimal test file
    if not test_package_file.exists():
        with open(test_package_file, "w") as f:
            f.write("<package><name>TestPackage</name></package>")
        logger.info(f"Created minimal test package file: {test_package_file}")
    
    # Run the package migration with our enhanced logging
    logger.info("Running package migration with enhanced M-query logging")
    
    # Mock Cognos credentials for testing
    # In a real scenario, these would be actual valid credentials
    cognos_url = "http://localhost:8080"
    session_key = "test-session-key"
    
    try:
        # Call the migration function directly
        success = migrate_package_with_explicit_session(
            package_file_path=str(test_package_file),
            output_path=str(output_dir),
            cognos_url=cognos_url,
            session_key=session_key
        )
        
        if success:
            logger.info("Package migration completed successfully")
        else:
            logger.error("Package migration failed")
            return
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return
    
    # Analyze the logs for M-query tracking
    analyze_logs("mquery_trace.log")

def analyze_logs(log_file):
    """Analyze the logs to trace M-query flow"""
    logger.info(f"Analyzing logs from {log_file}")
    
    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return
    
    # Read the log file
    with open(log_file, 'r') as f:
        log_lines = f.readlines()
    
    # Extract M-query tracking logs
    mquery_logs = [line for line in log_lines if "[MQUERY_TRACKING]" in line]
    
    if not mquery_logs:
        logger.error("No M-query tracking logs found")
        return
    
    logger.info(f"Found {len(mquery_logs)} M-query tracking log entries")
    
    # Group logs by table name
    table_logs = {}
    current_table = None
    
    for line in mquery_logs:
        if "table:" in line:
            # Extract table name
            table_start = line.find("table:") + 7
            table_end = line.find(" ", table_start)
            if table_end == -1:
                table_end = len(line)
            current_table = line[table_start:table_end].strip()
            
            if current_table not in table_logs:
                table_logs[current_table] = []
        
        if current_table:
            table_logs[current_table].append(line)
    
    # Analyze each table's M-query flow
    for table_name, logs in table_logs.items():
        logger.info(f"\n\n=== M-query flow for table {table_name} ===")
        
        # Extract key points in the flow
        source_query = None
        llm_generated = None
        cleaned_query = None
        final_query = None
        
        for log in logs:
            if "source_query:" in log:
                source_query = log
            elif "LLM service generated M-query" in log:
                llm_generated = log
            elif "Cleaned M-query" in log:
                cleaned_query = log
            elif "M-query being written to TMDL" in log:
                final_query = log
        
        # Print the flow
        logger.info("SOURCE QUERY:")
        logger.info(source_query if source_query else "Not found")
        
        logger.info("\nLLM GENERATED M-QUERY:")
        logger.info(llm_generated if llm_generated else "Not found")
        
        logger.info("\nCLEANED M-QUERY:")
        logger.info(cleaned_query if cleaned_query else "Not found")
        
        logger.info("\nFINAL M-QUERY IN TMDL:")
        logger.info(final_query if final_query else "Not found")
        
        # Analyze differences
        if llm_generated and final_query and "Select *" in final_query and "Select *" not in llm_generated:
            logger.info("\nDISCREPANCY DETECTED: LLM generated a detailed query but a simplified 'Select *' query was used in the TMDL file")
            
            # Try to identify where the simplification occurred
            if cleaned_query and "Select *" in cleaned_query and "Select *" not in llm_generated:
                logger.info("Simplification occurred during the cleaning process in MQueryConverter._clean_m_query()")
            elif final_query and "Select *" in final_query and (cleaned_query and "Select *" not in cleaned_query):
                logger.info("Simplification occurred after cleaning, possibly during template rendering or context building")

if __name__ == "__main__":
    main()
