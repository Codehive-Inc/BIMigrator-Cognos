"""Handles datatype mapping between Tableau and Power BI."""
from typing import Dict, Any


class ColumnTypeMapper:
    """Maps Tableau datatypes to Power BI datatypes."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the type mapper.
        
        Args:
            config: Configuration dictionary
        """
        self.tableau_to_tmdl_datatypes = config.get('tableau_datatype_to_tmdl', {})
        
        # Initialize default datatype mapping if not provided in config
        if not self.tableau_to_tmdl_datatypes:
            self.tableau_to_tmdl_datatypes = {
                'string': 'string',
                'integer': 'int64',
                'real': 'double',
                'boolean': 'boolean',
                'date': 'datetime',
                'datetime': 'datetime'
            }

    def map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes.
        
        Args:
            tableau_type: Tableau datatype string
            
        Returns:
            Power BI datatype string
        """
        if not tableau_type or not isinstance(tableau_type, str):
            return 'string'

        return self.tableau_to_tmdl_datatypes.get(tableau_type.lower(), 'string')

    def get_annotations_for_datatype(self, pbi_datatype: str, summarize_by: str = "none") -> Dict[str, Any]:
        """Get annotations for a given Power BI datatype.
        
        Args:
            pbi_datatype: Power BI datatype
            summarize_by: Summarization type
            
        Returns:
            Dictionary of annotations
        """
        annotations = {
            'SummarizationSetBy': 'User' if summarize_by == "sum" else 'Automatic'
        }

        # Add PBI_FormatHint for numeric columns
        if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
            annotations['PBI_FormatHint'] = {"isGeneralNumber": True}

        return annotations
