Extraction Paths and Elements:
Here are the key elements to extract and their paths, mapping them to the information you need for your JSON config:
Package Name (from Project Name):
Element: <project><name>
Path: ./bmt:name (relative to the root <project>)
Extraction: package_name_elem = root.find('./bmt:name', ns); package_name = package_name_elem.text if package_name_elem is not None else 'Unknown Package'
Physical Data Source Connection:
Element: <dataSources><dataSource> (There can be multiple, but typically one primary one for a package).
Path to <dataSource>: ./bmt:dataSources/bmt:dataSource
Inside <dataSource>:
CM Data Source Name: <cmDataSource>
Path relative to <dataSource>: ./bmt:cmDataSource
Schema Name: <schema>
Path relative to <dataSource>: ./bmt:schema
Extraction: Find the <dataSource> element(s) and extract the text from <cmDataSource> and <schema>. This maps to the cognos_connection_name and helps you link to your connection_mappings JSON section.
Namespaces (Layers):
Element: <namespace>
Paths:
Root Namespace (often the package name implicitly): ./bmt:namespace
"Database Layer" Namespace: ./bmt:namespace/bmt:namespace[bmt:name='Database Layer']
"Presentation Layer" Namespace: ./bmt:namespace/bmt:namespace[bmt:name='Presentation Layer']
Extraction: Identify these namespaces to iterate through their contents separately.
Query Subjects (Tables/Views):
Element: <querySubject>
Paths (relative to the relevant Namespace element - Database or Presentation):
All Query Subjects: ./bmt:querySubject
Inside <querySubject>:
Query Subject Name: <name>
Path relative to <querySubject>: ./bmt:name
Query Subject Status: @status (attribute)
Path relative to <querySubject>: . (get attribute status)
For Database Layer QS Definition: <definition><dbQuery>
Path relative to <querySubject>: ./bmt:definition/bmt:dbQuery
Source SQL: <sql type="cognos">
Path relative to <dbQuery>: ./bmt:sql
Table Type: <tableType>
Path relative to <dbQuery>: ./bmt:tableType
Source Data Source Ref: <sources><dataSourceRef>
Path relative to <dbQuery>: ./bmt:sources/bmt:dataSourceRef
For Presentation Layer QS Definition: <definition><modelQuery>
Path relative to <querySubject>: ./bmt:definition/bmt:modelQuery
Model Query SQL: <sql type="cognos">
Path relative to <modelQuery>: ./bmt:sql
Extraction: Iterate through query subjects in the Database and Presentation layers. Extract name and definition details. Use the definition (especially dbQuery for Database Layer) to identify the physical source table/view (physical_schema, physical_table, source_type).
Query Items (Columns/Fields):
Element: <queryItem>
Path (relative to its parent <querySubject>): ./bmt:queryItem
Inside <queryItem>:
Query Item Name: <name>
Path relative to <queryItem>: ./bmt:name
Query Item External Name: <externalName> (Often the physical column name)
Path relative to <queryItem>: ./bmt:externalName
Query Item Expression: <expression>
Path relative to <queryItem>: ./bmt:expression
Query Item Usage: <usage>
Path relative to <queryItem>: ./bmt:usage
Query Item Datatype: <datatype>
Path relative to <queryItem>: ./bmt:datatype
Query Item Regular Aggregate: <regularAggregate>
Path relative to <queryItem>: ./bmt:regularAggregate (Check if exists)
Query Item Nullable: <nullable>
Path relative to <queryItem>: ./bmt:nullable (Check if exists)
Extraction: Iterate through query items within each relevant query subject. Extract name, usage, datatype, aggregate, nullability, and expression. Analyze the expression to classify as source column reference or calculation.
Relationships:
Element: <relationship>
Paths (relative to the relevant Namespace element - Database or Presentation): ./bmt:relationship
Inside <relationship>:
Relationship Name: <name>
Path relative to <relationship>: ./bmt:name
Relationship Expression (Join Condition): <expression>
Path relative to <relationship>: ./bmt:expression (You'll need to parse this expression to find the joining <refobj>s).
Left/Right Side: <left>, <right>
Paths relative to <relationship>: ./bmt:left, ./bmt:right
Inside <left> / <right>:
Referenced Query Subject: <refobj>
Path relative to <left> / <right>: ./bmt:refobj (Get text content, this is the Cognos QS name).
Cardinality: <mincard>, <maxcard>
Paths relative to <left> / <right>: ./bmt:mincard, ./bmt:maxcard
Extraction: Iterate through relationships in the Database and Presentation layers. Extract name, expression, and left/right details (Query Subject names, cardinalities). Parse the expression to find the joining query items (<refobj> text content within the expression string).
Calculations (Model Level):
Identified by examining <queryItem> elements (Paths from #5) where the <expression> element's text is not simply a <refobj> to another item, but contains functions, operators, or literals.
Filters (Model Level):
Element: <filter> (Often found within <querySubject> or <namespace>)
Path (example, relative to a Query Subject): ./bmt:filter
Inside <filter>:
Filter Name: <name>
Filter Expression: <expression>
Extraction: Search for <filter> elements in relevant parts of the model (Query Subjects, Namespaces).
