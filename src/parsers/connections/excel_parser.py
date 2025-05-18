"""Parser for Excel connections in Tableau workbooks."""
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

from .base_connection import BaseConnectionParser
from config.data_classes import PowerBiPartition, PowerBiColumn
from ...common.tableau_helpers import generate_excel_m_code


class ExcelConnectionParser(BaseConnectionParser):
    """Parser for Excel connections in Tableau workbooks."""

    def can_handle(self, connection_node: ET.Element) -> bool:
        """Check if this parser can handle the given connection.
        
        Args:
            connection_node: Connection element from Tableau workbook
            
        Returns:
            True if this is an Excel connection, False otherwise
        """
        # Check direct Excel connection
        if connection_node.get('class') == 'excel-direct':
            return True
            
        # Check federated connection with Excel
        if connection_node.get('class') == 'federated':
            for named_conn in connection_node.findall('.//named-connection'):
                conn = named_conn.find('.//connection')
                if conn is not None and conn.get('class') == 'excel-direct':
                    return True
        return False
        
    def extract_partition_info(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        table_name: str,
        columns: Optional[List[PowerBiColumn]] = None
    ) -> List[PowerBiPartition]:
        """Extract partition information from Excel connection.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            table_name: Name of the table
            columns: Optional list of PowerBiColumn objects with type information
            
        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        
        # Get Excel filename and sheet name
        excel_filename = None
        excel_sheet = None
        
        # Check direct connection
        if connection_node.get('class') == 'excel-direct':
            excel_filename = connection_node.get('filename')
            
        # Check federated connection
        elif connection_node.get('class') == 'federated':
            for named_conn in connection_node.findall('.//named-connection'):
                conn = named_conn.find('.//connection')
                if conn is not None and conn.get('class') == 'excel-direct':
                    excel_filename = conn.get('filename')
                    break
                    
        # Get sheet name from relation
        if excel_filename:
            table_ref = relation_node.get('table', '')
            if table_ref and table_ref.startswith('[') and table_ref.endswith('$]'):
                excel_sheet = table_ref[1:-2]  # Remove [ and $]
            else:
                excel_sheet = relation_node.get('name', 'Sheet1')
                
            # Prepare column data for M code generation
            columns_data = []
            if columns:
                for col in columns:
                    col_data = {
                        'source_name': col.source_name,
                        'datatype': col.pbi_datatype
                    }
                    columns_data.append(col_data)
                    
            # Generate M code
            m_code = generate_excel_m_code(excel_filename, excel_sheet, columns_data)
            
            # Create partition
            partition = PowerBiPartition(
                name=excel_sheet,
                expression=m_code,
                source_type='m',
                description=f"Excel partition for table {excel_sheet}"
            )
            partitions.append(partition)
            
        return partitions
        
    def extract_columns(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        columns_yaml_config: Dict[str, Any]
    ) -> List[PowerBiColumn]:
        """Extract columns from Excel connection.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            columns_yaml_config: YAML configuration for columns
            
        Returns:
            List of PowerBiColumn objects
        """
        columns = []
        
        # Get relation column paths from configuration
        relation_paths = columns_yaml_config.get('relation_column_paths', [])
        if not relation_paths:
            relation_paths = [
                ".//_.fcp.ObjectModelEncapsulateLegacy.false...relation//column",
                ".//_.fcp.ObjectModelEncapsulateLegacy.true...relation//column",
                ".//relation//column"
            ]
            
        # Get relation column mappings
        relation_column_mappings = columns_yaml_config.get('relation_column_mappings', {})
        relation_name_attr = relation_column_mappings.get('name_attribute', 'name')
        relation_datatype_attr = relation_column_mappings.get('datatype_attribute', 'datatype')
        
        # Extract columns from relation
        for rel_path in relation_paths:
            rel_columns = relation_node.findall(rel_path)
            for col_elem in rel_columns:
                col_name = col_elem.get(relation_name_attr)
                if not col_name:
                    continue
                    
                # Get datatype
                twb_datatype = col_elem.get(relation_datatype_attr, 'string')
                pbi_datatype = self._map_datatype(twb_datatype)
                
                # Create column
                column = PowerBiColumn(
                    name=col_name,
                    source_name=col_name,
                    pbi_datatype=pbi_datatype
                )
                columns.append(column)
                
        return columns
        
    def _map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes.
        
        Args:
            tableau_type: Tableau datatype string
            
        Returns:
            Power BI datatype string
        """
        tableau_to_tmdl_datatypes = self.config.get('tableau_datatype_to_tmdl', {})
        if not tableau_type or not isinstance(tableau_type, str):
            return 'string'
            
        tableau_type = tableau_type.lower()
        return tableau_to_tmdl_datatypes.get(tableau_type, 'string')
