{
  "mappingVersion": "1.0",
  "sourceTool": "Tableau",
  "targetTool": "PowerBI",
  "conceptualMappings": [
    {
      "sourceType": "Workbook",
      "targetType": "Power BI Report (.pbix)",
      "notes": "Overall container mapping."
    },
    {
      "sourceType": "DataSource",
      "targetType": "Power BI DataSource/Query",
      "notes": "Maps to the connection definition in Power Query/Power BI dataset."
    },
    {
      "sourceType": "Connection (Live)",
      "targetType": "Power BI Connection (DirectQuery)",
      "confidence": "High"
    },
    {
      "sourceType": "Connection (Extract)",
      "targetType": "Power BI Connection (Import)",
      "confidence": "High"
    },
    {
      "sourceType": "CustomSQL",
      "targetType": "Power Query Custom SQL / Native Query",
      "notes": "Requires validation of SQL dialect compatibility.",
      "confidence": "Medium"
    },
    {
      "sourceType": "DataTable (in Model)",
      "targetType": "Power BI Table (in Model)",
      "notes": "Logical table representation.",
      "confidence": "High"
    },
    {
      "sourceType": "Relationship",
      "targetType": "Power BI Relationship",
      "notes": "Need to map join types to cardinality and cross-filter direction.",
      "confidence": "Medium"
    },
    {
      "sourceType": "Field (Dimension)",
      "targetType": "Power BI Column (Dimension)",
      "confidence": "High"
    },
    {
      "sourceType": "Field (Measure)",
      "targetType": "Power BI Column (Numeric)", // Could also be implicit measure
      "notes": "Direct numeric columns. Base for implicit measures.",
      "confidence": "High"
    },
    {
      "sourceType": "CalculatedField (Measure Role)",
      "targetType": "Power BI Measure (DAX)",
      "translationNeeded": true,
      "handler": "AI_Calculation_Translator",
      "confidence": "Medium",
      "notes": "Core DAX translation needed."
    },
    {
      "sourceType": "CalculatedField (Dimension Role)",
      "targetType": "Power BI Calculated Column (DAX)",
      "translationNeeded": true,
      "handler": "AI_Calculation_Translator",
      "confidence": "Medium",
      "notes": "Often maps to columns, sometimes complex measures needed."
    },
    {
        "sourceType": "Hierarchy",
        "targetType": "Power BI Hierarchy",
        "confidence": "High"
    },
    {
        "sourceType": "Parameter",
        "targetType": "Power BI Parameter (What-If or Field Parameter)",
        "notes": "Mapping depends heavily on parameter type and usage.",
        "confidence": "Low"
    },
    {
        "sourceType": "Set",
        "targetType": ["Calculated Table (DAX)", "Complex Filter (DAX)", "Role"],
        "notes": "Sets have poor direct mapping. Requires analysis of usage. Can sometimes map to Roles for security.",
        "confidence": "Low"
    },
    {
      "sourceType": "Worksheet",
      "targetType": ["Power BI Page", "Power BI Visual"],
      "notes": "Simple worksheets map 1:1 to a page with one visual. Complex worksheets (multiple mark types, density) may need decomposition or approximation.",
      "confidence": "Medium"
    },
    {
        "sourceType": "Visualization (Bar)",
        "targetType": ["Clustered Bar Chart", "Stacked Bar Chart"],
        "confidence": "High"
    },
    {
        "sourceType": "Visualization (Line)",
        "targetType": "Line Chart",
        "confidence": "High"
    },
    {
        "sourceType": "Visualization (Text/Table)",
        "targetType": ["Table", "Matrix"],
        "confidence": "High"
    },
    {
        "sourceType": "Visualization (Map)",
        "targetType": ["Map", "Filled Map", "Azure Map"],
        "notes": "Requires mapping geographic roles.",
        "confidence": "Medium"
    },
    {
        "sourceType": "Filter (Worksheet/Dashboard)",
        "targetType": ["Power BI Slicer", "Visual Filter", "Page Filter", "Report Filter"],
        "notes": "Mapping depends on scope and type.",
        "confidence": "Medium"
    },
    {
      "sourceType": "Dashboard",
      "targetType": "Power BI Page(s)",
      "notes": "Layout translation is complex. May require multiple pages or careful object placement.",
      "confidence": "Medium"
    },
    {
      "sourceType": "Action (Filter/Highlight)",
      "targetType": "Power BI Visual Interaction (Filter/Highlight)",
      "notes": "Default interactions often cover this, but specific cross-filtering logic needs mapping.",
      "confidence": "Medium"
    },
    {
      "sourceType": "Action (GoToSheet)",
      "targetType": "Power BI Bookmark / Button Navigation",
      "confidence": "Medium"
    }
    // ... add mappings for Groups, Bins, other Viz types, other Actions etc.
  ],
  "propertyMappings": [
      { "sourceType": "Visualization", "sourceProperty": "Shelves.Columns", "targetType": "VisualFieldWell", "targetProperty": ["Axis", "Category"], "notes": "Depends on visual type" },
      { "sourceType": "Visualization", "sourceProperty": "Shelves.Rows", "targetType": "VisualFieldWell", "targetProperty": ["Values", "Y-Axis"], "notes": "Depends on visual type" },
      { "sourceType": "Visualization", "sourceProperty": "Shelves.Color", "targetType": "VisualFieldWell", "targetProperty": "Legend" },
      { "sourceType": "Visualization", "sourceProperty": "Shelves.Tooltip", "targetType": "VisualFieldWell", "targetProperty": "Tooltips" }
      // ... etc.
  ],
  "functionMappings": [
      { "sourceFunction": "ZN", "targetFunction": "COALESCE", "pattern": "COALESCE(<arg1>, 0)", "notes": "Direct mapping", "confidence": "High" },
      { "sourceFunction": "SUM", "targetFunction": "SUM", "notes": "Direct mapping", "confidence": "High" },
      { "sourceFunction": "ATTR", "targetFunction": ["MIN", "MAX", "VALUES"], "notes": "Context dependent. Often indicates need for MIN/MAX in DAX measures, or VALUES in calculated columns.", "confidence": "Medium" },
      { "sourceFunction": "LOOKUP", "targetFunction": ["CALCULATE", "Time Intelligence Functions"], "notes": "Complex. Often requires DAX time intelligence or advanced CALCULATE filters. High translation risk.", "confidence": "Low" },
      { "sourceFunction": "FIXED", "targetFunction": "CALCULATE + ALLEXCEPT/ALL", "notes": "LOD expressions require careful context mapping in DAX.", "handler": "AI_Calculation_Translator", "confidence": "Medium" }
      // ... many more functions
  ]
}