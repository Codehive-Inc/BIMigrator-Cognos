# Migration Report: MaterialReceiptDetail_UC016

## Summary

- **Report Name**: MaterialReceiptDetail_UC016
- **Migration Date**: 2025-08-10 11:51:20

## Data Model

- **Model Name**: ReportDataModel
- **Tables**: 4

### Tables

- **PURCHASE_ORDER_RECEIPT**
  - Columns: 9
  - Column details:
    - DATE_ENTERED (string)
    - SITE_NUMBER (string)
    - PO_NUMBER (string)
    - PO_LINE_NUMBER (string)
    - RELEASE_NUMBER (string)
    - DATE_RECEIVED_AT_SITE (string)
    - QTY_RECEIVED (string)
    - TIME_ENTERED (string)
    - UNIT_PRICE (string)

- **PURCHASE_ORDER_LINE**
  - Columns: 5
  - Column details:
    - ITEM_NUMBER (string)
    - JOB_NUMBER (string)
    - UNIT_OF_MEASURE (string)
    - REQUESTOR_NAME (string)
    - VENDOR_NAME (string)

- **STORAGE_LOCATION**
  - Columns: 2
  - Column details:
    - LOCATION1 (string)
    - LOCATION2 (string)

- **PURCHASE_ORDER_DESCRIPTIONS**
  - Columns: 1
  - Column details:
    - DESCRIPTION1 (string)


## Report

- **Report ID**: MaterialReceiptDetail_UC016
- **Report Name**: MaterialReceiptDetail_UC016
- **Pages**: 1

### Pages

- **Page1**
  - No visuals


## Next Steps

1. Open the generated .pbit file in Power BI Desktop
2. Review and fix any errors in the data model
3. Connect to the appropriate data source
4. Refresh the data
