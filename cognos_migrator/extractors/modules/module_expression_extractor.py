"""Module expression extractor for Cognos to Power BI migration"""

import logging
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from .module_extractor import ModuleExtractor


class ModuleExpressionExtractor(ModuleExtractor):
    """Collects and combines calculations from Cognos reports"""
    
    def __init__(self, logger=None, llm_client=None):
        """Initialize the module expression extractor
        
        Args:
            logger: Optional logger instance
            llm_client: LLM client (not used in this implementation)
        """
        super().__init__(logger)
        self.llm_client = llm_client
        
    def collect_report_calculations(self, report_ids: List[str], base_output_path: str, output_dir: str) -> Dict[str, Any]:
        """Collect calculations from multiple reports and combine them
        
        Args:
            report_ids: List of report IDs to collect calculations from
            base_output_path: Base path where report outputs are stored
            output_dir: Directory to save combined calculations
            
        Returns:
            Dictionary with combined calculations
        """
        self.logger.info(f"Collecting calculations from {len(report_ids)} reports")
        
        # Initialize empty calculations dictionary
        combined_calculations = {"calculations": []}
        
        try:
            # For each report, check if calculations.json exists and collect calculations
            for report_id in report_ids:
                # Construct the path to the report's calculations.json file
                report_calculations_path = Path(base_output_path).parent / f"report_{report_id}" / "extracted" / "calculations.json"
                
                if report_calculations_path.exists():
                    self.logger.info(f"Found calculations for report {report_id}")
                    with open(report_calculations_path, 'r', encoding='utf-8') as f:
                        report_calculations = json.load(f)
                        
                        # Merge calculations from this report
                        if 'calculations' in report_calculations and isinstance(report_calculations['calculations'], list):
                            combined_calculations['calculations'].extend(report_calculations['calculations'])
            
            # Process the calculations to extract correct table names and update DAX expressions
            processed_calculations = self._process_calculations(combined_calculations['calculations'])
            combined_calculations['calculations'] = processed_calculations
            
            # Save the combined calculations to calculations.json
            with open(Path(output_dir) / "calculations.json", 'w', encoding='utf-8') as f:
                json.dump(combined_calculations, f, indent=2)
            
            self.logger.info(f"Saved {len(combined_calculations['calculations'])} calculations from reports")
            return combined_calculations
            
        except Exception as e:
            self.logger.error(f"Error collecting calculations from reports: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            return {"calculations": []}
    
    def _process_calculations(self, calculations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process calculations to extract correct table names and update DAX expressions
        
        Args:
            calculations: List of calculation dictionaries
            
        Returns:
            Processed calculations
        """
        processed_calculations = []
        
        for calc in calculations:
            try:
                # Extract table name from FormulaCognos
                formula_cognos = calc.get('FormulaCognos', '')
                table_name = self._extract_table_name(formula_cognos)
                
                if table_name:
                    # Update TableName with the extracted table name
                    calc['TableName'] = table_name
                
                # Update FormulaDax to use correct [table].[column] format
                formula_dax = calc.get('FormulaDax', '')
                if formula_dax:
                    calc['FormulaDax'] = self._update_dax_formula(formula_dax, table_name)
                
                processed_calculations.append(calc)
            except Exception as e:
                self.logger.warning(f"Error processing calculation: {e}")
                # Keep the original calculation if processing fails
                processed_calculations.append(calc)
        
        return processed_calculations
    
    def _extract_table_name(self, formula_cognos: str) -> str:
        """Extract table name from Cognos formula
        
        Args:
            formula_cognos: Cognos formula
            
        Returns:
            Extracted table name or empty string if not found
        """
        # Pattern to match [namespace].[package].[table].[column]
        pattern = r'\[\w+\]\.\[\w+\]\.\[(\w+)\]'
        match = re.search(pattern, formula_cognos)
        
        if match:
            return match.group(1)
        
        return ""
    
    def _update_dax_formula(self, formula_dax: str, table_name: str) -> str:
        """Update DAX formula to use correct [table].[column] format
        
        Args:
            formula_dax: DAX formula
            table_name: Table name to use
            
        Returns:
            Updated DAX formula
        """
        if not table_name:
            return formula_dax
        
        # Replace 'Report_with_Calculations'[column] with 'table_name'[column]
        pattern = r"'[^']*'\[(\w+)\]"
        
        def replace_table(match):
            column = match.group(1)
            return f"'{table_name}'[{column}]"
        
        updated_formula = re.sub(pattern, replace_table, formula_dax)
        return updated_formula
    
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Placeholder method to maintain compatibility with the ModuleExtractor interface
        
        This method is not used as we're only collecting calculations from reports.
        
        Args:
            module_content: JSON content of the module (not used)
            output_dir: Directory to save extracted data (not used)
            
        Returns:
            Empty dictionary
        """
        self.logger.info("Module expression extraction not implemented - use collect_report_calculations instead")
        return {"calculations": []}