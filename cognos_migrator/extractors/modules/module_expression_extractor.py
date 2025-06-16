"""
Module expression extractor for Cognos to Power BI migration
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

from .module_extractor import ModuleExtractor


class ModuleExpressionExtractor(ModuleExtractor):
    """Extracts and converts expressions from a Cognos module"""
    
    def __init__(self, logger=None, llm_client=None):
        """Initialize the module expression extractor
        
        Args:
            logger: Optional logger instance
            llm_client: LLM client for expression conversion
        """
        super().__init__(logger)
        self.llm_client = llm_client
        
    def extract_and_save(self, module_content: str, output_dir: str) -> Dict[str, Any]:
        """Extract expressions and save to JSON
        
        Args:
            module_content: JSON content of the module
            output_dir: Directory to save extracted data
            
        Returns:
            Dictionary with extracted expressions
        """
        # Extract expressions
        expressions = self.extract_expressions(module_content)
        dax_expressions = self.convert_expressions_to_powerbi(expressions)
        
        # Combine into a single structure
        expression_data = {
            'cognos_expressions': expressions,
            'dax_expressions': dax_expressions
        }
        
        # Save to JSON files
        self.save_to_json(expressions, output_dir, "cognos_expressions.json")
        self.save_to_json(dax_expressions, output_dir, "dax_expressions.json")
        self.save_to_json(expression_data, output_dir, "expression_data.json")
        
        return expression_data
    
    def extract_expressions(self, module_content: str) -> Dict[str, Dict[str, str]]:
        """Extract expressions from a module
        
        Args:
            module_content: JSON content of the module
            
        Returns:
            Dictionary mapping query subject identifiers to dictionaries of item expressions
        """
        try:
            # Parse the module content as JSON
            module_data = json.loads(module_content)
            
            expressions_by_subject = {}
            
            # Extract expressions for each query subject
            if "querySubject" in module_data:
                for query_subject in module_data.get("querySubject", []):
                    subject_id = query_subject.get("identifier", "")
                    expressions = {}
                    
                    # Extract expressions from query items
                    for item in query_subject.get("item", []):
                        if "queryItem" in item:
                            query_item = item["queryItem"]
                            identifier = query_item.get("identifier", "")
                            expression = query_item.get("expression", "")
                            
                            if identifier and expression:
                                expressions[identifier] = expression
                    
                    if subject_id and expressions:
                        expressions_by_subject[subject_id] = expressions
            
            return expressions_by_subject
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing module content as JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error extracting expressions: {e}")
            return {}
    
    def convert_expressions_to_powerbi(self, expressions_by_subject: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Convert Cognos expressions to Power BI DAX expressions
        
        Args:
            expressions_by_subject: Dictionary mapping query subject identifiers to dictionaries of item expressions
            
        Returns:
            Dictionary mapping query subject identifiers to dictionaries of converted DAX expressions
        """
        converted_expressions = {}
        
        for subject_id, expressions in expressions_by_subject.items():
            converted = {}
            
            for item_id, expression in expressions.items():
                # Skip simple column references (not calculated)
                if expression == item_id:
                    continue
                
                # Convert the expression
                converted_expression = self._convert_expression_to_dax(expression, subject_id, item_id)
                converted[item_id] = converted_expression
            
            if converted:
                converted_expressions[subject_id] = converted
        
        return converted_expressions
    
    def _convert_expression_to_dax(self, expression: str, subject_id: str, item_id: str) -> str:
        """Convert a single Cognos expression to Power BI DAX
        
        Args:
            expression: Cognos expression
            subject_id: Query subject identifier
            item_id: Query item identifier
            
        Returns:
            Converted DAX expression
        """
        # If we have an LLM client, use it for complex expressions
        if self.llm_client and len(expression) > 10 and not self._is_simple_expression(expression):
            try:
                return self._convert_with_llm(expression, subject_id, item_id)
            except Exception as e:
                self.logger.error(f"Error converting expression with LLM: {e}")
                # Fall back to rule-based conversion
        
        # Rule-based conversion for common patterns
        return self._rule_based_conversion(expression)
    
    def _is_simple_expression(self, expression: str) -> bool:
        """Check if an expression is simple (direct reference or basic operation)
        
        Args:
            expression: Expression to check
            
        Returns:
            True if the expression is simple, False otherwise
        """
        # Simple direct reference
        if not any(op in expression for op in ['+', '-', '*', '/', '(', ')', 'if', 'case', 'when']):
            return True
        
        # Simple arithmetic with at most one operator
        if expression.count('+') + expression.count('-') + expression.count('*') + expression.count('/') <= 1 and '(' not in expression:
            return True
        
        return False
    
    def _convert_with_llm(self, expression: str, subject_id: str, item_id: str) -> str:
        """Convert an expression using the LLM client
        
        Args:
            expression: Cognos expression
            subject_id: Query subject identifier
            item_id: Query item identifier
            
        Returns:
            Converted DAX expression
        """
        if not self.llm_client:
            return expression
        
        prompt = f"""
        Convert the following Cognos expression to Power BI DAX:
        
        Cognos Expression: {expression}
        Table Name: {subject_id}
        Column Name: {item_id}
        
        Return only the DAX expression without any explanation.
        """
        
        response = self.llm_client.generate_text(prompt)
        
        # Clean up the response
        dax_expression = response.strip()
        
        # Remove any markdown code block formatting
        dax_expression = re.sub(r'^```.*\n', '', dax_expression)
        dax_expression = re.sub(r'\n```$', '', dax_expression)
        
        return dax_expression
    
    def _rule_based_conversion(self, expression: str) -> str:
        """Apply rule-based conversion for common Cognos expression patterns
        
        Args:
            expression: Cognos expression
            
        Returns:
            Converted DAX expression
        """
        # Replace common Cognos functions with DAX equivalents
        converted = expression
        
        # Date functions
        converted = re.sub(r'current_date\(\)', 'TODAY()', converted, flags=re.IGNORECASE)
        converted = re.sub(r'current_timestamp\(\)', 'NOW()', converted, flags=re.IGNORECASE)
        converted = re.sub(r'current_time\(\)', 'TIME(HOUR(NOW()), MINUTE(NOW()), SECOND(NOW()))', converted, flags=re.IGNORECASE)
        
        # String functions
        converted = re.sub(r'lower\((.*?)\)', r'LOWER(\1)', converted, flags=re.IGNORECASE)
        converted = re.sub(r'upper\((.*?)\)', r'UPPER(\1)', converted, flags=re.IGNORECASE)
        converted = re.sub(r'substring\((.*?),\s*(.*?),\s*(.*?)\)', r'MID(\1, \2, \3)', converted, flags=re.IGNORECASE)
        converted = re.sub(r'trim\((.*?)\)', r'TRIM(\1)', converted, flags=re.IGNORECASE)
        
        # Numeric functions
        converted = re.sub(r'round\((.*?),\s*(.*?)\)', r'ROUND(\1, \2)', converted, flags=re.IGNORECASE)
        converted = re.sub(r'ceiling\((.*?)\)', r'CEILING(\1)', converted, flags=re.IGNORECASE)
        converted = re.sub(r'floor\((.*?)\)', r'FLOOR(\1)', converted, flags=re.IGNORECASE)
        
        # Conditional functions
        converted = re.sub(r'nullif\((.*?),\s*(.*?)\)', r'IF(\1 = \2, BLANK(), \1)', converted, flags=re.IGNORECASE)
        
        # Replace if-then-else pattern
        if_pattern = r'if\s+\((.*?)\)\s+then\s+(.*?)\s+else\s+(.*?)\s+endif'
        converted = re.sub(if_pattern, r'IF(\1, \2, \3)', converted, flags=re.IGNORECASE)
        
        # Replace case-when pattern (simplified)
        case_pattern = r'case\s+when\s+(.*?)\s+then\s+(.*?)\s+else\s+(.*?)\s+end'
        converted = re.sub(case_pattern, r'IF(\1, \2, \3)', converted, flags=re.IGNORECASE)
        
        return converted
