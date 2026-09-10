# Student Knowledge System - Re-Architecture Walkthrough

This document outlines the changes made to build a robust Student Knowledge System using Supabase (for full content) and ChromaDB (for semantic search).

## 1. System Architecture

The system uses a "Dual-Store" approach:
-   **Supabase (`inbox_items` table)**: Acts as the **Source of Truth**. It stores the FULL extracted text of every file, along with metadata (Google Drive links, titles).
-   **ChromaDB**: Stores **Chunks** (vectors) of the content. Each chunk has an `item_id` that points back to the full record in Supabase.

### Schema Highlights
-   **Deterministic UUIDs**: We generate UUIDs (UUIDv5) based on the Google Classroom ID. This ensures that `item_id` is consistent across both databases and future runs.
-   **Courses Table**: Maps course names (e.g., "MA2150") to unique UUIDs.
-   **Full Content Storage**: The `files_data` column in Supabase is a JSONB array containing the `content` (text) of all attached files.

## 2. Ingestion Pipeline

The script [src/services/ingest_complete.py](file:///f:/IITH/epoch/src/services/ingest_complete.py) handles the entire process:
1.  **Loads Data**: Reads [data.json](file:///f:/IITH/epoch/data.json) and [courses.json](file:///f:/IITH/epoch/courses.json).
2.  **Ingests Courses**: Upserts all courses into Supabase first (to satisfy Foreign Key constraints).
3.  **Ingests Items**:
    -   Generates the deterministic `item_id`.
    -   Upserts the full record into Supabase.
    -   Splits content into ~500-word chunks.
    -   Upserts chunks into ChromaDB with metadata (`course_id`, `item_id`, `source_link`).

## 3. The Agent (Brain)

The Agent ([src/brain/agent.py](file:///f:/IITH/epoch/src/brain/agent.py)) is equipped with three key tools:

### KnowledgeRetriever
-   **Search Mode**: Takes a query (e.g., "fixed point theorem") and a course ID (e.g., "MA2150"). It searches ChromaDB for relevant chunks and returns snippets with **Link Citations**.
-   **Read Mode**: Takes an `item_id`. It fetches the **Full Content** from Supabase, allowing the agent to "read" entire documents/assignments to answer deep questions.

### Other Tools
-   **ProfileTool**: Fetches student details.
-   **CalendarTool**: Manages the schedule.

## 4. Verification

We verified the system with [test_agent_e2e.py](file:///f:/IITH/epoch/test_agent_e2e.py):
-   **Query**: "What is the fixed point theorem in MA2150?"
-   **Result**: The Agent successfully mapped "MA2150" to its UUID, searched ChromaDB, and returned relevant information.

## How to Run

1.  **Ingest Data**:
    ```bash
    python src/services/ingest_complete.py
    ```

2.  **Run Agent**:
    ```bash
    python src/brain/agent.py
    ```
