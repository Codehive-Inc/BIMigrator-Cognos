# Cognos to Power BI Migration Paths

| Migration Type | Description | Inputs | Outputs |
|---------------|-------------|--------|----------|
| **Type 1: Module + Report Pair** | Migrates a specific report and its linked Cognos Data Module | - Cognos Report ID<br>- JSON Configuration file | - Power BI Dataset (.Dataset)<br>- Power BI Report (.Report) |
| **Type 2: Package + Report Pair** | Migrates a specific report and its linked Cognos Package | - Cognos Report ID<br>- JSON Configuration file with Package mapping | - Power BI Dataset (.Dataset)<br>- Power BI Report (.Report) |
| **Type 3: Module Only** | Migrates only a Cognos Data Module | - Cognos Module ID<br>- JSON Configuration file | - Power BI Dataset (.Dataset) |
| **Type 4: Package Only** | Migrates only a Cognos Package | - Cognos Package Name/ID<br>- JSON Configuration file with Package mapping | - Power BI Dataset (.Dataset) |
| **Type 5: Report Layout Only** | Migrates only report layout, linking to existing dataset | - Cognos Report ID<br>- Target Power BI Dataset name | - Power BI Report (.Report) |
| **Type 6: Folder Migration** | Migrates all reports in a folder | - Folder ID<br>- Optional recursive flag | - Multiple Power BI Reports |
| **Type 7: Package File Migration** | Migrates a Framework Manager package file | - Package file path<br>- Optional folder ID or report IDs | - Power BI Dataset (.Dataset) |