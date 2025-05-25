"""Parser for relation columns in Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Set, Tuple

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.parsers.column_parser_base import ColumnParserBase


class RelationColumnParser(ColumnParserBase):
    """Parser for relation columns in Tableau workbooks."""

    def extract_columns_and_measures(
            self,
            ds_element: ET.Element,
            columns_yaml_config: Dict[str, Any],
            pbi_table_name: str
    ) -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]:
        """Extract relation columns from a datasource element.
        
        Args:
            ds_element: Datasource element
            columns_yaml_config: YAML configuration for columns
            pbi_table_name: Table name for DAX expressions
            
        Returns:
            Tuple of (columns, measures)
        """
        columns = []
        seen_col_names = set()

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

        # Process relation columns
        for rel_col in relation_column_elements:
            col_name = rel_col.get(relation_name_attr)
            if not col_name or col_name in seen_col_names:
                continue

            twb_datatype = rel_col.get(relation_datatype_attr, 'string')
            pbi_datatype = self.type_mapper.map_datatype(twb_datatype)

            # For numeric columns, set summarize_by to 'sum'
            summarize_by = "sum" if pbi_datatype.lower() in ["int64", "double", "decimal", "currency"] else "none"

            # Set annotations
            annotations = self.type_mapper.get_annotations_for_datatype(pbi_datatype, summarize_by)

            column = PowerBiColumn(
                source_name=col_name,
                pbi_datatype=pbi_datatype,
                source_column=col_name,  # Regular columns use their name as the source column
                summarize_by=summarize_by,
                annotations=annotations
            )
            columns.append(column)
            seen_col_names.add(col_name)

        return columns, []  # No measures from relation columns
