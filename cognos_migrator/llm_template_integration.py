"""
Integration layer to ensure LLM uses error-handled templates
"""

import json
from typing import Dict, Any
from .templates.mquery.error_handled_templates import get_error_handled_template


def prepare_llm_request_with_template(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare LLM request with template guidance
    
    This ensures the LLM uses our error-handled templates as a base
    """
    # Determine source type
    source_type = context.get('source_type', 'sql')
    
    # Get appropriate template
    template = get_error_handled_template(source_type)
    
    # Enhanced context with template
    enhanced_context = {
        **context,
        'base_template': template,
        'template_instructions': {
            'message': "Use the provided base_template as your starting point",
            'requirements': [
                "Maintain ALL try...otherwise blocks from the template",
                "Keep all error handling structures intact",
                "Only modify the template placeholders with actual values",
                "Preserve the error record structure with Reason, Message, Detail",
                "Ensure fallback to empty table with correct schema",
                "Keep retry logic for web requests"
            ]
        },
        'example_filled_template': _generate_example(source_type, context)
    }
    
    # Enhanced options for DAX API
    enhanced_options = {
        'optimize_for_performance': True,
        'include_comments': True,
        'use_template_mode': True,
        'template_compliance': 'strict',
        'error_handling_required': True,
        'validation_rules': [
            "must_contain_try_otherwise",
            "must_have_fallback_table", 
            "must_check_HasError",
            "must_preserve_schema"
        ]
    }
    
    # System prompt additions
    system_prompt_additions = """
    You are generating M-Query code for Power BI that MUST be resilient to failures.
    
    CRITICAL REQUIREMENTS:
    1. Use the provided base_template as your foundation
    2. ALL database/file/web operations MUST be wrapped in try...otherwise
    3. ALWAYS check [HasError] before accessing [Value]
    4. ALWAYS provide fallback to empty table with correct schema
    5. Include meaningful error messages in error records
    
    The template provided already has proper error handling. 
    Your job is to fill in the template placeholders, not rewrite it.
    """
    
    return {
        'context': enhanced_context,
        'options': enhanced_options,
        'system_prompt_additions': system_prompt_additions
    }


def _generate_example(source_type: str, context: Dict[str, Any]) -> str:
    """Generate a filled example based on context"""
    if source_type == 'sql':
        return f"""
Example of filled template for your reference:

let
    ConnectionAttempt = try 
        Sql.Database("{context.get('server', 'myserver')}", "{context.get('database', 'mydb')}")
    otherwise 
        error [
            Reason = "DatabaseConnectionFailed",
            Message = "Failed to connect to {context.get('server', 'myserver')}.{context.get('database', 'mydb')}",
            Detail = "Please check server name, credentials, and network connectivity"
        ],
    // ... rest of template with actual values
"""
    return ""


def validate_llm_output(m_query: str) -> Dict[str, Any]:
    """
    Validate that LLM output contains required error handling
    """
    validation_result = {
        'is_valid': True,
        'has_try_otherwise': 'try' in m_query and 'otherwise' in m_query,
        'has_error_checking': '[HasError]' in m_query,
        'has_error_records': 'error [' in m_query,
        'has_fallback': 'Table.FromColumns' in m_query or 'Table.FromRows' in m_query,
        'issues': []
    }
    
    # Check each requirement
    if not validation_result['has_try_otherwise']:
        validation_result['is_valid'] = False
        validation_result['issues'].append("Missing try...otherwise blocks")
    
    if not validation_result['has_error_checking']:
        validation_result['is_valid'] = False
        validation_result['issues'].append("Missing [HasError] checks")
    
    if not validation_result['has_fallback']:
        validation_result['is_valid'] = False
        validation_result['issues'].append("Missing fallback table generation")
    
    return validation_result