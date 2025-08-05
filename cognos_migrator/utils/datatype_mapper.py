"""
Utilities for mapping Cognos data types to Power BI data types.
"""
from typing import Dict, Any, Tuple


def map_cognos_to_powerbi_datatype(item: Dict[str, Any], logger=None) -> Tuple[str, str]:
    """
    Maps Cognos data types to Power BI data types and summarize_by values based on comprehensive mapping rules.
    
    Args:
        item: A dictionary containing data item properties including dataType, dataUsage, name, expression, etc.
        logger: Optional logger for debugging
        
    Returns:
        Tuple[str, str]: The recommended Power BI data type and summarize_by value
    """
    # Extract needed properties
    name = item.get('identifier', '') or item.get('name', '')  # Use 'name' if 'identifier' is not available
    expression = item.get('expression', '')
    data_type = item.get('dataType', '')
    data_usage = item.get('dataUsage', '')
    is_calculation = item.get('type') == 'calculation'
    aggregate = item.get('aggregate', 'none')
    
    # Check for XML datatype value (e.g., 'dateTime')
    xml_datatype = item.get('datatype', '')
    
    # Default fallback
    powerbi_type = "string"
    summarize_by = "none"  # Default summarize_by
    
    # Log input parameters if logger is provided
    if logger:
        logger.debug(f"Mapping data type for {name}: dataType={data_type}, dataUsage={data_usage}, is_calculation={is_calculation}, aggregate={aggregate}, xml_datatype={xml_datatype}")
    
    # Priority Level 0: Check for XML dateTime datatype
    if xml_datatype and xml_datatype.lower() == 'datetime':
        if logger:
            logger.info(f"Found dateTime XML datatype for {name}, setting to datetime")
        return "datetime", "none"
        
    
    # Priority Level 1: Based on dataUsage
    
    # Group A: dataUsage: "0" (Identifier / Key)
    if data_usage == "0":
        # Rule A.1: If dataUsage is "0" AND dataType is "3"
        if data_type == "3":
            # Check name for hints about text nature
            if any(text in name.lower() for text in ['name', 'title', 'desc', 'text', 'code', 'key']):
                powerbi_type = "string"  # Text for descriptive IDs
            else:
                powerbi_type = "string"  # Default to Text for IDs as per instructions
        
        # Rule A.2: If dataUsage is "0" AND dataType is "1" or "2"
        elif data_type in ["1", "2"]:
            powerbi_type = "int64"  # Whole Number for numeric IDs
        
        # Rule A.3: If dataUsage is "0" AND dataType corresponds to a Date/Time type
        elif data_type == "7":  # Assuming "7" is Date/Time
            powerbi_type = "datetime"  # Date/Time for timestamp IDs
        
        # Rule A.4: If dataUsage is "0" AND dataType corresponds to a Boolean type
        elif data_type == "1":  # Assuming "1" can be Boolean
            powerbi_type = "boolean"  # Boolean for boolean IDs (uncommon)
        
        # Rule A.5: If dataUsage is "0" AND dataType is any other value or missing
        else:
            powerbi_type = "string"  # Safe fallback for IDs
    
    # Group B: dataUsage: "1" (Attribute / Dimension)
    elif data_usage == "1":
        # Rule B.1: If dataUsage is "1" AND dataType is "3"
        if data_type == "3":
            powerbi_type = "string"  # Text for dimension attributes
        
        # Rule B.2: If dataUsage is "1" AND dataType is "1" or "2"
        elif data_type in ["1", "2"]:
            # Check if it's likely a boolean
            if data_type == "1" and any(term in name.lower() for term in ["is", "has", "flag", "bool", "yes", "no", "true", "false"]):
                powerbi_type = "boolean"  # Boolean for boolean attributes
            else:
                powerbi_type = "decimal"  # Decimal Number for numeric attributes
        
        # Rule B.3: If dataUsage is "1" AND dataType corresponds to a Date/Time type
        elif data_type == "7":  # Assuming "7" is Date/Time
            powerbi_type = "datetime"  # Date/Time for date attributes
        
        # Rule B.4: If dataUsage is "1" AND dataType corresponds to a Boolean type
        elif data_type == "1" and any(term in name.lower() for term in ["is", "has", "flag", "bool", "yes", "no", "true", "false"]):
            powerbi_type = "boolean"  # Boolean for boolean attributes
        
        # Rule B.5: If dataUsage is "1" AND dataType is any other value or missing
        else:
            powerbi_type = "string"  # Safe fallback for attributes
    
    # Group C: dataUsage: "2" (Fact / Measure)
    elif data_usage == "2":
        # Rule C.1: If dataUsage is "2" AND dataType is "1"
        if data_type == "1":
            powerbi_type = "decimal"  # Decimal Number for numeric facts
        
        # Rule C.2: If dataUsage is "2" AND dataType is "2"
        elif data_type == "2":
            powerbi_type = "decimal"  # Decimal Number for currency facts
        
        # Rule C.3: If dataUsage is "2" AND dataType is "3"
        elif data_type == "3":
            powerbi_type = "int64"  # Whole Number for integer facts
        
        # Rule C.4: If dataUsage is "2" AND dataType corresponds to a Date/Time type
        elif data_type == "7":  # Assuming "7" is Date/Time
            powerbi_type = "decimal"  # Decimal Number for date facts (uncommon)
        
        # Rule C.5: If dataUsage is "2" AND dataType corresponds to a Boolean type
        elif data_type == "1" and any(term in name.lower() for term in ["is", "has", "flag", "bool", "yes", "no", "true", "false"]):
            powerbi_type = "int64"  # Whole Number for boolean facts (0/1)
        
        # Rule C.6: If dataUsage is "2" AND dataType is any other value or missing
        else:
            powerbi_type = "decimal"  # Safe numeric fallback for facts
    
    # Priority Level 2: dataUsage Attribute is Missing or Unknown
    else:
        # For calculations, try to determine type from the expression
        if is_calculation:
            # Rule D.1-D.6: Analyze expression to determine result type
            # This is a simplified version - in a real implementation, you would do more sophisticated parsing
            
            # Check for common aggregation functions that suggest numeric results
            if any(func in expression.lower() for func in ['sum', 'avg', 'average', 'count', 'min', 'max']):
                if 'count' in expression.lower():
                    powerbi_type = "int64"  # Counts typically yield integers
                else:
                    powerbi_type = "decimal"  # Other aggregations typically yield decimals
            
            # Check for division operations which suggest decimal results
            elif '/' in expression:
                powerbi_type = "decimal"  # Division typically yields decimals
            
            # Check for date functions
            elif any(func in expression.lower() for func in ['date', 'time', 'year', 'month', 'day']):
                powerbi_type = "datetime"  # Date functions typically yield dates
            
            # Check for string operations
            elif any(func in expression.lower() for func in ['concat', 'substring', 'trim', 'upper', 'lower']):
                powerbi_type = "string"  # String functions typically yield strings
            
            # Check for boolean operations
            elif any(op in expression for op in ['==', '!=', '<', '>', '<=', '>=', ' and ', ' or ', ' not ']):
                powerbi_type = "boolean"  # Comparison operations typically yield booleans
            
            # Default for calculations based on name hints
            elif any(term in name.lower() for term in ['count', 'sum', 'total', 'avg', 'min', 'max', 'amount']):
                powerbi_type = "decimal"  # Names suggesting aggregations
            elif any(term in name.lower() for term in ['is', 'has', 'flag', 'bool']):
                powerbi_type = "boolean"  # Names suggesting booleans
            elif any(term in name.lower() for term in ['date', 'time', 'year', 'month', 'day']):
                powerbi_type = "datetime"  # Names suggesting dates
            else:
                # Default fallback for calculations
                powerbi_type = "decimal"  # Most calculations yield numbers
        else:
            # Fallback mapping for when dataUsage is not specified and it's not a calculation
            if data_type == "1":
                if any(term in name.lower() for term in ["is", "has", "flag", "bool", "yes", "no", "true", "false"]):
                    powerbi_type = "boolean"  # Boolean
                else:
                    powerbi_type = "decimal"  # Numeric
            elif data_type == "2":
                powerbi_type = "int64"  # Integer
            elif data_type == "3":
                powerbi_type = "decimal"  # Decimal
            elif data_type == "4":
                powerbi_type = "decimal"  # Currency
            elif data_type == "7":
                powerbi_type = "datetime"  # Date/Time
            else:
                powerbi_type = "string"  # Safe fallback
    
    # Determine summarize_by based on the rules
    
    # Rule 1: Identifier (dataUsage: "0")
    if data_usage == "0":
        # Identifiers should not be summarized
        summarize_by = "none"
    
    # Rule 2: Attribute (dataUsage: "1")
    elif data_usage == "1":
        # Attributes should not be summarized
        summarize_by = "none"
    
    # Rule 3: Fact/Measure - Numeric/Currency Source Columns (dataUsage: "2")
    elif data_usage == "2":
        # Look at Cognos aggregate attribute
        if aggregate == "total":
            summarize_by = "sum"
        elif aggregate == "count":
            summarize_by = "count"
        elif aggregate == "average":
            summarize_by = "average"
        elif aggregate == "maximum":
            summarize_by = "max"
        elif aggregate == "minimum":
            summarize_by = "min"
        elif aggregate == "none" or not aggregate:
            # Default for numeric facts is sum
            if powerbi_type in ["decimal", "double", "int64", "currency"]:
                summarize_by = "sum"
            else:
                summarize_by = "none"
        else:
            # Default for other aggregates
            summarize_by = "sum" if powerbi_type in ["decimal", "double", "int64", "currency"] else "none"
    
    # Rule 4: Calculations
    elif is_calculation:
        # For calculated columns that are numeric
        if powerbi_type in ["decimal", "double", "int64", "currency"]:
            summarize_by = "sum"
        # For calculated columns that are categorical
        elif powerbi_type in ["string", "boolean"]:
            summarize_by = "none"
        else:
            summarize_by = "none"
    
    # Default case
    else:
        # For numeric types, default to sum
        if powerbi_type in ["decimal", "double", "int64", "currency"]:
            summarize_by = "sum"
        else:
            summarize_by = "none"
    
    # Log the final mapping if logger is provided
    if logger:
        logger.debug(f"Mapped {name} to Power BI type: {powerbi_type}, summarize_by: {summarize_by}")
    
    return powerbi_type, summarize_by