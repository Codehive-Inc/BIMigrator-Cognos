# M-Query Generation API Documentation

## Overview

This document outlines the requirements for implementing an M-Query generation endpoint in the FastAPI service. The endpoint will generate optimized Power BI M-Query expressions based on provided context information.

## API Endpoint Specification

### Generate M-Query

```
POST /api/m-query
```

This endpoint generates an optimized M-Query expression for Power BI based on the provided table context, source query, and report specification.

#### Request Body

```json
{
  "context": {
    "table_name": "string",
    "columns": [
      {
        "name": "string",
        "data_type": "string",
        "description": "string (optional)"
      }
    ],
    "source_query": "string (optional)",
    "report_spec": "string (optional)",
    "data_sample": "object (optional)"
  },
  "options": {
    "optimize_for_performance": true,
    "include_comments": true
  }
}
```

**Field Descriptions:**

- `context`: Contains all information needed to generate the M-Query
  - `table_name`: Name of the table for which the M-Query is being generated
  - `columns`: Array of column definitions
    - `name`: Column name
    - `data_type`: Data type as a string (e.g., "STRING", "INTEGER", "DATETIME")
    - `description`: Optional description of the column
  - `source_query`: Optional SQL query that was used as the source for this table
  - `report_spec`: Optional XML string containing relevant parts of the Cognos report specification
  - `data_sample`: Optional sample data for the table (can be partial)

- `options`: Configuration options for M-Query generation
  - `optimize_for_performance`: Whether to optimize the M-Query for performance
  - `include_comments`: Whether to include explanatory comments in the generated M-Query

#### Response Body

```json
{
  "m_query": "string",
  "performance_notes": "string (optional)",
  "confidence": 0.95
}
```

**Field Descriptions:**

- `m_query`: The generated M-Query expression as a string
- `performance_notes`: Optional notes about performance considerations
- `confidence`: A score between 0 and 1 indicating the confidence in the generated M-Query

#### Example Request

```json
{
  "context": {
    "table_name": "Customers",
    "columns": [
      {
        "name": "CustomerID",
        "data_type": "STRING"
      },
      {
        "name": "FirstName",
        "data_type": "STRING"
      },
      {
        "name": "LastName",
        "data_type": "STRING"
      },
      {
        "name": "Email",
        "data_type": "STRING"
      },
      {
        "name": "Age",
        "data_type": "INTEGER"
      },
      {
        "name": "RegistrationDate",
        "data_type": "DATETIME"
      }
    ],
    "source_query": "SELECT * FROM Customers WHERE Age > 18"
  },
  "options": {
    "optimize_for_performance": true,
    "include_comments": true
  }
}
```

#### Example Response

```json
{
  "m_query": "// M-Query for Customers table\nlet\n    Source = Sql.Database(\"server\", \"database\", [Query=\"SELECT * FROM Customers WHERE Age > 18\"]),\n    #\"Changed Type\" = Table.TransformColumnTypes(Source,{\n        {\"CustomerID\", type text},\n        {\"FirstName\", type text},\n        {\"LastName\", type text},\n        {\"Email\", type text},\n        {\"Age\", Int64.Type},\n        {\"RegistrationDate\", type datetime}\n    })\nin\n    #\"Changed Type\"",
  "performance_notes": "Consider adding an index on the Age column to improve query performance.",
  "confidence": 0.95
}
```

### Health Check

```
GET /api/health
```

Returns the health status of the M-Query generation service.

#### Response Body

```json
{
  "status": "healthy",
  "llm_available": true,
  "version": "1.0.0"
}
```

## Implementation Notes

1. The LLM should be prompted to generate M-Query expressions that:
   - Follow Power BI best practices
   - Include proper data type transformations
   - Are optimized for performance
   - Include helpful comments when requested

2. Error handling should include:
   - Validation of input parameters
   - Graceful fallback if the LLM is unavailable
   - Detailed error messages for debugging

3. The API should be designed to handle both simple and complex table structures, with appropriate optimizations for each.

4. Consider implementing caching for similar requests to improve performance and reduce LLM API costs.

5. The endpoint should be secured appropriately if deployed in a production environment.
