# Centralized Date Tables and DateTime Variations

This document outlines the best-practice approach for handling date and time columns during a Cognos to Power BI migration, focusing on two key areas: creating a single, centralized date table and enhancing dateTime columns with variations for time intelligence.

## 1. Centralized Date Table Strategy

To ensure consistent date filtering and a simpler, more efficient data model in Power BI, the migration process should create a single, centralized date table (often called a "Calendar table") that all other tables can relate to.

### The Problem with Multiple Date Tables

Creating a separate `LocalDateTable` for each source table that contains a `dateTime` column leads to a bloated data model with redundant tables. This makes the model harder to manage and can lead to inconsistent filtering behavior across different report visuals.

### Implementation

The solution is to refactor the data extraction logic to create only one central date table and establish relationships from all `dateTime` columns across the model to this single table.

This is implemented in `cognos_migrator/extractors/packages/consolidated_package_extractor.py`. The key steps are:

1.  **Identify all `dateTime` columns:** Iterate through all tables and their columns in the data model to find every column with a `dateTime` data type.
2.  **Create a Single Date Table:** If at least one `dateTime` column exists, create a single `LocalDateTable`. Its name includes a UUID to ensure it is unique.
3.  **Create Relationships:** For each identified `dateTime` column, create a relationship between its parent table and the central `LocalDateTable` on the date key.

The `_create_central_date_table` function in `consolidated_package_extractor.py` handles this logic:

```python
def _create_central_date_table(self, data_model: DataModel):
    """Create a single, central date table and relationships for all datetime columns."""
    datetime_columns = []
    for table in data_model.tables:
        for column in table.columns:
            if (hasattr(column.data_type, 'value') and column.data_type.value == 'dateTime') or \
               (isinstance(column.data_type, str) and column.data_type.lower() == 'datetime'):
                datetime_columns.append((table, column))

    if not datetime_columns:
        return

    # Create a single date table
    date_table_name = f"LocalDateTable_{uuid.uuid4()}"
    date_table = self._create_date_table(date_table_name)
    data_model.date_tables.append({
        'name': date_table.name,
        'template_content': self.template_engine.render('DateTableTemplate', {'table': date_table})
    })
    self.logger.info(f"Created central date table '{date_table.name}'")

    # Create relationships to the central date table
    for table, column in datetime_columns:
        relationship = Relationship(
            from_table=table.name,
            from_column=column.name,
            to_table=date_table.name,
            to_column="Date"
            # ... other relationship properties
        )
        data_model.relationships.append(relationship)

    # Store relationship info directly in the column metadata
    if not hasattr(column, 'metadata'):
        column.metadata = {}
    column.metadata['relationship_info'] = {
        'id': relationship.id,
        'hierarchy': f"'{date_table.name}'.'Date Hierarchy'"
    }
```

## 2. Enhancing DateTime Columns with Variations

To enable Power BI's built-in time intelligence features, `dateTime` columns need a `variation` property in their TMDL definition. This variation links the column to a date table hierarchy.

### Target TMDL Structure

The goal is to generate the following structure for each `dateTime` column in its respective `Table.tmdl` file:

```tmdl
column 'datecreated'
    dataType: dateTime
    summarizeBy: none
    sourceColumn: datecreated

    variation 'Variation'
        isDefault
        relationship: 9c4e4288-0b2b-4665-8777-5685545dca19
        defaultHierarchy: 'LocalDateTable_...'.'Date Hierarchy'

    annotation SummarizationSetBy = Automatic
```

### Implementation: A Direct Metadata Approach

The most robust way to ensure the relationship information is available during TMDL generation is to store it directly with the column when the relationship is created.

#### Step 1: Store Relationship Info in Column Metadata

In `cognos_migrator/extractors/packages/consolidated_package_extractor.py`, when a relationship is created in the `_create_central_date_table` function, we add its ID and the target hierarchy directly to the `metadata` dictionary of the `Column` object.

```python
# In _create_central_date_table...
for table, column in datetime_columns:
    relationship = Relationship(...)
    data_model.relationships.append(relationship)

    # Store relationship info directly in the column metadata
    if not hasattr(column, 'metadata'):
        column.metadata = {}
    column.metadata['relationship_info'] = {
        'id': relationship.id,
        'hierarchy': f"'{date_table.name}'.'Date Hierarchy'"
    }
```

#### Step 2: Use Metadata in the TMDL Generator

In `cognos_migrator/generators/model_file_generator.py`, the `_build_table_context` function can now directly access this information from the column's metadata, eliminating the need for fragile lookups.

```python
# In _build_table_context...
for col in table.columns:
    # ...
    is_datetime = (col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type).lower()) == 'datetime'
    
    # Directly access relationship_info from metadata
    relationship_info = col.metadata.get('relationship_info') if hasattr(col, 'metadata') else None

    columns_context.append({
        # ... other properties
        'is_datetime': is_datetime,
        'relationship_info': relationship_info
    })
```

#### Step 3: Update the `Table.tmdl` Template

Finally, the `cognos_migrator/templates/Table.tmdl` template uses this context to conditionally render the `variation` block.

```jinja2
{# In Table.tmdl #}
{% for column in columns %}
    column '{{ column.name }}'
        dataType: {{ column.dataType }}
        summarizeBy: {{ column.summarizeBy }}
        sourceColumn: {{ column.sourceColumn }}

        {% if column.is_datetime and column.relationship_info %}
        variation 'Variation'
            isDefault
            relationship: {{ column.relationship_info.id }}
            defaultHierarchy: {{ column.relationship_info.hierarchy }}
        {% endif %}

        annotation SummarizationSetBy = {{ column.summarizationSetBy }}
{% endfor %}
```

This approach creates a robust and reliable pipeline for handling `dateTime` columns correctly, ensuring a well-structured Power BI model with full time-intelligence capabilities. 