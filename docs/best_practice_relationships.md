# Best Practices for Relationship Creation and Ambiguity Resolution

This document outlines the advanced, automated strategy used by BIMigrator-Cognos to build a clean, robust, and unambiguous relationship model from a raw Cognos package.

## The Problem: Ambiguous Paths

When migrating complex models, it's common for multiple relationship paths to exist between tables. For example, a `MATERIAL_CHARGES` table might be related directly to an `ITEM_SITE_EXTRACT` table, but also indirectly through a `PURCHASE_ORDER_LINE` table.

-   **Path 1 (Direct):** `MATERIAL_CHARGES` -> `ITEM_SITE_EXTRACT`
-   **Path 2 (Indirect):** `MATERIAL_CHARGES` -> `PURCHASE_ORDER_LINE` -> `ITEM_SITE_EXTRACT`

This creates ambiguity. When a user builds a report, the Power BI DAX engine doesn't know which path to use for filtering, resulting in errors and an invalid model.

## The Solution: A Two-Pass Post-Processing Algorithm

To solve this, the migrator uses a sophisticated two-pass approach that guarantees a valid model by intelligently selecting the best relationships and discarding those that would cause ambiguity.

### Pass 1: Generate the Raw, Unfiltered Model

The first pass of the migration is intentionally "dumb." The `PowerBIProjectGenerator` reads all potential relationships from the source Cognos package and writes them into the `relationships.tmdl` file.

This creates a temporary file that contains the complete, unfiltered "spiderweb" of relationships, including all the duplicates and ambiguous paths. This step is crucial because it gives our processor the full context of the model's structure before making any decisions.

### Pass 2: The `TMDLPostProcessor` Cleans the Model

After the initial, messy TMDL file is generated, a dedicated `TMDLPostProcessor` is invoked. This processor is the core of our intelligent relationship-building logic.

It performs the following steps:

#### 1. Parse the Raw TMDL File

The processor reads the entire `relationships.tmdl` file and parses it into an in-memory list of relationship objects.

#### 2. Prioritize Every Relationship

This is the most critical step. The processor analyzes every potential relationship and assigns it a priority score based on a set of robust heuristics. The goal is to identify which relationships form the strong, structural backbone of the star schema.

The prioritization logic is as follows:

-   **Key Strength (Primary Criterion):** Relationships are first judged by the semantic strength of the columns they join on.
    -   **Priority 1 (Strong):** Relationships on columns that look like primary or foreign keys (e.g., containing `_id`, `_key`, `number`, `code`) are considered strong and essential.
    -   **Priority 3 (Weak):** Relationships on generic or status-like columns (e.g., `status`, `stop`, `date`) are considered weak.
-   **Table Centrality (Tie-Breaker):** If two relationships have the same key strength, the processor uses "centrality" as a tie-breaker. It counts how many relationships each table participates in. A relationship involving a more "central" table (one with more connections) is given a higher priority.

This results in a list of all potential relationships, sorted from most essential to least essential.

#### 3. Build the Clean Model Iteratively

The processor initializes a new, empty relationship graph. It then iterates through the **prioritized list** from the previous step and evaluates each relationship one by one.

For each relationship, it asks a simple question: **"Does a path between these two tables *already* exist in the clean graph I'm building?"**

-   **If NO:** The relationship is a valid, non-ambiguous connection. It is **ADDED** to the final list of clean relationships, and the new connection is recorded in the graph.
-   **If YES:** Adding this relationship would create a second, competing path. The relationship is therefore **DISCARDED**, and a log message is written explaining why it was removed.

A special exception is made to **ignore paths that go through the `CentralDateTable`**. This prevents the algorithm from incorrectly discarding valid relationships just because both tables happen to connect to the central calendar.

#### 4. Overwrite the TMDL File

Once the iteration is complete, the processor takes the final list of clean, unambiguous relationships and completely overwrites the original `relationships.tmdl` file.

## The Result

The final output is a perfectly structured `relationships.tmdl` file that Power BI can load without any ambiguity errors. This automated, deterministic process ensures that every migration produces a robust and performant star schema that is ready for analysis. 