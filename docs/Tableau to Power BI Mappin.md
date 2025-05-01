{
  "cimVersion": "1.1", // Incremented version
  "migrationMetadata": { /* ... as before ... */ },
  "workbook": {
    "id": "wbk-001",
    "name": "Original Tableau Workbook Name",
    "_sourceMetadata": {
      "xmlPath": "/workbook",
      "fileName": "myReport.twb"
    },
    "_targetHint": {
      "targetFileType": ".pbix",
      "primaryComponents": ["DataModel", "Report/Layout", "Connections"]
    },
    "datasources": [
      {
        "id": "ds-001",
        "name": "Sales Data Source", // Tableau Datasource Caption
        "_sourceMetadata": {
          "xmlPath": "/workbook/datasources/datasource[@name='federated.1a2b3c4d']", // Internal name
          "caption": "Sales Data Source"
        },
        "_targetHint": {
          "targetFile": "DataModel", // Connection info stored within the model for PBI
          "pbiDatasetName": "Sales Data Source" // Suggested PBI Dataset name
        },
        "connection": {
          "id": "conn-001",
          "type": "sqlserver",
          /* ... other connection properties ... */
          "_sourceMetadata": {
            "xmlPath": "/workbook/datasources/datasource/connection[@class='sqlserver']",
            "attributes": { "server": "salesdb.example.com", "dbname": "SalesDW", "schema": "dbo", "authentication": "windows" }
          },
          "_targetHint": {
            "targetFile": "Connections (implicitly in DataModel)", // M queries define connections
            "powerQueryFunction": "Sql.Database",
            "mQueryTemplate": "Source = Sql.Database(\"{server}\", \"{database}\", [Query=\"SELECT * FROM {schema}.{table}\"])", // Example template
            "importMode": "directQuery" // Previously "_powerBiMappingHint"
          }
        },
        "model": {
           "_sourceMetadata": {
             "xmlPath": "/workbook/datasources/datasource[@name='...']/connection/metadata-records" // Or logical query structure
           },
           "_targetHint": {
              "targetFile": "DataModel", // Core of the PBI dataset
              "tmslStructure": "model/tables, model/relationships" // Path within Tabular Model Scripting Language (TMSL) JSON
           },
          "tables": [
            {
              "id": "tbl-001",
              "name": "FactSales", // Tableau logical table name (caption)
              "physicalTable": "FactSales", // Tableau physical table name
              /* ... */
              "_sourceMetadata": {
                "xmlPath": "/workbook/datasources/datasource/connection/relation[@name='FactSales']", // Or metadata-record path
                "type": "table" // Tableau relation type
              },
              "_targetHint": {
                "targetFile": "DataModel",
                "tmslPath": "model/tables('FactSales')" // TMSL path
              }
            }
             // ... other tables
          ],
          "relationships": [
            {
              "id": "rel-001",
              /* ... from/to info ... */
              "_sourceMetadata": {
                 "xmlPath": "/workbook/datasources/datasource/connection/_.*/clause[@type='join']/expression[@op='=']" // Simplified path example
              },
              "_targetHint": {
                  "targetFile": "DataModel",
                  "tmslPath": "model/relationships",
                  "properties": ["fromTable", "fromColumn", "toTable", "toColumn", "cardinality", "crossFilteringBehavior"]
              }
            }
            // ... other relationships
          ]
        },
        "fields": [
          {
            "id": "fld-001",
            "datasourceId": "ds-001",
            "tableId": "tbl-001",
            "name": "[OrderQuantity]", // Tableau field caption
            "sourceColumn": "OrderQuantity", // Tableau 'remote-name' or 'local-name'
            /* ... type, role, etc. ... */
            "_sourceMetadata": {
              "xmlPath": "/workbook/datasources/datasource/column[@caption='OrderQuantity']", // Can also be in metadata-records
              "attributes": {"datatype": "integer", "role": "measure", "name": "[sqlproxy.0abc...].[OrderQuantity]"} // Example internal name
            },
            "_targetHint": {
              "targetFile": "DataModel",
              "tmslPath": "model/tables('FactSales')/columns('OrderQuantity')", // TMSL path for the column
              "pbiProperties": ["name", "dataType", "isHidden", "formatString", "summarizeBy"]
            }
          },
          {
            "id": "fld-101",
            "datasourceId": "ds-001",
            "name": "[Sales Amount]",
            "fieldType": "calculatedField",
            /* ... calculation, type, role ... */
            "_sourceMetadata": {
              "xmlPath": "/workbook/datasources/datasource/column[@caption='Sales Amount']",
              "attributes": { "role": "measure", "type": "quantitative", "datatype": "real" },
              "formulaXmlPath": "calculation[@formula='...']" // Path to the formula attribute
            },
            "_targetHint": {
              "targetFile": "DataModel",
              "targetType": "measure", // Explicit target type
              "tmslPath": "model/tables('FactSales')/measures('Sales Amount')", // DAX Measures belong to tables
              "pbiProperties": ["name", "expression", "isHidden", "formatString"] // Key PBI measure properties
            }
          }
          // ... other fields (Parameters, Sets, Hierarchies would have similar hints)
        ]
      }
    ],
    "worksheets": [
      {
        "id": "ws-001",
        "name": "Sales Overview Bar Chart", // Tableau Sheet Name
         "_sourceMetadata": {
           "xmlPath": "/workbook/worksheets/worksheet[@name='Sales Overview Bar Chart']"
         },
         "_targetHint": {
            "targetFile": "Report/Layout", // Visuals live in the report layout
            "pbiPageName": "Sales Overview Bar Chart", // Suggested PBI Page Name
            "pbiPageIndex": 0 // Suggested order
         },
        "visualizations": [
          {
            "id": "viz-001",
            "vizType": "bar",
            "_sourceMetadata": {
              "xmlPath": "/workbook/worksheets/worksheet[@name='...']/table/view",
              "markClass": "Bar", // Tableau uses mark types
              "shelvesXmlPath": "/workbook/worksheets/worksheet[@name='...']/table/rows | ./cols | ./aggregation/encodings/*" // Paths to shelves
            },
            "_targetHint": {
              "targetFile": "Report/Layout",
              "layoutJsonPath": "sections(0)/visualContainers(0)", // Example path in Layout JSON
              "pbiVisualType": "clusteredBarChart",
              "configJsonPath": "sections(0)/visualContainers(0)/config", // Path to visual config
              "dataRolesMapping": { // Map CIM shelves to PBI data roles
                "Category": "shelves.columns[0].fieldId",
                "Y": "shelves.rows[0].fieldId",
                "Legend": "shelves.color[0].fieldId",
                "Tooltips": "shelves.tooltip[*].fieldId"
              }
            }
          }
        ],
        "filters": [
          {
             "id": "filt-001",
             /* ... filter details ... */
             "_sourceMetadata": {
                "xmlPath": "/workbook/worksheets/worksheet[@name='...']/filter[@column='...']" // Or datasource-filter
             },
             "_targetHint": {
                "targetFile": "Report/Layout",
                "targetScope": "visual", // "visual", "page", "report"
                "pbiFilterType": "relativeDate", // e.g., advanced, topN, relativeDate
                "layoutJsonPath": "sections(0)/filters(0)" // Path in Layout JSON
             }
          }
        ]
      }
    ],
    "dashboards": [
      {
          "id": "db-001",
          "name": "Executive Summary",
          "_sourceMetadata": {
             "xmlPath": "/workbook/dashboards/dashboard[@name='Executive Summary']"
          },
          "_targetHint": {
             "targetFile": "Report/Layout",
             "pbiPageName": "Executive Summary",
             "pbiPageIndex": 1
          },
          "objects": [
             {
                "id": "dbo-001",
                "type": "worksheet",
                "worksheetId": "ws-001",
                "_sourceMetadata": {
                   "xmlPath": "/workbook/dashboards/dashboard[@name='...']/zones/zone[@name='Sales Overview Bar Chart']", // Zone containing worksheet
                   "zoneAttributes": {"id": "1", "type": "viz", "param": "Sales Overview Bar Chart"}
                },
                "_targetHint": {
                   "targetFile": "Report/Layout",
                   "layoutJsonPath": "sections(1)/visualContainers(1)", // A different container on the dashboard page
                   "isBookmarkTarget": false // Could be hint if used in actions
                }
             }
             // ... other dashboard objects (text boxes, filters, parameters)
          ]
          // ... actions with similar annotations
      }
    ]
  }
}