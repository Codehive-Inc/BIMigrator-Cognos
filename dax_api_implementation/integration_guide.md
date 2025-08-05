# DAX API Integration Guide

## Overview
This guide shows how to integrate the enhanced M-Query generator into your existing DAX API service to ensure all generated M-Query code includes proper exception handling.

## Integration Steps

### 1. Add Enhanced Generator to Your DAX API

Replace your current M-Query generation logic with the `EnhancedMQueryGenerator`:

```python
# In your DAX API service
from enhanced_mquery_generator import EnhancedMQueryGenerator

# Initialize with your LLM client
llm_client = YourLLMClient()  # OpenAI, Anthropic, etc.
mquery_generator = EnhancedMQueryGenerator(llm_client)
```

### 2. Update Your API Endpoint

Replace your `/api/m-query` endpoint with the enhanced version:

```python
@app.post("/api/m-query")
async def generate_mquery(request: MQueryRequest):
    result = mquery_generator.generate_mquery(request.dict())
    return MQueryResponse(**result)
```

### 3. Update LLM Client Integration

The enhanced generator expects your LLM client to have a `generate()` method:

```python
class YourLLMClient:
    def generate(self, system_prompt: str, user_prompt: str, 
                temperature: float = 0.3, max_tokens: int = 2000) -> str:
        # Your LLM implementation here
        # Return generated text
        pass
```

### 4. Configuration Changes

Update your service configuration to handle new request parameters:

```python
# Environment variables
ERROR_HANDLING_ENABLED = True
TEMPLATE_MODE_DEFAULT = "guided"
VALIDATION_ENABLED = True
```

## Request Format Changes

### Before (Current)
```json
{
    "context": {
        "table_name": "Orders",
        "columns": [{"name": "ID", "type": "int"}]
    },
    "options": {
        "optimize_for_performance": true
    }
}
```

### After (Enhanced)
```json
{
    "context": {
        "table_name": "Orders",
        "source_type": "sql",
        "columns": [{"name": "ID", "type": "int"}],
        "connection_info": {
            "server": "localhost",
            "database": "sales"
        },
        "base_template": "...",  // Optional template
        "error_handling_requirements": {
            "wrap_with_try_otherwise": true,
            "include_fallback_empty_table": true
        }
    },
    "options": {
        "optimize_for_performance": true,
        "use_template_mode": true,
        "template_compliance": "guided",
        "error_handling_mode": "comprehensive"
    }
}
```

## Response Format Changes

### Before
```json
{
    "m_query": "let Source = Sql.Database(...) in Source"
}
```

### After (Enhanced)
```json
{
    "m_query": "let ConnectionAttempt = try Sql.Database(...) otherwise error [...], Result = if ConnectionAttempt[HasError] then ... else ... in Result",
    "success": true,
    "validation": {
        "is_valid": true,
        "has_try_otherwise": true,
        "has_error_checking": true,
        "has_fallback": true
    },
    "template_used": true,
    "confidence": 0.95,
    "metadata": {
        "has_error_handling": true,
        "template_mode": "guided"
    }
}
```

## Backward Compatibility

The enhanced API maintains backward compatibility:

1. **Old requests work** - Missing fields get default values
2. **Old response format** - Core `m_query` field is always present
3. **Gradual migration** - Clients can adopt new features incrementally

## Testing the Integration

### 1. Health Check
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
    "status": "ok",
    "features": {
        "error_handling": true,
        "template_mode": true,
        "validation": true
    }
}
```

### 2. Test M-Query Generation
```bash
curl -X POST http://localhost:8080/api/m-query \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "table_name": "Orders",
      "source_type": "sql",
      "connection_info": {"server": "localhost", "database": "test"}
    },
    "options": {
      "use_template_mode": true
    }
  }'
```

### 3. Validate Error Handling
Check that the response includes:
- `try...otherwise` blocks
- `[HasError]` checks
- Fallback table generation
- Error records with Reason/Message/Detail

## Migration Checklist

- [ ] Install enhanced generator
- [ ] Update API endpoint
- [ ] Test with existing requests
- [ ] Verify error handling in responses
- [ ] Update documentation
- [ ] Monitor validation metrics
- [ ] Gradual rollout to production

## Monitoring

Add logging to track:
- Validation success rate
- Template usage frequency
- Fallback generation triggers
- Error handling effectiveness

```python
logger.info(f"M-Query generated: validation={validation['is_valid']}, template_used={template_used}")
```

## Troubleshooting

### Common Issues

1. **Templates not found**
   - Ensure template files are accessible
   - Check template format and placeholders

2. **Validation failures**
   - Review validation rules
   - Check for missing error handling patterns

3. **LLM client integration**
   - Verify client interface matches expected format
   - Check authentication and rate limits

### Debug Mode

Enable debug logging:
```python
logging.getLogger('enhanced_mquery_generator').setLevel(logging.DEBUG)
```

This will log:
- Template selection decisions
- LLM prompt construction
- Validation results
- Fallback triggers