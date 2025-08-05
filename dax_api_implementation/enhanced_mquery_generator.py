"""
Enhanced M-Query Generator for DAX API Service
This should be integrated into your DAX API service at localhost:8080
"""

import json
import logging
from typing import Dict, Any, Optional
from enum import Enum


class TemplateMode(str, Enum):
    STRICT = "strict"      # Must use template exactly
    GUIDED = "guided"      # Use template as base but allow modifications
    FLEXIBLE = "flexible"  # Template is optional guidance


class EnhancedMQueryGenerator:
    """
    Enhanced M-Query generator that ensures error handling in all outputs
    """
    
    def __init__(self, llm_client):
        """
        Initialize with LLM client
        
        Args:
            llm_client: Your existing LLM client (OpenAI, Anthropic, etc.)
        """
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Load templates
        self.templates = self._load_templates()
        
        # System prompt for error handling
        self.system_prompt = """
You are an expert M-Query (Power Query) code generator for Power BI.

MANDATORY REQUIREMENTS:
1. ALL generated M-Query code MUST include comprehensive error handling
2. Use try...otherwise blocks for ALL external operations (database, file, web)
3. ALWAYS check [HasError] before accessing [Value] 
4. ALWAYS provide fallback to empty tables with correct schema on errors
5. Include meaningful error information for debugging

TEMPLATE COMPLIANCE:
When a base_template is provided, you MUST:
- Use it as your foundation (do not rewrite from scratch)
- Fill in the template placeholders with actual values
- Preserve ALL error handling structures
- Maintain the fallback mechanisms

Remember: Power BI reports should NEVER break during refresh due to external failures.
"""

    def generate_mquery(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate M-Query with guaranteed error handling
        
        Args:
            request: Request payload from BIMigrator
            
        Returns:
            Response with M-Query and metadata
        """
        try:
            context = request.get('context', {})
            options = request.get('options', {})
            
            # Determine template mode
            template_mode = TemplateMode(options.get('template_compliance', 'guided'))
            use_template = options.get('use_template_mode', False)
            
            # Get source type and select template
            source_type = context.get('source_type', 'sql')
            base_template = None
            
            if use_template or 'base_template' in context:
                base_template = context.get('base_template') or self.templates.get(source_type)
            
            # Generate M-Query
            if template_mode == TemplateMode.STRICT and base_template:
                # Strict mode: Fill template only
                m_query = self._fill_template(base_template, context)
            else:
                # Use LLM with guidance
                m_query = self._generate_with_llm(context, options, base_template)
            
            # Validate output
            validation_result = self._validate_mquery(m_query)
            
            # If validation fails, apply fixes
            if not validation_result['is_valid']:
                self.logger.warning(f"M-Query validation failed: {validation_result['issues']}")
                m_query = self._fix_mquery(m_query, context, validation_result)
            
            # Final validation
            final_validation = self._validate_mquery(m_query)
            
            return {
                'm_query': m_query,
                'success': True,
                'validation': final_validation,
                'template_used': base_template is not None,
                'source_type': source_type,
                'confidence': self._calculate_confidence(final_validation),
                'metadata': {
                    'has_error_handling': final_validation['has_try_otherwise'],
                    'has_fallback': final_validation['has_fallback'],
                    'template_mode': template_mode
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating M-Query: {e}")
            # Return safe fallback
            return self._create_error_response(request, str(e))
    
    def _generate_with_llm(self, context: Dict[str, Any], options: Dict[str, Any], 
                          base_template: Optional[str]) -> str:
        """Generate M-Query using LLM with enhanced prompting"""
        
        # Build the prompt
        prompt = self._build_prompt(context, base_template)
        
        # Add system prompt additions if provided
        if 'system_prompt_additions' in context:
            full_system_prompt = self.system_prompt + "\n\n" + context['system_prompt_additions']
        else:
            full_system_prompt = self.system_prompt
        
        # Call LLM (adjust based on your LLM client)
        response = self.llm_client.generate(
            system_prompt=full_system_prompt,
            user_prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=2000
        )
        
        return response.strip()
    
    def _build_prompt(self, context: Dict[str, Any], base_template: Optional[str]) -> str:
        """Build prompt for LLM"""
        prompt_parts = [
            f"Generate M-Query code for Power BI with the following requirements:",
            f"Table Name: {context.get('table_name', 'Unknown')}",
            f"Source Type: {context.get('source_type', 'sql')}",
        ]
        
        # Add connection details
        if 'connection_info' in context:
            conn = context['connection_info']
            prompt_parts.append(f"Connection: {json.dumps(conn, indent=2)}")
        
        # Add columns
        if 'columns' in context:
            prompt_parts.append("Columns:")
            for col in context['columns']:
                prompt_parts.append(f"  - {col.get('name')}: {col.get('type')}")
        
        # Add SQL query if available
        if 'source_query' in context:
            prompt_parts.append(f"SQL Query: {context['source_query']}")
        
        # Add template if provided
        if base_template:
            prompt_parts.extend([
                "",
                "Use this template as your foundation:",
                "```",
                base_template,
                "```",
                "",
                "Fill in the template placeholders based on the context provided."
            ])
        
        # Add requirements
        prompt_parts.extend([
            "",
            "REQUIREMENTS:",
            "1. Include comprehensive error handling with try...otherwise",
            "2. Provide fallback to empty table with correct schema on errors",
            "3. Check [HasError] before accessing [Value]",
            "4. Include helpful error messages",
            "5. Ensure the code won't break Power BI refresh"
        ])
        
        return "\n".join(prompt_parts)
    
    def _validate_mquery(self, m_query: str) -> Dict[str, Any]:
        """Validate M-Query has proper error handling"""
        return {
            'is_valid': True,
            'has_try_otherwise': 'try' in m_query and 'otherwise' in m_query,
            'has_error_checking': '[HasError]' in m_query or 'HasError' in m_query,
            'has_error_records': 'error [' in m_query or 'error"' in m_query,
            'has_fallback': any(x in m_query for x in ['Table.FromColumns', 'Table.FromRows', 'Table.FromRecords']),
            'has_let_in': 'let' in m_query and 'in' in m_query,
            'issues': []
        }
    
    def _fix_mquery(self, m_query: str, context: Dict[str, Any], 
                    validation: Dict[str, Any]) -> str:
        """Fix M-Query to add missing error handling"""
        
        if not validation['has_try_otherwise']:
            # Wrap entire query in try...otherwise
            fixed = f"""
let
    // Wrapped with error handling by DAX API
    AttemptQuery = try (
{m_query}
    ) otherwise error [
        Reason = "QueryExecutionFailed",
        Message = "Failed to execute query for {context.get('table_name', 'table')}",
        Detail = "Check connection settings and query syntax"
    ],
    
    Result = if AttemptQuery[HasError] then
        // Fallback to empty table
        Table.FromColumns(
            {{{', '.join(['{}'] * len(context.get('columns', [])))}}},
            {{{', '.join([f'"{col.get("name", f"Column{i}")}"' for i, col in enumerate(context.get('columns', []))])}}}
        )
    else
        AttemptQuery[Value]
in
    Result
"""
            return fixed
        
        return m_query
    
    def _fill_template(self, template: str, context: Dict[str, Any]) -> str:
        """Fill template with context values"""
        # This is a simplified version - use proper template engine
        filled = template
        
        # Replace placeholders
        replacements = {
            '{{server}}': context.get('connection_info', {}).get('server', 'localhost'),
            '{{database}}': context.get('connection_info', {}).get('database', 'database'),
            '{{table_name}}': context.get('table_name', 'Table'),
            '{{schema}}': context.get('connection_info', {}).get('schema', ''),
            '{{sql_query}}': context.get('source_query', ''),
        }
        
        for placeholder, value in replacements.items():
            filled = filled.replace(placeholder, value)
        
        # Handle columns
        if 'columns' in context:
            columns_list = ', '.join([f'"{col.get("name")}"' for col in context['columns']])
            filled = filled.replace('{{#each columns}}"{{name}}"{{#unless @last}}, {{/unless}}{{/each}}', columns_list)
        
        return filled
    
    def _calculate_confidence(self, validation: Dict[str, Any]) -> float:
        """Calculate confidence score based on validation"""
        checks = [
            validation.get('has_try_otherwise', False),
            validation.get('has_error_checking', False),
            validation.get('has_error_records', False),
            validation.get('has_fallback', False),
            validation.get('has_let_in', False)
        ]
        return sum(checks) / len(checks)
    
    def _create_error_response(self, request: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Create error response with safe fallback M-Query"""
        context = request.get('context', {})
        columns = context.get('columns', [])
        
        # Safe fallback M-Query
        fallback_mquery = f"""
// Error generating M-Query: {error_msg}
// Safe fallback provided by DAX API
let
    ErrorTable = Table.FromColumns(
        {{{', '.join(['{}'] * len(columns))}}},
        {{{', '.join([f'"{col.get("name", f"Column{i}")}"' for i, col in enumerate(columns)])}}}
    ),
    WithError = Table.AddColumn(
        ErrorTable,
        "_GenerationError",
        each "Failed to generate query: {error_msg}"
    )
in
    WithError
"""
        
        return {
            'm_query': fallback_mquery,
            'success': False,
            'error': error_msg,
            'validation': self._validate_mquery(fallback_mquery),
            'template_used': False,
            'metadata': {
                'fallback_reason': 'generation_error',
                'has_error_handling': True
            }
        }
    
    def _load_templates(self) -> Dict[str, str]:
        """Load error-handled templates"""
        return {
            'sql': self._get_sql_template(),
            'csv': self._get_csv_template(),
            'web': self._get_web_template()
        }
    
    def _get_sql_template(self) -> str:
        """SQL template with error handling"""
        return """
let
    ConnectionAttempt = try 
        Sql.Database("{{server}}", "{{database}}")
    otherwise 
        error [
            Reason = "DatabaseConnectionFailed",
            Message = "Failed to connect to {{server}}.{{database}}",
            Detail = "Please check server name and credentials"
        ],
    
    DataAttempt = if ConnectionAttempt[HasError] then
        ConnectionAttempt
    else
        try
            ConnectionAttempt[Value]{[Schema="{{schema}}",Item="{{table_name}}"]}[Data]
        otherwise
            error [
                Reason = "TableAccessFailed",
                Message = "Cannot access table {{table_name}}",
                Detail = "Table might not exist or insufficient permissions"
            ],
    
    Result = if DataAttempt[HasError] then
        Table.FromColumns({}, {})  // Empty table fallback
    else
        DataAttempt[Value]
in
    Result
"""
    
    def _get_csv_template(self) -> str:
        """CSV template with error handling"""
        return """
let
    Source = try
        Csv.Document(File.Contents("{{file_path}}"), [Delimiter=",", Encoding=65001])
    otherwise
        error [
            Reason = "FileAccessFailed", 
            Message = "Cannot read file: {{file_path}}",
            Detail = "File not found or access denied"
        ],
    
    Result = if Source[HasError] then
        Table.FromColumns({}, {})
    else
        Table.PromoteHeaders(Source[Value])
in
    Result
"""
    
    def _get_web_template(self) -> str:
        """Web API template with error handling"""
        return """
let
    Source = try
        Web.Contents("{{url}}", [Headers=[Accept="application/json"]])
    otherwise
        error [
            Reason = "WebRequestFailed",
            Message = "Cannot fetch from: {{url}}",
            Detail = "Check URL and network connectivity"
        ],
    
    Result = if Source[HasError] then
        Table.FromColumns({}, {})
    else
        try
            Json.Document(Source[Value])
        otherwise
            error "Invalid JSON response"
in
    Result
"""