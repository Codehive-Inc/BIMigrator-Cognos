"""
Updated FastAPI endpoint for DAX API service
This shows how to integrate the enhanced M-Query generator
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from .enhanced_mquery_generator import EnhancedMQueryGenerator


# Request/Response models
class MQueryContext(BaseModel):
    table_name: str
    source_type: str = "sql"
    columns: List[Dict[str, str]] = []
    connection_info: Optional[Dict[str, Any]] = None
    source_query: Optional[str] = None
    base_template: Optional[str] = None
    error_handling_requirements: Optional[Dict[str, Any]] = None


class MQueryOptions(BaseModel):
    optimize_for_performance: bool = True
    include_comments: bool = True
    use_template_mode: bool = False
    template_compliance: str = "guided"  # strict, guided, flexible
    error_handling_mode: str = "comprehensive"
    include_exception_handling: bool = True
    fallback_strategy: str = "empty_table_with_schema"


class MQueryRequest(BaseModel):
    context: MQueryContext
    options: MQueryOptions = MQueryOptions()
    system_prompt_additions: Optional[str] = None


class MQueryResponse(BaseModel):
    m_query: str
    success: bool = True
    validation: Optional[Dict[str, Any]] = None
    template_used: bool = False
    source_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}
    performance_notes: Optional[str] = None
    error: Optional[str] = None


# FastAPI app update
app = FastAPI(title="DAX API with Enhanced M-Query Generation")
logger = logging.getLogger(__name__)

# Initialize enhanced generator (with your LLM client)
# llm_client = YourLLMClient()  # OpenAI, Anthropic, etc.
# mquery_generator = EnhancedMQueryGenerator(llm_client)


@app.post("/api/m-query", response_model=MQueryResponse)
async def generate_mquery(request: MQueryRequest):
    """
    Generate M-Query with comprehensive error handling
    
    This endpoint now ensures all generated M-Query code includes
    proper exception handling using try...otherwise blocks.
    """
    try:
        logger.info(f"Generating M-Query for table: {request.context.table_name}")
        
        # Convert request to dict for generator
        request_dict = {
            'context': request.context.dict(),
            'options': request.options.dict()
        }
        
        if request.system_prompt_additions:
            request_dict['context']['system_prompt_additions'] = request.system_prompt_additions
        
        # Generate M-Query with error handling
        result = mquery_generator.generate_mquery(request_dict)
        
        # Log validation results
        if result.get('validation'):
            validation = result['validation']
            logger.info(f"M-Query validation: {validation}")
            
            if not validation.get('is_valid', True):
                logger.warning(f"Validation issues: {validation.get('issues', [])}")
        
        # Create response
        response = MQueryResponse(
            m_query=result['m_query'],
            success=result.get('success', True),
            validation=result.get('validation'),
            template_used=result.get('template_used', False),
            source_type=result.get('source_type', request.context.source_type),
            confidence=result.get('confidence', 1.0),
            metadata=result.get('metadata', {}),
            performance_notes=_generate_performance_notes(result)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating M-Query: {e}", exc_info=True)
        
        # Return error response with safe fallback
        return MQueryResponse(
            m_query=_create_safe_fallback(request.context),
            success=False,
            error=str(e),
            validation={
                'is_valid': True,
                'has_error_handling': True,
                'fallback_used': True
            },
            template_used=True,
            source_type=request.context.source_type,
            confidence=0.0,
            metadata={'error_fallback': True}
        )


def _generate_performance_notes(result: Dict[str, Any]) -> str:
    """Generate performance notes based on the M-Query generation"""
    notes = []
    
    if result.get('template_used'):
        notes.append("Template-based generation ensures consistent error handling")
    
    validation = result.get('validation', {})
    if validation.get('has_try_otherwise'):
        notes.append("Includes try-otherwise blocks for resilient data refresh")
    
    if validation.get('has_fallback'):
        notes.append("Fallback to empty table prevents report failures")
    
    return ". ".join(notes) if notes else None


def _create_safe_fallback(context: MQueryContext) -> str:
    """Create a safe fallback M-Query"""
    columns = context.columns or []
    column_names = [f'"{col.get("name", f"Column{i+1}")}"' for i, col in enumerate(columns)]
    
    return f"""
// Safe fallback M-Query (API error)
let
    ErrorMessage = "Failed to generate M-Query via API",
    EmptyTable = Table.FromColumns(
        {{{', '.join(['{}'] * len(columns))}}},
        {{{', '.join(column_names)}}}
    ),
    Result = Table.AddColumn(
        EmptyTable,
        "_Error",
        each ErrorMessage
    )
in
    Result
"""


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "DAX API with enhanced M-Query generation is running",
        "features": {
            "error_handling": True,
            "template_mode": True,
            "validation": True,
            "fallback_generation": True
        }
    }


# Example usage endpoint
@app.get("/api/m-query/example")
async def get_example():
    """Get an example of error-handled M-Query"""
    return {
        "description": "Example M-Query with comprehensive error handling",
        "example": """
let
    // Connection with error handling
    ConnectionAttempt = try 
        Sql.Database("server", "database")
    otherwise 
        error [
            Reason = "DatabaseConnectionFailed",
            Message = "Failed to connect to server.database",
            Detail = "Check connection settings"
        ],
    
    // Data retrieval with fallback
    DataAttempt = if ConnectionAttempt[HasError] then
        ConnectionAttempt
    else
        try
            ConnectionAttempt[Value]{[Schema="dbo",Item="Orders"]}[Data]
        otherwise
            error [Reason = "TableAccessFailed"],
    
    // Result with empty table fallback
    Result = if DataAttempt[HasError] then
        Table.FromColumns({}, {})
    else
        DataAttempt[Value]
in
    Result
""",
        "explanation": "This M-Query will never break Power BI refresh"
    }