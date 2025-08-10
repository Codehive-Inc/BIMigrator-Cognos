# Migration Report: MaterialInquiryDetail_UC012

## Summary

- **Report Name**: MaterialInquiryDetail_UC012
- **Migration Date**: 2025-08-10 11:51:17

## Data Model

- **Model Name**: ReportDataModel
- **Tables**: 3

### Tables

- **ITEM_SITE_EXTRACT**
  - Columns: 25
  - Column details:
    - SITE_NUMBER (string)
    - ITEM_NUMBER (string)
    - DESCRIPTION (string)
    - UNIT_OF_MEASURE (string)
    - QTY_ON_HAND (string)
    - MINIMUM (string)
    - CONSUMABLE (string)
    - SHELF_LIFE (string)
    - MAXIMUM (string)
    - DATE_LAST_ISSUED (string)
    - DATE_LAST_RETURNED (string)
    - DATE_LAST_RECEIVED (string)
    - UTC_IND (string)
    - PRIMARY_LOC (string)
    - SECONDARY_LOC (string)
    - STATUS (string)
    - QA_CODE (string)
    - QA_LEVEL (string)
    - QA_CERT1 (string)
    - QA_CERT2 (string)
    - QA_CERT3 (string)
    - QA_CERT4 (string)
    - PIT (string)
    - PREVENT_MAINTENANCE (string)
    - SAP_IND (string)

- **PURCHASE_ORDER_LINE**
  - Columns: 4
  - Column details:
    - PO_NUMBER (string)
    - PO_LINE_NUMBER (string)
    - RELEASE_NUMBER (string)
    - STATUS_DATE (string)

- **MATERIAL_CHARGES**
  - Columns: 4
  - Column details:
    - SITE_NUMBER (string)
    - ITEM_NUMBER (string)
    - CHARGED_DATE (string)
    - TRANSACTION_TYPE (string)


## Report

- **Report ID**: MaterialInquiryDetail_UC012
- **Report Name**: MaterialInquiryDetail_UC012
- **Pages**: 1

### Pages

- **Page1**
  - No visuals


## Next Steps

1. Open the generated .pbit file in Power BI Desktop
2. Review and fix any errors in the data model
3. Connect to the appropriate data source
4. Refresh the data
