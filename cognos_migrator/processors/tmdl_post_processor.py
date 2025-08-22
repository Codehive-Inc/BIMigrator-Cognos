"""
This module contains the TMDLPostProcessor, which is responsible for reading
a generated TMDL file, fixing issues like ambiguous relationships, and
overwriting the file with a clean version.
"""
import logging
import re
from collections import deque
from typing import Dict, List, Any, Optional

class Graph:
    """A simple graph class to detect cycles in relationships."""

    def __init__(self, nodes: list[str]):
        """Initialize the graph with a set of nodes."""
        self.graph = {node: [] for node in nodes}
        self.nodes = nodes

    def add_edge(self, u: str, v: str):
        """Add an edge between two nodes."""
        if u in self.graph and v in self.graph:
            self.graph[u].append(v)
            self.graph[v].append(u)

    def path_exists(self, start_node: str, end_node: str, nodes_to_ignore: list[str] | None = None) -> bool:
        """Check if a path exists between two nodes using BFS, ignoring certain nodes."""
        if start_node not in self.graph or end_node not in self.graph:
            return False
        
        if nodes_to_ignore is None:
            nodes_to_ignore = []

        visited = {node: False for node in self.graph}
        queue = deque([start_node])
        visited[start_node] = True

        while queue:
            u = queue.popleft()
            if u == end_node:
                return True
            for v in self.graph.get(u, []):
                # Ignore specified nodes
                if v.lower() in [ign.lower() for ign in nodes_to_ignore]:
                    continue
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
        return False

class TMDLPostProcessor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def fix_relationships(self, tmdl_file_path: str):
        """
        Reads a relationships.tmdl file, resolves ambiguities,
        and overwrites it with a clean version.
        """
        self.logger.info(f"Starting post-processing for relationship file: {tmdl_file_path}")
        
        with open(tmdl_file_path, 'r') as f:
            tmdl_content = f.read()

        # Step 1: Read and parse the file
        raw_relationships, all_tables = self._parse_tmdl_file(tmdl_content)
        if not raw_relationships:
            self.logger.warning("No relationships found in TMDL file. Aborting post-processing.")
            return

        self.logger.info(f"Read {len(raw_relationships)} raw relationships from TMDL file involving tables: {all_tables}")

        # Step 2: Filter out incompatible relationships for DirectQuery mode
        filtered_relationships = self._filter_directquery_incompatible_relationships(raw_relationships)
        
        # Step 3: Apply the proven ambiguity resolution logic
        clean_relationships = self._resolve_ambiguities(filtered_relationships, all_tables)
        
        # Step 3: Write the clean relationships back to the file
        self._write_tmdl_file(tmdl_file_path, clean_relationships)
        
        self.logger.info(f"Relationship post-processing complete. Wrote {len(clean_relationships)} clean relationships.")

    def _parse_tmdl_file(self, tmdl_content: str) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Parses a .tmdl file content and extracts relationship objects and all unique table names.
        """
        relationships = []
        table_names = set()
        
        # Split the content by relationship blocks
        # The format is "relationship UUID" followed by indented properties
        rel_blocks = re.split(r'\nrelationship\s+', tmdl_content)
        
        # Skip the first element if it's empty (file starts with 'relationship')
        if rel_blocks and not rel_blocks[0].strip():
            rel_blocks = rel_blocks[1:]
        elif rel_blocks and rel_blocks[0].startswith('relationship'):
            # Handle case where first line starts with 'relationship'
            rel_blocks[0] = rel_blocks[0][len('relationship'):].strip()
        
        self.logger.info(f"Found {len(rel_blocks)} potential relationship blocks")
        
        for block in rel_blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            # First line contains the relationship ID
            rel_id = lines[0].strip()
            
            # Parse properties from the remaining lines
            properties = {}
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    properties[key] = value
            
            # Extract table and column information
            from_column = properties.get('fromColumn', '')
            to_column = properties.get('toColumn', '')
            
            # Extract table names from column references (format: TABLE.COLUMN)
            from_table = from_column.split('.')[0] if '.' in from_column else ''
            to_table = to_column.split('.')[0] if '.' in to_column else ''
            
            if from_table and to_table and from_column and to_column:
                # Create raw body for writing back
                raw_body = '\n'.join([f'\t{key}: {value}' for key, value in properties.items()])
                
                relationships.append({
                    "id": rel_id,
                    "from_table": from_table,
                    "from_column": from_column.split('.')[-1] if '.' in from_column else from_column,
                    "to_table": to_table,
                    "to_column": to_column.split('.')[-1] if '.' in to_column else to_column,
                    "raw_body": raw_body
                })
                
                table_names.add(from_table)
                table_names.add(to_table)

        # No need for additional processing - we've already built the relationships list

        return relationships, list(table_names)
        
    def _resolve_ambiguities(self, relationships: List[Dict[str, Any]], all_tables: List[str]) -> List[Dict[str, Any]]:
        """
        Applies centrality and key-strength logic to filter relationships.
        """
        centrality = self._calculate_centrality(relationships)
        self.logger.info(f"Table centrality scores: {centrality}")

        prioritized_list = sorted(relationships, key=lambda r: self._get_relationship_priority(r, centrality))
        self.logger.info(f"Prioritized {len(prioritized_list)} relationships for processing based on key strength and centrality.")

        final_relationships = []
        model_graph = Graph(nodes=[t.lower() for t in all_tables])

        for rel in prioritized_list:
            from_table = rel['from_table'].lower()
            to_table = rel['to_table'].lower()

            if model_graph.path_exists(from_table, to_table, nodes_to_ignore=['centraldatetable']):
                self.logger.warning(
                    f"DISCARDED: Ambiguous relationship from '{rel['from_table']}' to '{rel['to_table']}' "
                    f"on column '{rel['from_column']}'. A path already exists."
                )
            else:
                final_relationships.append(rel)
                model_graph.add_edge(from_table, to_table)
                self.logger.info(f"ADDED: Relationship from '{rel['from_table']}' to '{rel['to_table']}' on '{rel['from_column']}'.")

        return final_relationships

    def _calculate_centrality(self, relationships: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculates how many relationships each table participates in."""
        centrality = {}
        for rel in relationships:
            from_table = rel['from_table'].lower()
            to_table = rel['to_table'].lower()
            centrality[from_table] = centrality.get(from_table, 0) + 1
            centrality[to_table] = centrality.get(to_table, 0) + 1
        return centrality

    def _get_key_strength(self, column_name: str) -> str:
        """Determines if a column is a 'strong' or 'weak' key."""
        name_lower = column_name.lower()
        strong_key_indicators = ['_id', '_key', 'number', 'code']
        weak_key_names = ['stop', 'status', 'date']

        if any(weak_name in name_lower for weak_name in weak_key_names):
            if 'date' in name_lower:
                return 'date_weak'
            return 'weak'

        if any(indicator in name_lower for indicator in strong_key_indicators):
            return 'strong'
        
        return 'weak'

    def _get_relationship_priority(self, rel: Dict[str, Any], centrality: Dict[str, int]) -> tuple[int, int]:
        """Assigns a priority score to a relationship."""
        from_table = rel['from_table'].lower()
        to_table = rel['to_table'].lower()
        
        key_strength_from = self._get_key_strength(rel['from_column'])
        key_strength_to = self._get_key_strength(rel['to_column'])

        if 'strong' in [key_strength_from, key_strength_to]:
            key_priority = 1
        elif 'date_weak' in [key_strength_from, key_strength_to]:
            key_priority = 3
        else:
            key_priority = 2

        centrality_priority = -max(centrality.get(from_table, 0), centrality.get(to_table, 0))

        return (key_priority, centrality_priority)

    def _filter_directquery_incompatible_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out relationships that are incompatible with DirectQuery mode.
        Currently removes CentralDateTable relationships when in DirectQuery mode.
        """
        try:
            # Check if we're in DirectQuery mode and need to filter
            from ..migrations.package import load_settings
            settings = load_settings()
            is_directquery = settings.get("staging_tables", {}).get("data_load_mode", "import") == "direct_query"
            
            if not is_directquery:
                self.logger.info("Import mode detected, keeping all relationships")
                return relationships
            
            # Filter out CentralDateTable relationships in DirectQuery mode
            filtered_relationships = []
            skipped_count = 0
            
            for rel in relationships:
                # Skip relationships to/from CentralDateTable in DirectQuery mode
                if (rel.get('from_table') == 'CentralDateTable' or rel.get('to_table') == 'CentralDateTable'):
                    self.logger.info(f"Skipping CentralDateTable relationship in DirectQuery mode: {rel.get('from_table')}.{rel.get('from_column')} -> {rel.get('to_table')}.{rel.get('to_column')}")
                    skipped_count += 1
                    continue
                    
                filtered_relationships.append(rel)
            
            if skipped_count > 0:
                self.logger.warning(f"DirectQuery mode: Filtered out {skipped_count} CentralDateTable relationships (calculated date tables are incompatible with DirectQuery)")
                self.logger.info("To include date functionality in DirectQuery mode, consider creating a physical date table in your database")
            
            return filtered_relationships
            
        except Exception as e:
            self.logger.error(f"Error filtering DirectQuery incompatible relationships: {e}")
            self.logger.warning("Proceeding with all relationships (filtering failed)")
            return relationships

    def _write_tmdl_file(self, file_path: str, relationships: List[Dict[str, Any]]):
        """
        Writes a list of relationship objects back to a .tmdl file.
        """
        tmdl_output = ""
        for rel in relationships:
            tmdl_output += f"relationship {rel['id']}\n"
            tmdl_output += rel['raw_body']
            tmdl_output += "\n\n"
        
        with open(file_path, 'w') as f:
            f.write(tmdl_output) 