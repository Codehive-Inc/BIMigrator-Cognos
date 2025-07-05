Prerequisite: Access to the Cognos Analytics environment (for API calls in Types 1 & 3) and an External JSON Configuration File (containing data source connection mappings, Power BI naming conventions, and crucially, Package structure mappings for Types 2 & 4) are assumed for the migration tool's execution.
Migration Type	Description / Focus	Primary Inputs Needed for Tool Execution	Outcome (Power BI Artifacts)
Type 1: Module + Report Pair	Migrates a specific report and builds the dataset based on its linked Cognos Data Module.	- Specific Cognos Report ID / XML.<br>- External JSON Configuration file.	- One Power BI Dataset (.Dataset) derived from the Module.<br>- One Power BI Report (.Report) derived from the Report.<br>- Typically packaged together in a .pbip.
Type 2: Package + Report Pair	Migrates a specific report and builds the dataset based on its linked Cognos Package (structure from JSON).	- Specific Cognos Report ID / XML.<br>- External JSON Configuration file (must contain mapping for the Package used by the report).	- One Power BI Dataset (.Dataset) derived from the Package (structure defined in JSON).<br>- One Power BI Report (.Report) derived from the Report.<br>- Typically packaged together in a .pbip.
Type 3: Module Only (Dataset Only)	Migrates only a specific Cognos Data Module to create a reusable Power BI Dataset.	- Specific Cognos Module ID.<br>- External JSON Configuration file.	- One Power BI Dataset (.Dataset) derived from the Module.
Type 4: Package Only (Dataset Only)	Migrates only a specific Cognos Package (structure from JSON) to create a reusable Power BI Dataset.	- Specific Cognos Package Name / ID.<br>- External JSON Configuration file (must contain mapping for this Package).	- One Power BI Dataset (.Dataset) derived from the Package (structure defined in JSON).
Type 5: Report Layout Only (Dataset Assumed)	Migrates only the layout and visuals of a Cognos Report, linking it to a specified, existing Power BI Dataset.	- Specific Cognos Report ID / XML.<br>- Name/ID of the Target Power BI Dataset (this Dataset must already exist).<br>- External JSON Configuration file (for layout/field mappings).	- One Power BI Report (.Report) linked to the specified existing Dataset.
This table should serve as a clear guide for structuring the different execution paths or commands within your migration framework.


Given that a Cognos developer can provide you with specific details like "this Module ID is used by this Report ID" or "this Package (defined by this Framework Manager model) is used by this Report ID," we can define migration "types" based on these primary inputs.
This is a valid way to classify the execution workflows or commands your migration tool needs to support.
Let's break down the migration types based on the primary input you'd get from a developer:
Migration Type 1: Migrate a Specific Report and its Supporting Module (The "Module + Report" Pair)
Primary Input: A specific Report ID (from which you can get the report.xml) where the report's <modelPath> points to a Cognos Data Module.
Goal: Create the Power BI Dataset corresponding to the Module AND the Power BI Report layout corresponding to the specific Report.
Process:
Parse the Report report.xml. Identify the specific Module ID it uses.
Execute Data Model Migration (Scope 1): Connect to the Cognos Analytics API using the Module ID to extract its structure (tables, columns, relationships, module calcs). Use the JSON config (connection mappings, naming conventions) to generate the Power BI Dataset definition (.Dataset folder with TMDL files and M queries). This step needs to handle potential idempotency (if the Dataset for this Module was already migrated).
Execute Report Layout Migration (Scope 3): Parse the Report report.xml again (or continue processing). Translate its layout, visuals, field mappings, and report-specific calculations/filters. Generate the Power BI Report layout definition (.Report folder) ensuring it connects to the Power BI Dataset created in step 2 (based on the Module name mapping).
Outcome: A Power BI Project (.pbip) containing one Dataset derived from the Module and one Report derived from the specific input Report ID.
Migration Type 2: Migrate a Specific Report and its Supporting Package (The "Package + Report" Pair)
Primary Input: A specific Report ID (from which you get the report.xml) where the report's <modelPath> points to a Cognos Package, AND the External JSON Configuration file which must contain the pre-defined structure mapping for that specific Package.
Goal: Create the Power BI Dataset corresponding to the Package (as defined in the JSON) AND the Power BI Report layout corresponding to the specific Report.
Process:
Parse the Report report.xml. Identify the specific Package name it uses.
Validate JSON Config: Verify that the JSON Configuration file contains a mapping for this Package name. If not, migration cannot proceed (Package structure is unknown).
Execute Data Model Migration (Scope 2): Use the Package structure details from the JSON config and connection mappings from the JSON to generate the Power BI Dataset definition (.Dataset folder with TMDL files and M queries). This step needs to handle potential idempotency.
Execute Report Layout Migration (Scope 3): Parse the Report report.xml. Translate its layout, visuals, field mappings (mapping Cognos Package items to Power BI items based on the JSON config), and report-specific calculations/filters. Generate the Power BI Report layout definition (.Report folder) ensuring it connects to the Power BI Dataset created in step 3 (based on the Package name mapping).
Outcome: A Power BI Project (.pbip) containing one Dataset derived from the Package (via JSON config) and one Report derived from the specific input Report ID.
Migration Type 3: Migrate ONLY a Specific Module (The "Module Only" or "Dataset Only")
Primary Input: A specific Module ID.
Goal: Create only the Power BI Dataset corresponding to the Module, without migrating any specific report layout yet.
Process:
Execute Data Model Migration (Scope 1): Connect to the Cognos Analytics API using the Module ID to extract its structure. Use the JSON config (connection mappings, naming conventions) to generate the Power BI Dataset definition (.Dataset folder).
Outcome: A Power BI Project (.pbip) containing only a Dataset.
Migration Type 4: Migrate ONLY a Specific Package (The "Package Only" or "Dataset Only")
Primary Input: A specific Package Name/ID, AND the External JSON Configuration file containing the mapping for this Package.
Goal: Create only the Power BI Dataset corresponding to the Package (as defined in the JSON), without migrating any specific report layout yet.
Process:
Validate JSON Config: Verify the JSON contains a mapping for this Package name.
Execute Data Model Migration (Scope 2): Use the Package structure details from the JSON config and connection mappings to generate the Power BI Dataset definition (.Dataset folder).
Outcome: A Power BI Project (.pbip) containing only a Dataset.
Are these the only types?
You might also consider:
Migration Type 5: Migrate ONLY a Specific Report Layout (assuming Dataset exists): Input is a Report ID, requires the existing PB Dataset name. This is purely Scope 3.
Migration Type 6: Bulk Migration of Reports from a Module/Package: Input is a Module ID or Package Name/ID. Process is Type 3/4 to create the Dataset, then iterate through all reports using that Module/Package and execute Type 5 for each.
Conclusion:
Yes, classifying the migration based on the developer's input (Module/Report pair, Package/Report pair, or just Module/Package ID) makes sense for structuring your tool's commands or workflows.
Type 1 (Module+Report) & Type 2 (Package+Report) are the most common "end-to-end for one report's source" workflows. They combine a Dataset migration step with a Report Layout migration step.
Type 3 (Module Only) & Type 4 (Package Only) are useful for building the foundational datasets independently.
Type 2 and Type 4 fundamentally rely on your prior work to define the Package structure in the JSON config, as the tool cannot extract it directly like a Module.