# Troubleshooting and Maintenance Guide

## Overview

This document provides guidance for troubleshooting common issues and maintaining the BIMigrator-Cognos tool. It includes information on known issues, debugging techniques, and best practices for making updates to the codebase.

## Common Issues and Solutions

### 1. Relationship ID Errors

**Symptom**: Error message `'Relationship' object has no attribute 'id'` during migration.

**Cause**: The code is trying to access an `id` attribute on a `Relationship` object, but the class only has a `name` attribute.

**Solution**: 
- In `model_file_generator.py` and `module_model_file_generator.py`, ensure the `_generate_relationships_file` method uses `rel.name` instead of `rel.id` for relationship IDs.
- Check the `relationship_data` dictionary construction to verify it's using the correct attributes.

```python
# Correct implementation
relationship_data = {
    'id': rel.name,  # Use name as the relationship ID
    'name': rel.name,
    # Other attributes...
}
```

### 2. Culture File Naming Issues

**Symptom**: Generated Power BI files don't match expected structure or reference incorrect culture files.

**Cause**: Culture files are incorrectly named as "culture.tmdl" instead of using the culture code (e.g., "en-US.tmdl").

**Solution**:
- In both generator classes, ensure culture files are named after the culture code:

```python
culture_code = data_model.culture or 'en-US'
culture_file = model_dir / 'cultures' / f'{culture_code}.tmdl'
```

### 3. Version Format Inconsistencies

**Symptom**: Version strings in generated files don't match expected format.

**Cause**: Different version strings are used in different places.

**Solution**:
- For culture files, use version "1.0.0"
- For PBIDesktopVersion in model.tmdl, use the full version string: "2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729"

### 4. Method Signature Mismatches

**Symptom**: Errors about missing arguments when calling methods from derived classes.

**Cause**: Method signatures in derived classes don't match the base class.

**Solution**:
- Ensure all parameters in the base class method are included in the derived class method
- When overriding methods, always call the base class implementation with all required parameters

```python
# Example of correct override
def _build_table_context(self, table: Table, report_spec: Optional[str] = None, 
                       data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, 
                       m_query: Optional[str] = None, report_name: Optional[str] = None, 
                       project_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    context = super()._build_table_context(table, report_spec, data_items, extracted_dir, m_query, report_name, project_metadata)
    # Add module-specific context
    return context
```

### 5. LLM Service Connection Issues

**Symptom**: Error messages about connection refused or timeout when connecting to LLM service.

**Cause**: The LLM service is not available or not properly configured.

**Solution**:
- Check LLM service configuration in the config file
- Verify network connectivity to the LLM service
- Implement fallback mechanisms for when the LLM service is unavailable

## Debugging Techniques

### 1. Enable Detailed Logging

Increase the logging level to get more detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set the log level in the configuration:

```python
config.log_level = "DEBUG"
```

### 2. Inspect Generated Files

Examine the generated files to identify issues:

```bash
# View the model.tmdl file
cat output/report_<id>/pbit/Model/model.tmdl

# Check culture files
ls -la output/report_<id>/pbit/Model/cultures/
cat output/report_<id>/pbit/Model/cultures/en-US.tmdl

# Examine relationships file
cat output/report_<id>/pbit/Model/relationships.tmdl
```

### 3. Use Python Debugger

Add breakpoints in the code using the Python debugger:

```python
import pdb
pdb.set_trace()  # Add this line where you want to pause execution
```

### 4. Print Object Attributes

Print object attributes to understand their structure:

```python
for rel in relationships:
    print(f"Relationship: {rel.__dict__}")
```

## Maintenance Best Practices

### 1. Code Updates

When updating the code:

- Always maintain method signature compatibility between base and derived classes
- Test both report and module migrations after making changes
- Update documentation to reflect changes
- Add comprehensive logging for new functionality

### 2. Adding New Features

When adding new features:

- Follow the existing class hierarchy and design patterns
- Extend base classes rather than modifying them directly
- Implement features for both report and module migrations if applicable
- Add appropriate tests for new functionality

### 3. Version Control

Follow these version control practices:

- Create feature branches for new functionality
- Write descriptive commit messages
- Include issue references in commit messages
- Create pull requests for code reviews

### 4. Testing

Implement thorough testing:

- Test with various report and module types
- Verify generated files against expected structure
- Test edge cases and error handling
- Create automated tests for critical functionality

## Future Enhancements

Consider these potential enhancements:

1. **Automated Testing**: Add comprehensive automated tests for both report and module migrations.

2. **Error Recovery**: Implement better error recovery mechanisms to handle partial failures.

3. **Performance Optimization**: Optimize the migration process for large reports and modules.

4. **Enhanced Documentation**: Generate more detailed migration reports and documentation.

5. **UI Integration**: Develop a user interface for easier migration management.

## Contact and Support

For questions or issues:

- File issues in the project repository
- Contact the development team at [team-email@example.com]
- Refer to the internal knowledge base for additional resources
