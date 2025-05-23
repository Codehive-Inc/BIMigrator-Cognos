"""Parser for extracting column information from Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.converters import CalculationConverter
from bimigrator.converters.calculation_converter import CalculationInfo


class ColumnParser:
    """Parser for extracting column information from Tableau workbooks."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the column parser.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tableau_to_tmdl_datatypes = self.config.get('tableau_datatype_to_tmdl', {})
        
        # Initialize CalculationConverter with output_dir
        output_dir = config.get('output_dir')
        if output_dir:
            config['output_dir'] = output_dir
        self.calculation_converter = CalculationConverter(config)

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

    def extract_columns_and_measures(
            self,
            ds_element: ET.Element,
            columns_yaml_config: Dict[str, Any],
            pbi_table_name: str
    ) -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]:
        """Extract columns and measures from a datasource element.
        
        Args:
            ds_element: Datasource element
            columns_yaml_config: YAML configuration for columns
            pbi_table_name: Table name for DAX expressions
            
        Returns:
            Tuple of (columns, measures)
        """
        columns = []
        measures = []
        seen_col_names = set()

        # Get metadata-record columns
        column_elements_from_ds = ds_element.findall('.//metadata-record[@class="column"]')

        # Get calculated fields
        calc_field_xpath = columns_yaml_config.get('calculated_fields_xpath', "column[calculation]")
        calculated_field_elements = ds_element.findall(calc_field_xpath)

        # Get relation columns
        relation_column_elements = []
        relation_paths = columns_yaml_config.get('relation_column_paths', [])
        if not relation_paths:
            relation_paths = [
                ".//_.fcp.ObjectModelEncapsulateLegacy.false...relation//column",
                ".//_.fcp.ObjectModelEncapsulateLegacy.true...relation//column",
                ".//relation//column"
            ]

        for rel_path in relation_paths:
            rel_columns = ds_element.findall(rel_path)
            if rel_columns:
                relation_column_elements.extend(rel_columns)

        # Get configuration mappings
        relation_column_mappings = columns_yaml_config.get('relation_column_mappings', {})
        relation_name_attr = relation_column_mappings.get('name_attribute', 'name')
        relation_datatype_attr = relation_column_mappings.get('datatype_attribute', 'datatype')

        calc_field_mappings = columns_yaml_config.get('calculated_field_mappings', {})
        calc_name_attr = calc_field_mappings.get('name_attribute', 'caption')
        calc_datatype_attr = calc_field_mappings.get('datatype_attribute', 'datatype')

        # Process calculated fields first
        for calc_field in calculated_field_elements:
            col_name = calc_field.get(calc_name_attr)
            if not col_name or col_name in seen_col_names:
                continue

            # Get calculation name (the internal name)
            calculation_name = calc_field.get('name', col_name)

            # Get datatype and role
            twb_datatype = calc_field.get(calc_datatype_attr, 'string')
            role = calc_field.get('role', '')

            # Common aggregation functions
            agg_functions = ['SUM', 'AVERAGE', 'AVG', 'COUNT', 'MIN', 'MAX', 'COUNTD', 'ATTR']

            # Extract calculation formula
            calc_elem = calc_field.find('calculation')
            if calc_elem is not None and calc_elem.get('formula'):
                formula = calc_elem.get('formula')

                # Auto-detect measures based on aggregation functions
                formula_upper = formula.upper()
                for agg_func in agg_functions:
                    if formula_upper.startswith(agg_func + '('):
                        role = 'measure'
                        break

                # Convert to DAX
                dax_expression = self.calculation_converter.convert_to_dax(
                    CalculationInfo(
                        formula=formula,
                        caption=col_name,
                        datatype=twb_datatype,
                        role=role,
                        internal_name=calculation_name  # Pass the internal name
                    ),
                    pbi_table_name
                )

                if role == 'measure':
                    # Create measure
                    # Set annotations for measures
                    annotations = {
                        'SummarizationSetBy': 'Automatic',  # Add SummarizationSetBy
                    }

                    # PBI_FormatHint is now hardcoded in the template for measures

                    measure = PowerBiMeasure(
                        source_name=col_name,
                        dax_expression=dax_expression,
                        description=f"Converted from Tableau calculation: {formula}",
                        annotations=annotations,
                        tableau_name=calculation_name,  # Use internal calculation name
                        formula_tableau=formula  # Store original Tableau formula
                    )
                    measures.append(measure)
                    
                    # Validate that tableau_name is always the internal name
                    if not calculation_name or calculation_name == col_name:
                        print(f"Warning: Missing or invalid internal name for measure {col_name}")
                else:
                    # Create calculated column
                    pbi_datatype = self._map_datatype(twb_datatype)

                    # For numeric calculated columns, set summarize_by to 'sum'
                    summarize_by = "sum" if pbi_datatype.lower() in ["int64", "double", "decimal",
                                                                     "currency"] else "none"

                    # Set annotations
                    annotations = {
                        'SummarizationSetBy': 'Automatic'
                    }

                    # Add PBI_FormatHint for numeric columns
                    if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
                        annotations['PBI_FormatHint'] = {"isGeneralNumber": True}

                    # For calculated columns, we need to set the source_name to just the column name
                    # and put the DAX expression in the source_column field
                    # Validate internal name for calculated columns
                    if not calculation_name:
                        print(f"Warning: Missing internal name for calculated column {col_name}")
                        continue

                    if calculation_name == col_name:
                        print(f"Warning: Internal name same as caption for calculated column {col_name}")
                        continue

                    column = PowerBiColumn(
                        source_name=col_name,
                        pbi_datatype=pbi_datatype,
                        source_column=dax_expression,  # Put DAX expression in source_column
                        description=f"Converted from Tableau calculation: {formula}",
                        is_calculated=True,
                        is_data_type_inferred=True,
                        summarize_by=summarize_by,
                        annotations=annotations,
                        tableau_name=calculation_name,  # Internal Tableau calculation name
                        formula_tableau=formula  # Original Tableau formula
                    )
                    columns.append(column)

            seen_col_names.add(col_name)

        # Process relation columns
        for rel_col in relation_column_elements:
            col_name = rel_col.get(relation_name_attr)
            if not col_name or col_name in seen_col_names:
                continue

            twb_datatype = rel_col.get(relation_datatype_attr, 'string')
            pbi_datatype = self._map_datatype(twb_datatype)

            # For numeric columns, set summarize_by to 'sum'
            summarize_by = "sum" if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] else "none"

            # Set annotations
            annotations = {
                'SummarizationSetBy': 'User' if summarize_by == "sum" else 'Automatic'
            }

            # Add PBI_FormatHint for numeric columns
            if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
                annotations['PBI_FormatHint'] = {"isGeneralNumber": True}

            column = PowerBiColumn(
                source_name=col_name,
                pbi_datatype=pbi_datatype,
                source_column=col_name,  # Regular columns use their name as the source column
                summarize_by=summarize_by,
                annotations=annotations
            )
            columns.append(column)
            seen_col_names.add(col_name)

        # Process metadata-record columns
        for meta_col in column_elements_from_ds:
            remote_name = meta_col.find('remote-name')
            local_name = meta_col.find('local-name')

            if remote_name is not None and remote_name.text:
                col_name = remote_name.text
            elif local_name is not None and local_name.text:
                local_name_text = local_name.text
                if local_name_text.startswith('[') and local_name_text.endswith(']'):
                    col_name = local_name_text[1:-1]
                else:
                    col_name = local_name_text
            else:
                col_name = meta_col.get('caption') or meta_col.get('name')

            if not col_name or col_name in seen_col_names:
                continue

            # Get datatype
            local_type = meta_col.find('local-type')
            remote_type = meta_col.find('remote-type')

            if local_type is not None and local_type.text:
                twb_datatype = local_type.text
            elif remote_type is not None and remote_type.text:
                # Map remote-type number to string datatype
                remote_type_num = remote_type.text.strip()
                if remote_type_num in ['129', '130']:  # VARCHAR, WSTR
                    twb_datatype = 'string'
                elif remote_type_num in ['5', '6', '131']:  # FLOAT, DOUBLE, NUMERIC
                    twb_datatype = 'real'
                elif remote_type_num in ['3', '4', '20']:  # INT, LONG, BIGINT
                    twb_datatype = 'integer'
                elif remote_type_num in ['7', '135']:  # DATE, TIMESTAMP
                    twb_datatype = 'datetime'
                elif remote_type_num in ['11']:  # BOOLEAN
                    twb_datatype = 'boolean'
                else:
                    twb_datatype = 'string'
            else:
                twb_datatype = meta_col.get('type', 'string')

            pbi_datatype = self._map_datatype(twb_datatype)

            # For numeric columns, set summarize_by to 'sum'
            summarize_by = "sum" if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] else "none"

            # Set annotations
            annotations = {
                'SummarizationSetBy': 'User' if summarize_by == "sum" else 'Automatic'
            }

            # Add PBI_FormatHint for numeric columns
            if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"]:
                annotations['PBI_FormatHint'] = {"isGeneralNumber": True}

            column = PowerBiColumn(
                source_name=col_name,
                pbi_datatype=pbi_datatype,
                source_column=col_name,  # Regular columns use their name as the source column
                summarize_by=summarize_by,
                annotations=annotations
            )
            columns.append(column)
            seen_col_names.add(col_name)

        return columns, measures

    def _map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes.
        
        Args:
            tableau_type: Tableau datatype string
            
        Returns:
            Power BI datatype string
        """
        if not tableau_type or not isinstance(tableau_type, str):
            return 'string'

        return self.tableau_to_tmdl_datatypes.get(tableau_type.lower(), 'string')
