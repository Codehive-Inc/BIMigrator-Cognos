"""Parser for metadata record columns in Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Set, Tuple

from bimigrator.config.data_classes import PowerBiColumn, PowerBiMeasure
from bimigrator.parsers.column_parser_base import ColumnParserBase


class MetadataColumnParser(ColumnParserBase):
    """Parser for metadata record columns in Tableau workbooks."""

    def extract_columns_and_measures(
            self,
            ds_element: ET.Element,
            columns_yaml_config: Dict[str, Any],
            pbi_table_name: str
    ) -> Tuple[List[PowerBiColumn], List[PowerBiMeasure]]:
        """Extract metadata record columns from a datasource element.
        
        Args:
            ds_element: Datasource element
            columns_yaml_config: YAML configuration for columns
            pbi_table_name: Table name for DAX expressions
            
        Returns:
            Tuple of (columns, measures)
        """
        columns = []
        seen_col_names = set()

        # Get metadata-record columns
        column_elements_from_ds = ds_element.findall('.//metadata-record[@class="column"]')

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

        return columns, []  # No measures from metadata columns
