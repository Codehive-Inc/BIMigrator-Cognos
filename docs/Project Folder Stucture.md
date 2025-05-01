
**Project Folder Structure :**

1.  **Root Directory:** Standard files like `.gitignore`, `README.md`, `requirements.txt`.
2.  **`config/`:** Holds static configuration, crucially the `mappings/` definitions which drive the translation logic between specific tool pairs.
3.  **`data/`:** Contains sample inputs for development/testing and serves as a potential output location. Separating by tool helps organization.
4.  **`docs/`:** Essential for explaining the CIM, architecture, and how to use the tool.
5.  **`scripts/`:** For helpful operational scripts separate from the core tool logic.
6.  **`src/` (or `migration_tool/`):** The main Python package.
    *   **`cim/`:** Defines the central, abstract data structure.
    *   **`common/`:** Utilities used across different parts of the application (logging, file I/O).
    *   **`mapping/`:** Handles loading and accessing the rules defined in `config/mappings/`.
    *   **`parsers/`:** Contains sub-modules for each *source* tool. This is where you add logic to read Tableau XML, Cognos specs, etc., and convert them into the CIM format.
    *   **`transformation/`:** The engine room. It takes the CIM instance, uses the mapping configuration, orchestrates calls to AI services (like for calculation translation), and prepares data for the generator.
    *   **`generators/`:** Contains sub-modules for each *target* tool. This takes the (potentially transformed) CIM instance and generates the specific files/structures needed by Power BI, target Tableau, etc.
    *   **`cli.py`/`main.py`:** Entry points to run the migration process.
7.  **`tests/`:** Crucial for ensuring reliability. Mirroring the `src` structure helps organize tests. Includes unit tests (testing individual components in isolation) and integration tests (testing the full flow).
