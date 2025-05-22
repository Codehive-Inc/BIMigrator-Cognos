"""Parser for diagram layout."""
from bimigrator.models.power_bi_diagram_layout import (
    PowerBiDiagramLayout,
    DiagramLayout,
    TablePosition
)
from bimigrator.parsers.base_parser import BaseParser


class DiagramLayoutParser(BaseParser):
    """Parser for diagram layout."""

    def extract_diagram_layout(self) -> PowerBiDiagramLayout:
        """Extract diagram layout from Tableau workbook.
        
        Returns:
            PowerBiDiagramLayout object containing diagram layout
        """
        # For now, use default values with auto-layout
        # Place tables in a grid pattern
        tables = []
        x, y = 0, 0
        grid_width = 300  # Space between tables horizontally
        grid_height = 200  # Space between tables vertically
        max_columns = 3  # Maximum number of columns in the grid

        # Get all table names from the workbook
        table_names = self._get_table_names()

        # Create positions for each table
        for i, table_name in enumerate(table_names):
            # Calculate grid position
            column = i % max_columns
            row = i // max_columns
            
            # Create table position
            table_pos = TablePosition(
                id=table_name,
                x=column * grid_width,
                y=row * grid_height
            )
            tables.append(table_pos)

        layout = DiagramLayout(tables=tables)
        diagram_layout = PowerBiDiagramLayout(
            version=4,
            layout=layout
        )

        return diagram_layout

    def _get_table_names(self) -> list:
        """Get list of table names from the workbook.
        
        Returns:
            List of table names
        """
        # Get all datasources with valid connections
        datasources = []
        for ds in self.root.findall('.//datasource', self.namespaces):
            if ds.get('inline') == 'true' and ds.find('connection') is not None:
                datasources.append(ds)

        table_names = []
        for ds in datasources:
            caption = ds.get('caption')
            if caption:
                table_names.append(caption)

        return table_names
