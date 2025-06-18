# Migration Report: CognosModule

## Summary

- **Report Name**: CognosModule
- **Migration Date**: 2025-06-18 08:17:28

## Data Model

- **Model Name**: CognosModule Data Model
- **Tables**: 3

### Tables

- **Orders**
  - Columns: 22
  - Column details:
    - _row_id (Int64)
    - Row_ID (Int64)
    - Order_ID (String)
    - Order_Date (DateTime)
    - Ship_Date (DateTime)
    - Ship_Mode (String)
    - Customer_ID (String)
    - Customer_Name (String)
    - Segment (String)
    - Country_Region (String)
    - City (String)
    - State_Province (String)
    - Postal_Code (String)
    - Region (String)
    - Product_ID (String)
    - Category (String)
    - Sub_Category (String)
    - Product_Name (String)
    - Sales (Double)
    - Quantity (Int64)
    - Discount (Double)
    - Profit (Double)

- **People**
  - Columns: 5
  - Column details:
    - _row_id (Int64)
    - Regional_Manager (String)
    - Region (String)
    - Area (String)
    - Country (String)

- **Returns_**
  - Columns: 3
  - Column details:
    - _row_id (Int64)
    - Returned (String)
    - Order_ID (String)


### Relationships

- Orders.Region → People.Region
- Orders.Order_ID → Returns_.Order_ID

## Report

- **Report ID**: report_b964b9a0-8f3a-419a-a1e8-2d24008c6cfd
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
