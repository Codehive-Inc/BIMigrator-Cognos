# Tableau to DAX Conversion API

This FastAPI server provides an API for converting Tableau formulas to Power BI DAX expressions using LLM technology.

## Features

- Convert Tableau formulas to DAX expressions
- Support for Tableau LOD expressions (FIXED, INCLUDE, EXCLUDE)
- Fallback conversion when LLM is not available
- Health check endpoint

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp .env.example .env
```

3. Edit `.env` file and add your OpenAI API key.

## Running the Server

Start the server with:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or run directly:

```bash
python main.py
```

## API Endpoints

### Convert Formula

```
POST /convert
```

Request body:

```json
{
  "tableau_formula": "{ FIXED [FISCAL_WEEK]:SUM(IF [Calculation_1420604241832890368]=6 or [Calculation_1420604241832890368]=7 THEN [serial_count] END)}",
  "table_name": "Custom SQL Query (dlh_nsec_objdb)",
  "column_mappings": {
    "[FISCAL_WEEK]": "FISCAL_WEEK",
    "[serial_count]": "serial_count"
  }
}
```

Response:

```json
{
  "dax_expression": "CALCULATE(\n    SUM('Custom SQL Query (dlh_nsec_objdb)'[serial_count]),\n    FILTER(\n        'Custom SQL Query (dlh_nsec_objdb)',\n        'Custom SQL Query (dlh_nsec_objdb)'[Calculation_1420604241832890368] = 6 || 'Custom SQL Query (dlh_nsec_objdb)'[Calculation_1420604241832890368] = 7\n    ),\n    VALUES('Custom SQL Query (dlh_nsec_objdb)'[FISCAL_WEEK])\n)",
  "confidence": 0.9,
  "notes": "Converted using LLM"
}
```

### Health Check

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "llm_available": true
}
```

## Integration with Tableau to Power BI Converter

This API server is designed to work with the Tableau to Power BI converter. The `calculation_converter.py` module in the main project calls this API to convert Tableau formulas to DAX expressions.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
