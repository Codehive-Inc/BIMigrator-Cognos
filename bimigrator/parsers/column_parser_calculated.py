"""Parser for calculated fields in Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Set, Tuple

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.converters.calculation_converter import CalculationInfo
from bimigrator.parsers.column_parser_base import ColumnParserBase


class CalculatedFieldParser(ColumnParserBase):
    """Parser for calculated fields in Tableau workbooks."""

    def extract_columns_and_measures(
            self,
            ds_element: ET.Element,
            columns_yaml_config: Dict[str, Any],
            pbi_table_name: str
    ) -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]:
        """Extract calculated columns and measures from a datasource element.
        
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

        # Get calculated fields
        calc_field_xpath = columns_yaml_config.get('calculated_fields_xpath', "column[calculation]")
        calculated_field_elements = ds_element.findall(calc_field_xpath)

        # Get configuration mappings
        calc_field_mappings = columns_yaml_config.get('calculated_field_mappings', {})
        calc_name_attr = calc_field_mappings.get('name_attribute', 'caption')
        calc_datatype_attr = calc_field_mappings.get('datatype_attribute', 'datatype')

        # Common aggregation functions
        agg_functions = ['SUM', 'AVERAGE', 'AVG', 'COUNT', 'MIN', 'MAX', 'COUNTD', 'ATTR']

        # Process calculated fields
        for calc_field in calculated_field_elements:
            col_name = calc_field.get(calc_name_attr)
            if not col_name or col_name in seen_col_names:
                continue

            # Get calculation name (the internal name)
            calculation_name = calc_field.get('name', col_name)

            # Get datatype and role
            twb_datatype = calc_field.get(calc_datatype_attr, 'string')
            role = calc_field.get('role', '')

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

                # Store original formula first
                if self.calculation_tracker:
                    # Only add if not already present
                    key = f"{pbi_table_name}_{calculation_name}"
                    if key not in self.calculation_tracker.calculations:
                        self.calculation_tracker.add_tableau_calculation(
                            table_name=pbi_table_name,
                            caption=col_name,
                            expression=formula,
                            formula_type='measure' if role == 'measure' else 'calculated_column',
                            calculation_name=calculation_name
                        )

                # Convert to DAX
                dax_expression = self.calculation_converter.convert_to_dax(
                    CalculationInfo(
                        formula=formula,
                        caption=col_name,
                        datatype=twb_datatype,
                        role=role,
                        internal_name=calculation_name
                    ),
                    pbi_table_name
                )

                # Update with DAX expression
                if self.calculation_tracker:
                    self.calculation_tracker.update_powerbi_calculation(
                        table_name=pbi_table_name,
                        tableau_name=calculation_name,
                        powerbi_name=col_name,
                        dax_expression=dax_expression
                    )

                if role == 'measure':
                    # Create measure
                    annotations = {
                        'SummarizationSetBy': 'Automatic',
                    }

                    measure = PowerBiMeasure(
                        source_name=col_name,
                        dax_expression=dax_expression,
                        description=f"Converted from Tableau calculation: {formula}",
                        annotations=annotations,
                        tableau_name=calculation_name,
                        formula_tableau=formula
                    )
                    measures.append(measure)
                    
                    if not calculation_name or calculation_name == col_name:
                        print(f"Warning: Missing or invalid internal name for measure {col_name}")
                else:
                    # Create calculated column
                    pbi_datatype = self.type_mapper.map_datatype(twb_datatype)

                    # For numeric calculated columns, set summarize_by to 'sum'
                    summarize_by = "sum" if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] else "none"

                    # Set annotations
                    annotations = self.type_mapper.get_annotations_for_datatype(pbi_datatype, summarize_by)

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
                        source_column=dax_expression,
                        description=f"Converted from Tableau calculation: {formula}",
                        is_calculated=True,
                        is_data_type_inferred=True,
                        summarize_by=summarize_by,
                        annotations=annotations,
                        tableau_name=calculation_name,
                        formula_tableau=formula
                    )
                    columns.append(column)

            seen_col_names.add(col_name)

        return columns, measures
