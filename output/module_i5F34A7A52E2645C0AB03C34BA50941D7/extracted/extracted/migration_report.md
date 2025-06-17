# Migration Report: CognosModule

## Summary

- **Report Name**: CognosModule
- **Migration Date**: 2025-06-17 15:06:27

## Data Model

- **Model Name**: CognosModule Data Model
- **Tables**: 3

### Tables

- **Orders**
  - Columns: 22
  - Column details:
    - Row Id (Int64)
    - Row ID (Int64)
    - Order ID (String)
    - Order Date (DateTime)
    - Ship Date (DateTime)
    - Ship Mode (String)
    - Customer ID (String)
    - Customer Name (String)
    - Segment (String)
    - Country/Region (String)
    - City (String)
    - State/Province (String)
    - Postal Code (String)
    - Region (String)
    - Product ID (String)
    - Category (String)
    - Sub-Category (String)
    - Product Name (String)
    - Sales (Double)
    - Quantity (Int64)
    - Discount (Double)
    - Profit (Double)

- **People**
  - Columns: 5
  - Column details:
    - Row Id (Int64)
    - Regional Manager (String)
    - Region (String)
    - Area (String)
    - Country (String)

- **Returns**
  - Columns: 3
  - Column details:
    - Row Id (Int64)
    - Returned (String)
    - Order ID (String)


### Relationships

- Orders.Region → People.Region
- Orders.Order_ID → Returns_.Order_ID

## Report

- **Report ID**: report_b5bfb278-21b5-42cb-aea5-08679fa0700a
- **Report Name**: CognosModule Report
- **Pages**: 1

### Pages

- **Overview**
  - No visuals


## Next Steps

1. Open the generated .pbit file in Power BI Desktop
2. Review and fix any errors in the data model
3. Connect to the appropriate data source
4. Refresh the data
