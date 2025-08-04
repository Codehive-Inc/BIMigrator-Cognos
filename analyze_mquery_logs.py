#!/usr/bin/env python3
"""
Script to analyze existing logs for M-query tracking.
This script will search for [MQUERY_TRACKING] tags in the logs and
trace the M-query flow to identify where discrepancies occur.
"""

import os
import sys
import re
import logging
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mquery_analysis.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("mquery_analyzer")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Analyze logs for M-query tracking")
    parser.add_argument("--log-file", help="Path to the log file to analyze")
    parser.add_argument("--table", help="Filter analysis to a specific table name")
    return parser.parse_args()

def find_latest_log_file():
    """Find the most recent log file in the logs directory"""
    logs_dir = Path(__file__).parent / "logs"
    if not logs_dir.exists():
        logger.error(f"Logs directory not found: {logs_dir}")
        return None
    
    # Find all log files with mquery_tracking in the name
    log_files = list(logs_dir.glob("mquery_tracking_*.log"))
    
    # If no mquery_tracking logs, look for any log files
    if not log_files:
        log_files = list(logs_dir.glob("*.log"))
    
    if not log_files:
        logger.error("No log files found in logs directory")
        return None
    
    # Sort by modification time (most recent first)
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    logger.info(f"Found latest log file: {log_files[0]}")
    return log_files[0]

def extract_mquery_logs(log_file, table_filter=None):
    """Extract M-query tracking logs from the log file"""
    logger.info(f"Extracting M-query tracking logs from {log_file}")
    
    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return []
    
    # Read the log file
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        log_lines = f.readlines()
    
    # Extract M-query tracking logs
    mquery_logs = [line for line in log_lines if "[MQUERY_TRACKING]" in line]
    
    if not mquery_logs:
        logger.error("No M-query tracking logs found")
        return []
    
    logger.info(f"Found {len(mquery_logs)} M-query tracking log entries")
    
    # Filter by table name if specified
    if table_filter:
        filtered_logs = []
        for line in mquery_logs:
            if f"table {table_filter}:" in line or f"table: {table_filter}" in line:
                filtered_logs.append(line)
        
        logger.info(f"Filtered to {len(filtered_logs)} log entries for table {table_filter}")
        return filtered_logs
    
    return mquery_logs

def group_logs_by_table(mquery_logs):
    """Group logs by table name"""
    table_logs = defaultdict(list)
    
    # Regular expression to extract table names
    table_pattern = re.compile(r'table[:]?\s+([^\s:]+)')
    
    for line in mquery_logs:
        match = table_pattern.search(line)
        if match:
            table_name = match.group(1)
            table_logs[table_name].append(line)
        else:
            # Add to "unknown" category if no table name found
            table_logs["unknown"].append(line)
    
    return table_logs

def extract_mquery_content(log_line):
    """Extract M-query content from a log line"""
    # Try to find the M-query content after a colon
    parts = log_line.split(":", 3)  # Split into max 4 parts
    if len(parts) >= 4:
        return parts[3].strip()
    return None

def analyze_table_mquery_flow(table_name, logs):
    """Analyze the M-query flow for a specific table"""
    logger.info(f"\n\n=== M-query flow for table {table_name} ===")
    
    # Categorize logs by phase
    source_query_logs = [log for log in logs if "source_query:" in log]
    llm_generated_logs = [log for log in logs if "LLM service generated M-query" in log]
    raw_mquery_logs = [log for log in logs if "Raw M-query from LLM service" in log]
    cleaned_mquery_logs = [log for log in logs if "Cleaned M-query" in log]
    final_mquery_logs = [log for log in logs if "M-query being written to TMDL" in log]
    
    # Print the flow
    if source_query_logs:
        logger.info("SOURCE QUERY:")
        for log in source_query_logs:
            logger.info(log.strip())
    else:
        logger.info("SOURCE QUERY: Not found in logs")
    
    if llm_generated_logs:
        logger.info("\nLLM GENERATED M-QUERY:")
        for log in llm_generated_logs:
            logger.info(log.strip())
    else:
        logger.info("\nLLM GENERATED M-QUERY: Not found in logs")
    
    if raw_mquery_logs:
        logger.info("\nRAW M-QUERY FROM LLM:")
        for log in raw_mquery_logs:
            logger.info(log.strip())
    else:
        logger.info("\nRAW M-QUERY FROM LLM: Not found in logs")
    
    if cleaned_mquery_logs:
        logger.info("\nCLEANED M-QUERY:")
        for log in cleaned_mquery_logs:
            logger.info(log.strip())
    else:
        logger.info("\nCLEANED M-QUERY: Not found in logs")
    
    if final_mquery_logs:
        logger.info("\nFINAL M-QUERY IN TMDL:")
        for log in final_mquery_logs:
            logger.info(log.strip())
    else:
        logger.info("\nFINAL M-QUERY IN TMDL: Not found in logs")
    
    # Analyze differences
    llm_content = None
    final_content = None
    
    if llm_generated_logs:
        llm_content = extract_mquery_content(llm_generated_logs[-1])
    
    if final_mquery_logs:
        final_content = extract_mquery_content(final_mquery_logs[-1])
    
    if llm_content and final_content and llm_content != final_content:
        logger.info("\nDISCREPANCY DETECTED: The LLM-generated M-query differs from the final M-query in the TMDL file")
        
        # Check for simplification to "Select *"
        if "Select *" in final_content and "Select *" not in llm_content:
            logger.info("The final M-query was simplified to a basic 'Select *' query")
            
            # Try to identify where the simplification occurred
            cleaned_content = None
            if cleaned_mquery_logs:
                cleaned_content = extract_mquery_content(cleaned_mquery_logs[-1])
            
            if cleaned_content and "Select *" in cleaned_content and "Select *" not in llm_content:
                logger.info("Simplification occurred during the cleaning process in MQueryConverter._clean_m_query()")
            elif final_content and "Select *" in final_content and cleaned_content and "Select *" not in cleaned_content:
                logger.info("Simplification occurred after cleaning, possibly during template rendering or context building")
    elif llm_content and final_content:
        logger.info("\nNO DISCREPANCY: The LLM-generated M-query matches the final M-query in the TMDL file")

def main():
    """Main function"""
    args = parse_args()
    
    # Get the log file path
    log_file = args.log_file
    if not log_file:
        # Find the latest log file if none specified
        log_file_path = find_latest_log_file()
        if not log_file_path:
            logger.error("No log file specified and couldn't find a recent log file")
            return
        log_file = str(log_file_path)
    
    logger.info(f"Analyzing log file: {log_file}")
    
    # Extract M-query tracking logs
    mquery_logs = extract_mquery_logs(log_file, args.table)
    
    if not mquery_logs:
        logger.error("No [MQUERY_TRACKING] logs found in the log file.")
        logger.info("Make sure you've run a migration with the enhanced logging code.")
        return
    
    # Group logs by table
    table_logs = group_logs_by_table(mquery_logs)
    
    # Analyze each table's M-query flow
    for table_name, logs in table_logs.items():
        if table_name != "unknown":
            analyze_table_mquery_flow(table_name, logs)
    
    logger.info("\nAnalysis complete. Check mquery_analysis.log for details.")

if __name__ == "__main__":
    main()
