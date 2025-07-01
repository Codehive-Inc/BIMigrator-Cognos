"""
Consolidation utilities for Cognos to Power BI migration

This module provides functions to consolidate various artifacts from 
multiple migrations (modules and reports) into a single coherent output.
"""

import logging
from pathlib import Path
from typing import List, Optional

def consolidate_model_tables(output_path: str) -> bool:
    """Consolidate all tables into a single model.tmdl file
    
    This function scans the tables directory, collects all table names,
    and generates a new model.tmdl file that includes all tables.
    
    Args:
        output_path: Path where migration output is stored
        
    Returns:
        bool: True if consolidation was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting model table consolidation")
    
    try:
        # Collect all table names from the tables directory
        tables_dir = Path(output_path) / "pbit" / "Model" / "tables"
        if not tables_dir.exists():
            logger.warning(f"Tables directory not found at {tables_dir}")
            return False
            
        all_tables = [table_file.stem for table_file in tables_dir.glob("*.tmdl")]
        if not all_tables:
            logger.warning("No tables found to consolidate")
            return False
            
        logger.info(f"Found {len(all_tables)} tables to consolidate: {all_tables}")
        
        # Create a data model with all tables
        from cognos_migrator.models import DataModel, Table
        combined_model = DataModel(
            name="Model", 
            tables=[Table(name=table_name, columns=[]) for table_name in all_tables]
        )
        
        # Generate a new model.tmdl with all tables
        from cognos_migrator.generators.modules.module_model_file_generator import ModuleModelFileGenerator
        from cognos_migrator.generators.template_engine import TemplateEngine
        
        template_engine = TemplateEngine(str(Path(__file__).parent / "templates"))
        model_generator = ModuleModelFileGenerator(template_engine)
        model_dir = Path(output_path) / "pbit" / "Model"
        model_generator._generate_model_file(combined_model, model_dir)
        
        logger.info(f"Successfully consolidated {len(all_tables)} tables into model.tmdl")
        return True
    except Exception as e:
        logger.error(f"Error consolidating tables into model.tmdl: {e}")
        return False
