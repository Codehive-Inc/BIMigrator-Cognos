#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI server for converting Tableau formulas to DAX expressions.
This server runs independently and can be called from the main conversion process.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from agentic.formula_resolver import FormulaResolver, FormulaAgent
# Import python-dotenv correctly
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Tableau to DAX Converter API",
    description="API for converting Tableau formulas to DAX expressions using LLM",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get LLM configuration from environment variables
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

if not LLM_API_KEY:
    logger.warning("LLM_API_KEY not found in environment variables. LLM functionality will be limited.")
else:
    logger.info(f"Using LLM model: {LLM_MODEL}")

# Pydantic models for request and response
class TableauFormula(BaseModel):
    tableau_formula: str
    table_name: str
    column_mappings: Optional[Dict[str, str]] = None
    dependencies: Optional[List[Dict[str, str]]] = None  # List of dependent calculations with their formulas

class CalculationsData(BaseModel):
    calculations: List[Dict[str, Any]]

class DependencyRequest(BaseModel):
    calculations: List[Dict[str, Any]]
    calculation_name: str

class DAXResponse(BaseModel):
    dax_expression: str
    confidence: float = 1.0  # Confidence score (1.0 = high confidence)
    notes: Optional[str] = None

class TableauConnection(BaseModel):
    class_type: str
    server: Optional[str] = None
    database: Optional[str] = None
    db_schema: Optional[str] = Field(None, alias='schema')  # Use alias for schema
    table: Optional[str] = None
    sql_query: Optional[str] = None
    filename: Optional[str] = None
    connection_type: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = None

class Config:
    allow_population_by_field_name = True

class MCodeResponse(BaseModel):
    m_code: str
    confidence: float = 1.0
    notes: Optional[str] = None

# Helper function to create a prompt for the LLM
def create_conversion_prompt(tableau_formula: str, table_name: str, column_mappings: Dict[str, str] = None, dependencies: List[Dict[str, str]] = None) -> str:
    """
    Create a prompt for the LLM to convert a Tableau formula to DAX.
    
    Args:
        tableau_formula: The Tableau formula to convert
        table_name: The name of the table containing the calculation
        column_mappings: Optional mapping of column names to their display names
        dependencies: Optional list of dependent calculations with their formulas
        
    Returns:
        A prompt string for the LLM
    """
    # Create the prompt with examples and context
    prompt = f"""You are an expert in converting Tableau formulas to Power BI DAX expressions.

TABLE CONTEXT:
Table Name: {table_name}

"""

    # Add dependencies if provided
    if dependencies:
        prompt += "DEPENDENCIES:\n"
        for dep in dependencies:
            prompt += f"[{dep['caption']}] = {dep['formula']}\n"
            if 'dax' in dep and dep['dax']:
                prompt += f"DAX: {dep['dax']}\n"
        prompt += "\n"

    prompt += f"""TABLEAU FORMULA TO CONVERT:
{tableau_formula}

RULES:
1. Use proper DAX syntax and functions
2. Maintain the same logic and behavior
3. Return ONLY the DAX expression, no explanations
4. For column references:
   - Use '[Column]' for columns in the current table
   - Use 'TableName'[Column] for columns from other tables
   - ALWAYS enclose table names in single quotes, e.g. 'TableName'[Column]
   - For calculation references, use their DAX expressions from DEPENDENCIES
5. For Tableau functions:
   - SUM() -> SUM()
   - AVG() -> AVERAGE()
   - MIN() -> MIN()
   - MAX() -> MAX()
   - COUNT() -> COUNT()
   - COUNTD() -> DISTINCTCOUNT()
   - ATTR() -> MIN()
6. For string operations:
   - Use & for concatenation
   - Use CONCATENATE() for multiple strings
7. For case statements:
   - Use SWITCH(TRUE(), condition1, result1, condition2, result2, ...)"""
    
    # Add column mapping information if provided
    if column_mappings:
        prompt += "\n\nColumn mappings (Tableau -> DAX):\n"
        for tableau_col, dax_col in column_mappings.items():
            prompt += f"{tableau_col} -> {dax_col}\n"
    
    prompt += "\n\nProvide ONLY the DAX expression, no explanations or comments."
    
    return prompt

def create_m_code_prompt(connection: TableauConnection) -> str:
    """Create a prompt for the LLM to generate M code.
    
    Args:
        connection: The connection information
        
    Returns:
        A prompt string for the LLM
    """
    prompt = [
        "Generate Power BI M code for the following Tableau connection information:",
        "Rules:",
        "1. Use only valid Power BI M code syntax",
        "2. Include proper error handling where appropriate",
        "3. Follow Power BI best practices for data source connections",
        "4. Return only the M code, no explanations",
        "5. Use proper variable names and formatting",
        "6. For Excel files, use Excel.Workbook and specify the table name in Item",
        "7. For federated connections to Excel, use the Excel.Workbook function",
        "",
        "Connection details:"
    ]
    
    # Add connection details to prompt
    prompt.append(f"Connection type: {connection.class_type}")
    
    if connection.server:
        prompt.append(f"Server: {connection.server}")
    if connection.database:
        prompt.append(f"Database: {connection.database}")
    if connection.db_schema:
        prompt.append(f"Schema: {connection.db_schema}")
    if connection.table:
        prompt.append(f"Table: {connection.table}")
    if connection.sql_query:
        prompt.append(f"SQL Query:\n{connection.sql_query}")
    if connection.filename:
        prompt.append(f"File: {connection.filename}")
    if connection.additional_properties:
        prompt.append("Additional properties:")
        for key, value in connection.additional_properties.items():
            prompt.append(f"  {key}: {value}")
    
    return "\n".join(prompt)

# Function to call LLM API
def clean_dax_expression(dax_expression: str) -> str:
    """
    Clean the DAX expression from the LLM to ensure it is properly formatted.
    
    Args:
        dax_expression: The DAX expression from the LLM
        
    Returns:
        The cleaned DAX expression
    """
    # Remove any markdown code block markers and ensure no whitespace after ```
    dax_expression = dax_expression.replace('```dax\n', '').replace('```\n', '').replace('```', '').strip()
    
    # Remove any leading/trailing quotes
    dax_expression = dax_expression.strip('"').strip("'")
    
    # Replace HTML entities with actual characters
    html_entities = {
        '&amp;': '&',
        '&#x27;': "'",
        '&quot;': '"',
        '&lt;': '<',
        '&gt;': '>'
    }
    for entity, char in html_entities.items():
        dax_expression = dax_expression.replace(entity, char)
    
    # Clean up any double spaces
    dax_expression = ' '.join(dax_expression.split())
    
    # Ensure proper spacing around operators
    operators = ['+', '-', '*', '/', '=', '<', '>', '<=', '>=', '<>', '&']
    for op in operators:
        dax_expression = dax_expression.replace(op, f' {op} ')
    
    # Clean up any resulting double spaces
    dax_expression = ' '.join(dax_expression.split())
    
    return dax_expression

async def call_llm_api(prompt: str) -> str:
    """
    Call the LLM API to convert a Tableau formula to DAX or generate M code.
    
    Args:
        prompt: The prompt for the LLM
        
    Returns:
        The DAX expression or M code from the LLM
    """
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    try:
        # Determine which LLM API to use based on the model name
        if "claude" in LLM_MODEL.lower():
            # Call Anthropic Claude API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": LLM_MODEL or "claude-3-sonnet-20240229",
                        "max_tokens": 500,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("content", [{}])[0].get("text", "").strip()
                    # Clean the response text
                    response_text = clean_dax_expression(response_text)
                    return response_text
                else:
                    logger.error(f"Error from Claude API: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=500, detail=f"Claude API error: {response.text}")
        
        elif "gpt" in LLM_MODEL.lower():
            # Call OpenAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": LLM_MODEL or "gpt-4",
                        "messages": [
                            {"role": "system", "content": "You are a DAX formula expert that converts Tableau formulas to DAX."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result["choices"][0]["message"]["content"].strip()
                    # Clean the response text
                    response_text = clean_dax_expression(response_text)
                    return response_text
                else:
                    logger.error(f"Error from OpenAI API: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=500, detail=f"OpenAI API error: {response.text}")
        
        else:
            # Default to a custom API endpoint if model is not recognized
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    os.getenv("CUSTOM_LLM_ENDPOINT", "http://localhost:11434/api/generate"),
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": LLM_MODEL or "default",
                        "prompt": prompt,
                        "temperature": 0.2,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Adapt this based on your custom LLM API response format
                    response_text = result.get("response", "").strip()
                    # Clean the response text
                    response_text = clean_dax_expression(response_text)
                    return response_text
                else:
                    logger.error(f"Error from custom LLM API: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=500, detail=f"Custom LLM API error: {response.text}")
    
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        raise HTTPException(status_code=500, detail=f"Error calling LLM API: {str(e)}")

# API endpoints

@app.post("/convert", response_model=DAXResponse)
async def convert_formula(formula_request: TableauFormula):
    """
    Convert a Tableau formula to a DAX expression.
    
    Args:
        formula_request: The Tableau formula request
        
    Returns:
        The DAX expression response
    """
    try:
        # Log the incoming request
        logger.info(f"Converting formula: {formula_request.tableau_formula}")
        logger.info(f"Table name: {formula_request.table_name}")
        
        # Validate the formula
        if not formula_request.tableau_formula or not formula_request.tableau_formula.strip():
            raise ValueError("Empty formula provided")
            
        # Create the prompt for the LLM
        prompt = create_conversion_prompt(
            formula_request.tableau_formula,
            formula_request.table_name,
            formula_request.column_mappings,
            formula_request.dependencies
        )
        
        # Call the LLM API if available
        if LLM_API_KEY:
            try:
                # Log the conversion attempt
                logger.info("Calling LLM API for conversion...")
                
                # Call LLM
                dax_expression = await call_llm_api(prompt)
                
                # Basic validation of the response
                if not dax_expression or not dax_expression.strip():
                    raise ValueError("Empty response from LLM")
                    
                # Log success
                logger.info(f"Successfully converted to: {dax_expression}")
                
                return DAXResponse(
                    dax_expression=dax_expression,
                    confidence=0.9,
                    notes=f"Converted using {LLM_MODEL or 'LLM'}"
                )
            except Exception as e:
                logger.error(f"LLM conversion failed: {e}")
                # Return specific error message
                error_msg = str(e)
                if "Empty response" in error_msg:
                    error_msg = "LLM returned empty response. Please try again."
                elif "name 'caption' is not defined" in error_msg:
                    error_msg = "Error accessing column name. Please check column references."
                raise HTTPException(
                    status_code=500,
                    detail=error_msg
                )
        else:
            # No LLM API key, return an error
            logger.error("No LLM API key configured")
            raise HTTPException(
                status_code=500,
                detail="No LLM API key configured. Please set the LLM_API_KEY environment variable."
            )  
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error converting formula: {e}")
        raise HTTPException(status_code=500, detail=f"Error converting formula: {str(e)}")

@app.post("/convert/tableau-to-m-code")
async def generate_m_code(connection: TableauConnection) -> MCodeResponse:
    """Generate M code for a Tableau connection.
    
    Args:
        connection: The connection information
        
    Returns:
        The M code response
    """
    try:
        # Create prompt for LLM
        prompt = create_m_code_prompt(connection)
        
        # Call LLM API
        m_code = await call_llm_api(prompt)
        
        # Clean and validate the M code
        m_code = m_code.strip()
        
        # For Excel connections, generate M code directly
        if connection.class_type == 'excel-direct':
            filename = connection.filename.replace('\\', '/')
            table_name = connection.table.strip('[]')
            m_code = f'''let
    Source = Excel.Workbook(File.Contents("{filename}"), null, true),
    {table_name}_Table = Source{{[Item="{table_name}", Kind="Sheet"]}},
    #"Promoted Headers" = Table.PromoteHeaders({table_name}_Table, [PromoteAllScalars=true])
in
    #"Promoted Headers"'''
        else:
            # For other connections, use the LLM-generated M code
            if not m_code.startswith('let'):
                m_code = f'let\n    Source = {m_code}\nin\n    Source'
        
        # Unescape HTML entities
        m_code = m_code.replace('&quot;', '"')
        m_code = m_code.replace('&amp;', '&')
        m_code = m_code.replace('&lt;', '<')
        m_code = m_code.replace('&gt;', '>')
        m_code = m_code.replace('&#x27;', "'")
        
        return MCodeResponse(
            m_code=m_code,
            confidence=1.0
        )
        
    except Exception as e:
        logger.error(f"Error generating M code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy", 
        "llm_available": bool(LLM_API_KEY),
        "llm_model": LLM_MODEL or "not specified"
    }

# Run the server if executed directly
@app.post("/resolve_dependencies")
async def resolve_dependencies(request: DependencyRequest):
    """
    Resolve dependencies for a Tableau calculation using the agentic framework.
    
    Args:
        request: The dependency resolution request containing calculations and target calculation name
        
    Returns:
        The resolved dependencies and calculation chain with resolved formulas
    """
    try:
        logger.info(f"Resolving dependencies for calculation: {request.calculation_name}")
        
        # Initialize resolver with calculations
        resolver = FormulaResolver(calculations_data={"calculations": request.calculations})
        
        # Build a lookup map for calculations by caption
        calc_by_caption = {}
        calc_by_name = {}
        for calc in request.calculations:
            calc_by_caption[calc["FormulaCaptionTableau"]] = calc
            calc_by_name[calc["TableauName"]] = calc
            
        # Find the target calculation
        target_calc = None
        for calc in request.calculations:
            if (calc["FormulaCaptionTableau"] == request.calculation_name or 
                calc["TableauName"] == request.calculation_name):
                target_calc = calc
                break
                
        if not target_calc:
            raise HTTPException(
                status_code=404, 
                detail=f"Calculation not found: {request.calculation_name}"
            )
            
        logger.info(f"Found target calculation: {target_calc['FormulaCaptionTableau']}")
        
        # Get the calculation chain
        chain = resolver.resolve_calculation_chain(target_calc["TableauName"])
        logger.info(f"Resolved chain length: {len(chain)}")
        
        # Process each calculation in the chain
        processed_chain = []
        dependencies = set()
        for node in chain:
            # Get the original calculation
            orig_calc = calc_by_name.get(node.tableau_name)
            if not orig_calc:
                continue
                
            # Extract dependencies
            node_deps = resolver.extract_dependencies(node.formula)
            dependencies.update(node_deps)
            
            # Add to processed chain
            processed_chain.append({
                "caption": node.caption,
                "formula": node.formula,
                "dax": orig_calc.get("FormulaDax", "")
            })
            
            logger.info(f"Processed calculation: {node.caption}")
            logger.info(f"Dependencies found: {', '.join(node_deps) if node_deps else 'none'}")
        
        # Format response
        response = {
            "calculation": {
                "caption": target_calc["FormulaCaptionTableau"],
                "formula": target_calc["FormulaTableau"],
                "dax": target_calc["FormulaDax"]
            },
            "dependencies": list(dependencies),
            "chain": processed_chain
        }
        
        logger.info(f"Successfully resolved dependencies for {request.calculation_name}")
        return response
        
    except HTTPException as he:
        logger.error(f"HTTP error during dependency resolution: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Error during dependency resolution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
