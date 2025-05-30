"""Helper class to track and manage calculation conversions."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Union

from bimigrator.common.log_utils import log_file_saved, log_error

class CalculationTracker:
    """Tracks and manages calculation conversions between Tableau and Power BI."""
    
    def __init__(self, output_dir: Optional[Path], workbook_name: Optional[str] = None):
        """Initialize the calculation tracker.
        
        Args:
            output_dir: Output directory where the calculations.json will be stored
            workbook_name: Optional name of the workbook being processed
        """
        self.logger = logging.getLogger(__name__)
        self.workbook_name = workbook_name
        if output_dir:
            # Use the provided output directory directly
            self.output_dir = output_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Set JSON file path
            extracted_dir = self.output_dir / 'extracted'
            extracted_dir.mkdir(parents=True, exist_ok=True)
            self.json_path = extracted_dir / 'calculations.json'
            self.calculations = {}
            
            # Create or load existing JSON
            if self.json_path.exists():
                self._load_calculations()
            else:
                self._save_calculations()
    
    def _load_calculations(self):
        """Load existing calculations from JSON."""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
                self.calculations = {}
                for calc in data.get('calculations', []):
                    if 'TableauName' in calc and 'TableName' in calc:
                        # Always use internal name (TableauName) for key
                        key = f"{calc['TableName']}_{calc['TableauName']}"
                        self.calculations[key] = calc
                    else:
                        # Skip legacy data without internal names
                        continue
        except Exception as e:
            print(f"Error loading calculations: {str(e)}")
            self.calculations = {}
    
    def add_calculation(self, table_name: str, formula_caption_tableau: str, formula_tableau: str, formula_dax: str, data_type: str, is_measure: bool = False, tableau_name: Optional[str] = None):
        """Add a calculation to the tracker.
        
        Args:
            table_name: Name of the table containing the calculation
            formula_caption_tableau: Display name of the calculation in Tableau
            formula_tableau: Original Tableau formula
            formula_dax: Converted DAX formula
            data_type: Data type of the calculation
            is_measure: Whether this is a measure (True) or calculated column (False)
            tableau_name: Original name of the calculation in Tableau
        """
        # Validate tableau_name is provided for measures
        if is_measure and not tableau_name:
            print(f"Warning: Missing internal name for measure {formula_caption_tableau} in {table_name}")
            return

        # Validate tableau_name is different from caption for measures
        if is_measure and tableau_name == formula_caption_tableau:
            print(f"Warning: Internal name same as caption for measure {formula_caption_tableau} in {table_name}")
            return

        # Use internal name for key if available, otherwise use caption
        key = f"{table_name}_{tableau_name if tableau_name else formula_caption_tableau}"
        self.calculations[key] = {
            'TableName': table_name,
            'FormulaCaptionTableau': formula_caption_tableau,
            'TableauName': tableau_name or formula_caption_tableau,  # For non-measures, caption is ok as fallback
            'FormulaTableau': formula_tableau,
            'FormulaDax': formula_dax,
            'DataType': data_type,
            'IsMeasure': is_measure
        }
        self._save_calculations()

    def _save_calculations(self):
        """Save calculations to JSON."""
        try:
            # Ensure output directory exists
            if self.output_dir:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                extracted_dir = self.output_dir / 'extracted'
                extracted_dir.mkdir(parents=True, exist_ok=True)
                self.json_path = extracted_dir / 'calculations.json'

            data = {'calculations': []}
            for key, calc in self.calculations.items():
                data['calculations'].append(calc)
            with open(self.json_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Log the file save operation
            log_file_saved(str(self.json_path), f"{len(self.calculations)} calculations")
        except Exception as e:
            log_error(f"Error saving calculations", e)
            print(f"Error saving calculations: {str(e)}")
    
    def add_tableau_calculation(
        self,
        table_name: str,
        caption: str,
        expression: str,
        formula_type: str,
        calculation_name: Optional[str] = None
    ):
        """Add a Tableau calculation before conversion.
        
        Args:
            table_name: Name of the table containing the calculation
            caption: Display name of the calculation
            expression: Tableau formula expression
            formula_type: Type of formula (measure/calculated_column)
            calculation_name: Optional unique name for the calculation
        """
        if not hasattr(self, 'calculations'):
            return
            
        # Validate internal name based on formula type
        if formula_type in ['measure', 'calculated_column']:
            if not calculation_name:
                print(f"Warning: Missing internal name for {formula_type} {caption} in {table_name}")
                return

            if calculation_name == caption:
                print(f"Warning: Internal name same as caption for {formula_type} {caption} in {table_name}")
                return

        if not calculation_name:
            print(f"Warning: Missing TableauName for {formula_type} {caption} in {table_name}")
            return

        # Use TableName_TableauName as key
        key = f"{table_name}_{calculation_name}"
        self.calculations[key] = {
            'TableName': table_name,
            'FormulaCaptionTableau': caption,
            'TableauName': calculation_name,  # Always use internal name
            'FormulaTableau': expression,  # Store original formula
            'FormulaTypeTableau': formula_type,
            'PowerBIName': caption,
            'FormulaDax': '',  # Empty until conversion
            'Status': 'extracted'  # Track calculation state: extracted -> converted/failed
        }
        self._save_calculations()
    
    def update_powerbi_calculation(
        self,
        table_name: str,
        tableau_name: str,  # Use TableauName instead of caption
        powerbi_name: str,
        dax_expression: str
    ):
        """Update a calculation with Power BI conversion details.
        
        Args:
            table_name: Name of the table containing the calculation
            tableau_name: Internal Tableau name (e.g. [Calculation_123])
            powerbi_name: Name in Power BI
            dax_expression: Converted DAX expression
        """
        if not hasattr(self, 'calculations'):
            return
            
        # Find the calculation by TableauName
        for k, calc in self.calculations.items():
            if calc['TableName'] == table_name and calc['TableauName'] == tableau_name:
                # Only update DAX-related fields, preserve original formula
                self.calculations[k].update({
                    'PowerBIName': powerbi_name,
                    'FormulaDax': dax_expression,
                    'Status': 'converted' if not dax_expression.startswith('/* ERROR') else 'failed'
                })
                break
        self._save_calculations()
