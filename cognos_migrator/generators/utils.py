"""
Utility functions for generators.
"""
import json
import logging
import xml.dom.minidom as minidom
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple


def get_extracted_dir(dir_path: Path) -> Optional[Path]:
    """
    Get the extracted directory path based on the given directory path.
    
    Args:
        dir_path: Directory path to check
        
    Returns:
        Path to the extracted directory if applicable, None otherwise
    """
    # Check if we should save extracted files
    if dir_path.parent and dir_path.parent.name == 'pbit':
        # Navigate up to get to the output directory
        output_dir = dir_path.parent.parent
        extracted_dir = output_dir / 'extracted'
        extracted_dir.mkdir(exist_ok=True)
        return extracted_dir
    return None


def save_json_to_extracted_dir(extracted_dir: Path, filename: str, data: Dict[str, Any]) -> None:
    """
    Save JSON data to a file in the extracted directory.
    
    Args:
        extracted_dir: Path to the extracted directory
        filename: Name of the file to save
        data: JSON data to save
    """
    json_file = extracted_dir / filename
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def split_report_specification(xml_path: Path) -> Tuple[str, str]:
    """
    Split report specification XML into layout and query components while preserving the original XML structure.
    
    Args:
        xml_path: Path to the report specification XML file
        
    Returns:
        Tuple containing layout specification and query specification as XML strings
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Read the original XML file
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Parse the XML content
        dom = minidom.parseString(xml_content)
        root = dom.documentElement
        
        # Get the namespace if present
        namespace = ''
        xmlns = root.getAttribute('xmlns')
        if xmlns:
            logger.info(f"Detected XML namespace: {xmlns}")
            namespace = xmlns
        
        # Create new XML documents for layout and query
        impl = minidom.getDOMImplementation()
        
        # Create layout document with the same structure as the original
        layout_doc = impl.createDocument(namespace, 'report', None)
        layout_root = layout_doc.documentElement
        
        # Copy attributes from original root to layout root
        for i in range(root.attributes.length):
            attr = root.attributes.item(i)
            layout_root.setAttribute(attr.name, attr.value)
        
        # Create query document with the same structure as the original
        query_doc = impl.createDocument(namespace, 'report', None)
        query_root = query_doc.documentElement
        
        # Copy attributes from original root to query root
        for i in range(root.attributes.length):
            attr = root.attributes.item(i)
            query_root.setAttribute(attr.name, attr.value)
        
        # Copy comments from original document to both new documents
        for child in root.childNodes:
            if child.nodeType == minidom.Node.COMMENT_NODE:
                layout_root.appendChild(child.cloneNode(True))
                query_root.appendChild(child.cloneNode(True))
        
        # Helper function to clean whitespace nodes
        def clean_whitespace(node):
            # Remove text nodes that are just whitespace
            children_to_remove = []
            for child in node.childNodes:
                if child.nodeType == minidom.Node.TEXT_NODE and child.nodeValue.strip() == '':
                    children_to_remove.append(child)
                elif child.hasChildNodes():
                    clean_whitespace(child)
            
            for child in children_to_remove:
                node.removeChild(child)
        
        # Copy drillBehavior to both documents (if present)
        drill_behavior = root.getElementsByTagName('drillBehavior')
        if drill_behavior and drill_behavior.length > 0:
            drill_node = drill_behavior[0].cloneNode(True)
            clean_whitespace(drill_node)
            layout_root.appendChild(drill_node)
            query_root.appendChild(drill_node.cloneNode(True))
        
        # Copy layouts section to layout document
        layouts = root.getElementsByTagName('layouts')
        if layouts and layouts.length > 0:
            layouts_node = layouts[0].cloneNode(True)
            clean_whitespace(layouts_node)
            layout_root.appendChild(layouts_node)
        
        # Copy queries section to query document
        queries = root.getElementsByTagName('queries')
        if queries and queries.length > 0:
            queries_node = queries[0].cloneNode(True)
            clean_whitespace(queries_node)
            query_root.appendChild(queries_node)
        
        # Copy parameterList to query document (if present)
        param_list = root.getElementsByTagName('parameterList')
        if param_list and param_list.length > 0:
            param_node = param_list[0].cloneNode(True)
            clean_whitespace(param_node)
            query_root.appendChild(param_node)
        
        # Generate XML strings
        layout_xml = layout_doc.toprettyxml(indent='  ')
        query_xml = query_doc.toprettyxml(indent='  ')
        
        return layout_xml, query_xml
        
    except Exception as e:
        logger.error(f"Error splitting report specification: {e}")
        # Return empty documents in case of error
        impl = minidom.getDOMImplementation()
        layout_doc = impl.createDocument(None, 'report', None)
        query_doc = impl.createDocument(None, 'report', None)
        return layout_doc.toprettyxml(indent='  '), query_doc.toprettyxml(indent='  ')


def save_split_report_specification(xml_path: Path, extracted_dir: Path) -> None:
    """
    Split report specification and save layout and query components to separate XML files.
    
    Args:
        xml_path: Path to the report specification XML file
        extracted_dir: Path to the extracted directory
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Split the report specification
        layout_xml, query_xml = split_report_specification(xml_path)
        
        # Save layout specification as XML
        layout_path = extracted_dir / "report_layout_specification.xml"
        with open(layout_path, 'w', encoding='utf-8') as f:
            f.write(layout_xml)
        
        # Save query specification as XML
        query_path = extracted_dir / "report_query_specification.xml"
        with open(query_path, 'w', encoding='utf-8') as f:
            f.write(query_xml)
            
        logger.info("Split report specification into layout and query components")
    except Exception as e:
        logger.error(f"Failed to save split report specification: {e}")
