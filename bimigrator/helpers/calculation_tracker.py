"""Helper class to track and manage calculation conversions."""
import json
from pathlib import Path
from typing import Dict, Optional

class CalculationTracker:
    """Tracks and manages calculation conversions between Tableau and Power BI."""
    
    def __init__(self, output_dir: Optional[Path]):
        """Initialize the calculation tracker.
        
        Args:
            output_dir: Output directory where the calculations.json will be stored
        """
        if output_dir:
            # Use the provided output directory directly
            self.output_dir = output_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Set JSON file path
            self.json_path = self.output_dir / 'calculations.json'
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
                    key = f"{calc['TableName']}_{calc['FormulaCaptionTableau']}"
                    self.calculations[key] = calc
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

        key = f"{table_name}_{formula_caption_tableau}"
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
        """Save calculations to JSON file."""
        try:
            data = {'calculations': []}
            for key, calc in self.calculations.items():
                data['calculations'].append(calc)
            with open(self.json_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
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
            
        key = f"{table_name}_{caption}"
        self.calculations[key] = {
            'TableName': table_name,
            'FormulaCaptionTableau': caption,
            'TableauName': calculation_name or caption,  # Use calculation_name if available, else caption
            'FormulaExpressionTableau': expression,
            'FormulaTypeTableau': formula_type,
            'PowerBIName': caption,
            'DAXExpression': '',
            'ConversionStatus': 'Pending'
        }
        self._save_calculations()
    
    def update_powerbi_calculation(
        self,
        table_name: str,
        tableau_caption: str,
        powerbi_name: str,
        dax_expression: str
    ):
        """Update a calculation with Power BI conversion details.
        
        Args:
            table_name: Name of the table containing the calculation
            tableau_caption: Original Tableau caption
            powerbi_name: Name in Power BI
            dax_expression: Converted DAX expression
        """
        if not hasattr(self, 'calculations'):
            return
            
        key = f"{table_name}_{tableau_caption}"
        if key in self.calculations:
            self.calculations[key].update({
                'PowerBIName': powerbi_name,
                'DAXExpression': dax_expression,
                'ConversionStatus': 'Converted'
            })
            self._save_calculations()
