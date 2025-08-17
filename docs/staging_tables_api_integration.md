# Staging Tables API Integration Guide

## Overview

The staging table functionality integrates with the Fast API endpoints defined in the API I/O reference. This document shows how the staging table system calls these endpoints and what data flows between them.

## API Endpoints Used by Staging Tables

### 1. **SQL Analysis Endpoint** (`/api/sql/analyze-package`)

**Purpose**: Analyze Cognos package XML to extract relationships and join patterns.

#### Input from Staging System:
```json
{
  "package_xml": "<cognos package XML content>",
  "target_database": "sqlserver",
  "analysis_options": {
    "include_relationships": true,
    "extract_calculations": true,
    "detect_join_patterns": true,
    "identify_composite_keys": true
  },
  "staging_context": {
    "analyze_for_staging": true,
    "min_join_confidence": 0.8,
    "table_classification": true
  }
}
```

#### Expected Output:
```json
{
  "query_subjects": [
    {
      "name": "PURCHASE_ORDER_LINE",
      "sql_definition": "SELECT * FROM PURCHASE_ORDER_LINE",
      "table_type": "fact",
      "columns": ["PO_NUMBER", "SITE_NUMBER", "ITEM_NUMBER", "QUANTITY"]
    },
    {
      "name": "ITEM_SITE_EXTRACT", 
      "sql_definition": "SELECT * FROM ITEM_SITE_EXTRACT",
      "table_type": "dimension",
      "columns": ["SITE_NUMBER", "ITEM_NUMBER", "DESCRIPTION", "QTY_ON_HAND"]
    }
  ],
  "relationships": [
    {
      "from_table": "PURCHASE_ORDER_LINE",
      "to_table": "ITEM_SITE_EXTRACT",
      "relationship_type": "many-to-one",
      "join_columns": [
        {"left": "SITE_NUMBER", "right": "SITE_NUMBER"},
        {"left": "ITEM_NUMBER", "right": "ITEM_NUMBER"}
      ],
      "composite_key": true,
      "confidence": 0.9
    }
  ],
  "staging_recommendations": [
    {
      "staging_table_name": "Staging_PO_Items",
      "source_tables": ["PURCHASE_ORDER_LINE", "ITEM_SITE_EXTRACT"],
      "join_complexity": "medium",
      "shared_key_needed": "SITE_NUMBER_ITEM_NUMBER_Key"
    }
  ],
  "processing_time": 3.2
}
```

#### Code Integration:
```python
# In sql_join_analyzer.py
def analyze_package_with_llm(self, package_xml: str) -> List[JoinPattern]:
    api_payload = {
        "package_xml": package_xml,
        "target_database": "sqlserver", 
        "analysis_options": {
            "include_relationships": True,
            "extract_calculations": True,
            "detect_join_patterns": True,
            "identify_composite_keys": True
        },
        "staging_context": {
            "analyze_for_staging": True,
            "min_join_confidence": 0.8,
            "table_classification": True
        }
    }
    
    response = self.llm_service_client.call_api_endpoint(
        endpoint="/api/sql/analyze-package",
        method="POST",
        payload=api_payload
    )
    
    # Convert response to JoinPattern objects
    patterns = []
    for rel in response.get("relationships", []):
        pattern = JoinPattern(
            left_table=rel["from_table"],
            right_table=rel["to_table"], 
            left_columns=[col["left"] for col in rel["join_columns"]],
            right_columns=[col["right"] for col in rel["join_columns"]],
            join_type=self._map_relationship_to_join_type(rel["relationship_type"]),
            join_expression=self._build_join_expression(rel["join_columns"]),
            confidence=rel.get("confidence", 0.8),
            source="llm_package_analysis",
            composite_key=rel.get("composite_key", False)
        )
        patterns.append(pattern)
    
    return patterns
```

### 2. **M-Query Staging Endpoint** (`/api/mquery/staging`)

**Purpose**: Generate optimized M-queries for staging tables with shared keys.

#### Input from Staging System:
```json
{
  "table_name": "Staging_PO_Items",
  "source_info": {
    "source_type": "sqlserver",
    "server": "prod-sql-01",
    "database": "SalesDB",
    "source_tables": ["PURCHASE_ORDER_LINE", "ITEM_SITE_EXTRACT"]
  },
  "join_patterns": [
    {
      "left_table": "PURCHASE_ORDER_LINE",
      "right_table": "ITEM_SITE_EXTRACT",
      "left_columns": ["SITE_NUMBER", "ITEM_NUMBER"],
      "right_columns": ["SITE_NUMBER", "ITEM_NUMBER"],
      "join_type": "LEFT",
      "composite_key": true
    }
  ],
  "shared_keys": [
    {
      "name": "SITE_ITEM_Key",
      "source_columns": ["SITE_NUMBER", "ITEM_NUMBER"],
      "is_composite": true,
      "surrogate_key_formula": "Text.From([SITE_NUMBER]) & \"_\" & Text.From([ITEM_NUMBER])"
    }
  ],
  "etl_options": {
    "add_shared_keys": true,
    "optimize_for_powerbi": true,
    "handle_composite_keys": true,
    "add_audit_columns": false
  },
  "powerbi_requirements": [
    "Generate efficient star schema relationships",
    "Use proper data types for performance", 
    "Implement shared keys for relationship optimization",
    "Handle composite keys with surrogate keys",
    "Optimize for VertiPaq engine compression"
  ]
}
```

#### Expected Output:
```json
{
  "m_query": "let\n    Source = Sql.Database(\"prod-sql-01\", \"SalesDB\"),\n    PO_Lines = Source{[Schema=\"dbo\",Item=\"PURCHASE_ORDER_LINE\"]}[Data],\n    Items = Source{[Schema=\"dbo\",Item=\"ITEM_SITE_EXTRACT\"]}[Data],\n    JoinedData = Table.NestedJoin(PO_Lines, {\"SITE_NUMBER\", \"ITEM_NUMBER\"}, Items, {\"SITE_NUMBER\", \"ITEM_NUMBER\"}, \"Items\", JoinKind.LeftOuter),\n    ExpandedItems = Table.ExpandTableColumn(JoinedData, \"Items\", {\"DESCRIPTION\", \"QTY_ON_HAND\"}, {\"Item_DESCRIPTION\", \"Item_QTY_ON_HAND\"}),\n    AddedSharedKey = Table.AddColumn(ExpandedItems, \"SITE_ITEM_Key\", each Text.From([SITE_NUMBER]) & \"_\" & Text.From([ITEM_NUMBER]), type text)\nin\n    AddedSharedKey",
  "etl_patterns_applied": [
    "nested_join_optimization",
    "shared_key_generation", 
    "composite_key_handling",
    "powerbi_optimization"
  ],
  "performance_notes": "Query uses nested joins for optimal performance. Shared key created for efficient relationships.",
  "confidence": 0.92,
  "processing_time": 2.3,
  "metadata": {
    "table_name": "Staging_PO_Items",
    "request_type": "staging_mquery",
    "join_complexity": "medium",
    "optimization_level": "high"
  },
  "recommendations": [
    "Monitor refresh performance with large datasets",
    "Consider incremental refresh for fact tables",
    "Validate shared key uniqueness in source data"
  ]
}
```

#### Code Integration:
```python
# In staging_mquery_converter.py  
def _generate_m_query_with_llm(self, staging_definition, shared_keys, connection_info, settings):
    api_payload = {
        "table_name": staging_definition.name,
        "source_info": {
            "source_type": "sqlserver",
            "server": connection_info.get("server", "server"),
            "database": connection_info.get("database", "database"), 
            "source_tables": staging_definition.source_tables
        },
        "join_patterns": [
            {
                "left_table": jp.left_table,
                "right_table": jp.right_table,
                "left_columns": jp.left_columns,
                "right_columns": jp.right_columns,
                "join_type": jp.join_type,
                "composite_key": jp.composite_key
            } for jp in staging_definition.join_patterns
        ],
        "shared_keys": [
            {
                "name": sk.name,
                "source_columns": sk.source_columns,
                "is_composite": sk.is_composite,
                "surrogate_key_formula": sk.surrogate_key_formula
            } for sk in shared_keys
        ],
        "etl_options": {
            "add_shared_keys": True,
            "optimize_for_powerbi": True,
            "handle_composite_keys": True
        },
        "powerbi_requirements": [
            "Generate efficient star schema relationships",
            "Use proper data types for performance",
            "Implement shared keys for relationship optimization"
        ]
    }
    
    response = self.llm_service_client.call_api_endpoint(
        endpoint="/api/mquery/staging",
        method="POST",
        payload=api_payload
    )
    
    if response and response.get("m_query"):
        return response["m_query"]
    
    return None
```

### 3. **M-Query Generation Endpoint** (`/api/mquery/generate`)

**Purpose**: Update existing fact table M-queries to include shared keys.

#### Input from Staging System:
```json
{
  "context": {
    "table_name": "PURCHASE_ORDER_LINE",
    "existing_m_query": "let\n    Source = Sql.Database(\"server\", \"database\"),\n    POLines = Source{[Schema=\"dbo\",Item=\"PURCHASE_ORDER_LINE\"]}[Data]\nin\n    POLines",
    "shared_keys": [
      {
        "name": "SITE_ITEM_Key", 
        "source_columns": ["SITE_NUMBER", "ITEM_NUMBER"],
        "is_composite": true,
        "surrogate_key_formula": "Text.From([SITE_NUMBER]) & \"_\" & Text.From([ITEM_NUMBER])"
      }
    ],
    "source_info": {
      "source_type": "sqlserver",
      "server": "prod-sql-01", 
      "database": "SalesDB"
    },
    "modification_type": "add_shared_keys"
  },
  "options": {
    "preserve_existing_logic": true,
    "optimize_for_performance": true,
    "add_comments": true,
    "query_folding_preference": "BestEffort"
  }
}
```

#### Expected Output:
```json
{
  "m_query": "let\n    Source = Sql.Database(\"prod-sql-01\", \"SalesDB\"),\n    POLines = Source{[Schema=\"dbo\",Item=\"PURCHASE_ORDER_LINE\"]}[Data],\n    // Add shared key for staging table relationships\n    AddedSharedKey = Table.AddColumn(POLines, \"SITE_ITEM_Key\", each Text.From([SITE_NUMBER]) & \"_\" & Text.From([ITEM_NUMBER]), type text)\nin\n    AddedSharedKey",
  "performance_notes": "Shared key added with minimal performance impact. Query folding preserved.",
  "confidence": 0.95,
  "processing_time": 1.4,
  "metadata": {
    "table_name": "PURCHASE_ORDER_LINE",
    "modification_type": "add_shared_keys",
    "changes_made": [
      "Added SITE_ITEM_Key column",
      "Preserved existing transformations",
      "Maintained query folding capability"
    ]
  }
}
```

### 4. **Table Classification Endpoint** (`/api/table/classify`)

**Purpose**: Classify tables as fact or dimension for optimal relationship creation.

#### Input from Staging System:
```json
{
  "table_name": "PURCHASE_ORDER_LINE",
  "columns": [
    {"name": "PO_NUMBER", "data_type": "text", "is_key": true},
    {"name": "SITE_NUMBER", "data_type": "text", "is_foreign_key": true},
    {"name": "ITEM_NUMBER", "data_type": "text", "is_foreign_key": true},
    {"name": "QUANTITY", "data_type": "decimal", "is_measure": true},
    {"name": "UNIT_PRICE", "data_type": "decimal", "is_measure": true}
  ],
  "sample_row_count": 50000,
  "business_context": "Purchase order line items with quantities and pricing"
}
```

#### Expected Output:
```json
{
  "table_type": "fact",
  "confidence": 0.88,
  "reasoning": [
    "Contains numeric measures (QUANTITY, UNIT_PRICE)",
    "Has foreign key relationships to dimensions",
    "Moderate to high cardinality (50K rows)",
    "Transactional data pattern detected"
  ],
  "recommendations": [
    "Create relationships to dimension tables via staging",
    "Optimize for fact table performance patterns",
    "Consider partitioning for large datasets"
  ],
  "staging_considerations": [
    "Good candidate for staging table optimization",
    "Composite keys suggest shared key benefits",
    "High join frequency indicates performance gains"
  ],
  "processing_time": 1.2
}
```

## Integration Workflow

### 1. **Package Analysis Phase**
```python
# Step 1: Analyze Cognos package
package_analysis = sql_analyzer.analyze_package_with_llm(package_xml)

# Step 2: Classify tables
for table in package_tables:
    classification = table_classifier.classify_table_with_llm(table)
    table.table_type = classification["table_type"]
```

### 2. **Staging Table Generation Phase**
```python
# Step 3: Generate staging tables
staging_tables = staging_analyzer.generate_staging_tables(join_patterns, settings)

# Step 4: Generate M-queries for staging tables
for staging_table in staging_tables:
    m_query = mquery_converter.generate_staging_m_query_with_llm(staging_table)
    staging_table.m_query = m_query
```

### 3. **Fact Table Update Phase**
```python
# Step 5: Update fact tables with shared keys
for fact_table in fact_tables:
    updated_query = mquery_converter.add_shared_keys_with_llm(fact_table)
    fact_table.m_query = updated_query
```

## Error Handling and Fallbacks

### API Call Failures
```python
def call_with_fallback(self, endpoint, payload):
    try:
        response = self.llm_service_client.call_api_endpoint(endpoint, "POST", payload)
        if response:
            return response
    except Exception as e:
        self.logger.warning(f"API call failed for {endpoint}: {e}")
    
    # Fall back to template-based generation
    return self._generate_template_response(payload)
```

### Response Validation
```python
def validate_api_response(self, response, expected_fields):
    if not response:
        return False
    
    for field in expected_fields:
        if field not in response:
            self.logger.warning(f"Missing expected field: {field}")
            return False
    
    return True
```

## LLM Prompts Used by API

The API endpoints use specific prompts optimized for different tasks:

### SQL Analysis Prompt
```
Analyze the provided Cognos package XML and extract:
1. Table relationships and join patterns
2. Composite key scenarios
3. Fact vs dimension table classification
4. Optimization opportunities for Power BI staging tables

Focus on identifying complex joins that would benefit from staging table optimization.
```

### M-Query Generation Prompt  
```
Generate an optimized Power BI M-query for a staging table that:
1. Combines multiple source tables using specified join patterns
2. Creates shared keys for optimal relationships
3. Handles composite keys with surrogate key generation
4. Follows Power BI performance best practices
5. Maintains query folding where possible
```

### Fact Table Update Prompt
```
Update the existing M-query to add shared key columns while:
1. Preserving all existing transformations
2. Maintaining query folding capability
3. Adding appropriate comments
4. Using optimal data types for keys
5. Minimizing performance impact
```

This integration allows the staging table system to leverage the full power of the LLM API for intelligent analysis and code generation while maintaining robust fallback mechanisms. 