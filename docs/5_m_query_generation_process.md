# M-Query Generation Process

## Overview

The M-Query generation process creates Power BI M-language queries (Power Query) from Cognos report expressions and data sources. This process can use an LLM service to optimize and transform the queries.

## Process Flow

1. **Build Context for M-Query Generation**
   - Collect table metadata (name, columns, data types)
   - Extract relevant report specifications
   - Prepare source query information

2. **Generate M-Query**
   - If LLM service is enabled:
     - Send context to LLM service API
     - Receive optimized M-query
   - If LLM service is disabled:
     - Generate basic M-query using templates

3. **Clean and Format M-Query**
   - Remove comments
   - Format query for TMDL file
   - Handle SQL queries and parameter arrays

## Key Components

### M-Query Generation in PowerBIProjectGenerator

The `PowerBIProjectGenerator` class in `generators.py` handles the generation of M-queries:

```python
def _build_m_expression(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
    """Build M expression for table partition using LLM service if available"""
    # If LLM service is not available, use a basic template
    if not self.llm_service:
        return self._build_basic_m_expression(table)
    
    # Build context for LLM service
    context = {
        'table_name': table.name,
        'columns': [{
            'name': col.name,
            'data_type': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
            'description': col.description if hasattr(col, 'description') else None
        } for col in table.columns],
        'source_query': table.source_query,
    }
    
    # Add report specification if available
    if report_spec:
        context['report_spec'] = self._extract_relevant_report_spec(report_spec, table.name)
    
    # Generate M-query using LLM service
    m_query = self.llm_service.generate_m_query(context)
    
    # Clean and format the M-query
    cleaned_m_query = self._clean_m_query(m_query)
    
    return cleaned_m_query
```

### LLM Service Integration

The `LLMServiceClient` class in `llm_service.py` handles communication with the LLM service API:

```python
class LLMServiceClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> bool:
        """Check if the LLM service is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Failed to check LLM service health: {e}")
            return False
    
    def generate_m_query(self, context: Dict[str, Any]) -> str:
        """Generate M query from context using LLM service"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.post(
                f"{self.base_url}/generate-m-query",
                json=context,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("m_query", "")
            else:
                self.logger.error(f"LLM service error: {response.status_code} {response.text}")
                return self._generate_fallback_m_query(context)
                
        except Exception as e:
            self.logger.error(f"Failed to generate M query: {e}")
            return self._generate_fallback_m_query(context)
    
    def _generate_fallback_m_query(self, context: Dict[str, Any]) -> str:
        """Generate a basic M query as fallback"""
        table_name = context.get('table_name', 'Table')
        columns = context.get('columns', [])
        
        column_list = ", ".join([f"[{col['name']}]" for col in columns])
        
        return f"""
        let
            Source = Table.FromRows(
                {{
                    {{ "ID", "Name", "Value" }}
                }},
                {{ "ID", "Name", "Value" }}
            )
        in
            Source
        """
```

### Extracting Relevant Report Specification

The `_extract_relevant_report_spec` method extracts the relevant parts of the report specification for a given table:

```python
def _extract_relevant_report_spec(self, report_spec: str, table_name: str) -> str:
    """Extract relevant parts of the report specification for the given table"""
    try:
        import xml.etree.ElementTree as ET
        
        # Find data items related to the table
        root = ET.fromstring(report_spec)
        data_items = root.findall('.//dataItem')
        relevant_items = []
        
        for item in data_items:
            # Check if the data item is related to the table
            if table_name.lower() in ET.tostring(item, encoding='unicode').lower():
                relevant_items.append(ET.tostring(item, encoding='unicode'))
        
        return '\n'.join(relevant_items)
    except Exception as e:
        self.logger.warning(f"Failed to extract relevant report spec: {e}")
        return ""
```

### Cleaning and Formatting M-Query

The `_clean_m_query` method cleans and formats the generated M-query:

```python
def _clean_m_query(self, m_query: str) -> str:
    """Clean M-query by removing comments and fixing formatting"""
    try:
        # Check if the query has let/in structure
        if "let" in m_query and "in" in m_query:
            # Split into let and in parts
            let_part = m_query.split("let")[1].split("in")[0].strip()
            in_part = m_query.split("in")[1].strip()
            
            # Clean the let part
            cleaned_let_part = ""
            for line in let_part.split(','):
                # Remove comments
                code_part = re.sub(r'(/ /|//).*?(?=,|$)', '', line).strip()
                if code_part:
                    cleaned_let_part += code_part + ", "
            
            # Remove trailing comma if present
            cleaned_let_part = cleaned_let_part.rstrip(', ')
            
            # Clean the in part
            cleaned_in_part = re.sub(r'(/ /|//).*', '', in_part).strip()
            
            # Format the final M-query with proper indentation for TMDL
            formatted_query = "let\n"
            
            # Process each step
            steps = []
            for step in cleaned_let_part.split(','):
                step = step.strip()
                if step:
                    steps.append(step)
            
            for i, step in enumerate(steps):
                if '=' in step:
                    parts = step.split('=', 1)
                    step_name = parts[0].strip()
                    step_content = parts[1].strip()
                    
                    formatted_query += f"\t\t\t\t{step_name} = {step_content}"
                    if i < len(steps) - 1:
                        formatted_query += ",\n"
                else:
                    formatted_query += f"\t\t\t\t{step}"
                    if i < len(steps) - 1:
                        formatted_query += ",\n"
            
            # Add the 'in' part
            formatted_query += "\n\t\t\tin\n\t\t\t\t" + cleaned_in_part
            
            return formatted_query
        else:
            # If the query doesn't have let/in structure, return it as is
            return m_query
    except Exception as e:
        self.logger.warning(f"Error cleaning M-query: {e}")
        return m_query
```

## Output

The M-Query generation process produces formatted M-language queries that are included in the Power BI table definitions (.tmdl files). These queries define how data is loaded and transformed in the Power BI model.
