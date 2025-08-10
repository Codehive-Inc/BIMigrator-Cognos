# Definitive Guide to Migration Entry Points

This document provides a clear breakdown of the primary migration workflows, the specific backend functions to call for each, their key inputs, and what to expect as output.

---

### **1. Single Report Migration**

-   **Goal**: To migrate a single Cognos report into its own, self-contained Power BI project.
-   **Entry Point**: `cognos_migrator.migrations.report.migrate_single_report`
-   **Key Inputs**:
    -   `output_path`, `cognos_url`, `session_key`
    -   **EITHER** `report_id` (from live server)
    -   **OR** `report_file_path` (from local XML)
-   **Output**: A single Power BI Project for that report.

---

### **2. Standalone Module Migration**

-   **Goal**: To migrate a full Cognos Data Module from a live server into a Power BI dataset.
-   **Entry Point**: `cognos_migrator.migrations.module.migrate_module_with_explicit_session`
-   **Key Inputs**:
    -   `module_id`: The ID of the Data Module on the live Cognos server.
    -   `output_path`, `cognos_url`, `session_key`
-   **Output**: A single Power BI Project (Dataset only).

---

### **3. Standalone Package Migration**

-   **Goal**: To migrate a full Cognos Framework Manager (FM) Package from a local XML file into a Power BI dataset.
-   **Entry Point**: `cognos_migrator.migrations.package.migrate_package_with_explicit_session`
-   **Note**: While the function name contains `_explicit_session`, it is the correct entry point for local package files.
-   **Key Inputs**:
    -   `package_file_path`: The file path to a local FM package XML file.
    -   `output_path`
    -   `cognos_url` (Required for authentication context, even with local files)
    -   `session_key` (Required for authentication context, even with local files)
-   **Output**: A single Power BI Project (Dataset only).

---

### **4. Shared Semantic Model (Package + Reports)**

-   **Goal**: To create a single, shared semantic model by combining a local FM Package file with one or more reports. This produces **one consolidated Power BI project**.
-   **Logic**: This process deconstructs the reports to find the underlying source tables they use. It then filters the main FM package to include only those required tables and their direct relationships, creating a lean and efficient final model. This behavior can be configured in `settings.json`.
-   **This path has two variations based on the source of the reports:**

    #### **A. Package File + Live Reports (by ID)**
    -   **Entry Point**: `cognos_migrator.migrations.package.migrate_package_with_reports_explicit_session`
    -   **Key Inputs**: `package_file_path`, `output_path`, `report_ids`, `cognos_url`, `session_key`

    #### **B. Package File + Local Report Files**
    -   **Entry Point**: `cognos_migrator.migrations.package.migrate_package_with_local_reports`
    -   **Key Inputs**: `package_file_path`, `output_path`, `report_file_paths`, `cognos_url`, `session_key`

-   **Output (for both A and B)**: A single, consolidated Power BI Project containing only the tables and relationships from the package that are required by the reports. 