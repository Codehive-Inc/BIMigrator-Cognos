# Generator Implementation Details

## Overview

This document provides detailed information about the generator classes used in the BIMigrator-Cognos tool, focusing on the differences between report and module generators and important implementation details.

## Generator Class Hierarchy

The BIMigrator-Cognos tool uses a hierarchical approach to generators:

1. **Base Generator Classes**
   - `ModelFileGenerator`: Base class for generating Power BI model files
   - `ReportFileGenerator`: Base class for generating Power BI report files
   - `MetadataFileGenerator`: Base class for generating metadata files

2. **Module-Specific Generator Classes**
   - `ModuleModelFileGenerator`: Extends `ModelFileGenerator` with module-specific functionality
   - `ModuleGenerator`: Orchestrates the module generation process

3. **Report-Specific Generator Classes**
   - `ReportGenerator`: Orchestrates the report generation process
   - `VisualContainerGenerator`: Handles visual container generation

## Key Implementation Details

### ModelFileGenerator vs. ModuleModelFileGenerator

The `ModuleModelFileGenerator` class extends `ModelFileGenerator` with module-specific functionality:

#### Method Signatures

It's critical that method signatures match between the base and derived classes. For example:

```python
# Base class (ModelFileGenerator)
def _build_table_context(self, table: Table, report_spec: Optional[str] = None, 
                        data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, 
                        m_query: Optional[str] = None, report_name: Optional[str] = None,
                        project_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Implementation...

# Derived class (ModuleModelFileGenerator)
def _build_table_context(self, table: Table, report_spec: Optional[str] = None, 
                       data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, 
                       m_query: Optional[str] = None, report_name: Optional[str] = None, 
                       project_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Call base implementation
    context = super()._build_table_context(table, report_spec, data_items, extracted_dir, m_query, report_name, project_metadata)
    # Add module-specific context
    context['is_module_table'] = True
    return context
```

### Relationship Handling

Both generators handle relationships, but with important differences:

1. **Relationship ID Usage**
   - The `Relationship` class does not have an `id` attribute
   - Both generators should use `rel.name` as the relationship ID in the context passed to the template

```python
# Correct implementation in both generators
relationship_data = {
    'id': rel.name,  # Use name as the relationship ID
    'name': rel.name,
    # Other attributes...
}
```

### Culture File Generation

Both generators create culture files, but with specific requirements:

1. **File Naming**
   - Culture files should be named after the culture code (e.g., "en-US.tmdl")
   - Do not use generic names like "culture.tmdl"

2. **Version Format**
   - Culture files should use version "1.0.0"
   - This is different from the PBIDesktopVersion used in model.tmdl

```python
# Correct implementation
culture_code = data_model.culture or 'en-US'
culture_file = model_dir / 'cultures' / f'{culture_code}.tmdl'
```

### PBIDesktopVersion Annotation

The PBIDesktopVersion annotation in model.tmdl should use the full version string:

```python
# Correct implementation
context = {
    # Other context items...
    'desktop_version': "2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729"
}
```

## Common Pitfalls and Solutions

### 1. Attribute Access Errors

**Problem**: Accessing non-existent attributes like `rel.id` when the `Relationship` class only has a `name` attribute.

**Solution**: Always verify the class structure and use existing attributes. Use `rel.name` instead of `rel.id` for relationship identifiers.

### 2. Method Signature Mismatches

**Problem**: Method signatures in derived classes not matching the base class, causing argument mismatch errors.

**Solution**: Ensure all parameters in the base class method are included in the derived class method, even if they're not used. Always call the base class method with all required parameters.

### 3. File Naming Inconsistencies

**Problem**: Using incorrect file names like "culture.tmdl" instead of culture-specific names like "en-US.tmdl".

**Solution**: Use the culture code from the data model to name culture files, with a fallback to "en-US" if no culture is specified.

### 4. Version String Inconsistencies

**Problem**: Using different version strings in different places, causing inconsistency in generated files.

**Solution**: Use "1.0.0" for culture file versions and the full PBIDesktopVersion string for model.tmdl.

## Best Practices for Extending Generators

1. **Always call super() methods**: When overriding methods in derived classes, call the base class implementation first to ensure core functionality is preserved.

2. **Match method signatures exactly**: Ensure all parameters from the base class are included in derived class methods.

3. **Use consistent naming conventions**: Follow the same naming patterns for files and attributes across all generators.

4. **Add comprehensive logging**: Include detailed logging to help diagnose issues during the generation process.

5. **Validate inputs**: Check that required attributes and properties exist before accessing them.

6. **Handle exceptions gracefully**: Catch and handle exceptions with informative error messages.

7. **Document differences**: Clearly document any differences between base and derived class implementations.
