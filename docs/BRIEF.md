# Frontend Technical Brief: Blinkit Discovery Engine

This brief outlines the backend architecture, API contract, and core flows to guide the frontend UI generation for the Blinkit Discovery Engine.

## Project Objective
The Blinkit Discovery Engine is an AI-powered data pipeline and Retrieval-Augmented Generation (RAG) chat application designed for product teams. It aggregates unstructured customer feedback across multiple platforms (App Store, Play Store, Reddit, YouTube), extracts behavioral taxonomy using LLMs, and allows users to query this massive dataset to uncover actionable product insights backed by explicit citations.

## API Endpoints

### 1. Chat (RAG)
**`POST /api/chat`**
- **Description:** Submits a natural language query to the RAG engine to retrieve insights and synthesize an answer.
- **Required Params:** `question` (string)
- **Optional Params:** `filters` (object/dict for metadata filtering)
- **Response Shape:**
  ```json
  {
    "answer": "String containing the synthesized LLM response.",
    "citations": [
      {
        "id": "play_store:12345",
        "snippet": "String of the original review/comment",
        "source": "play_store"
      }
    ],
    "source_breakdown": {
      "play_store": 14,
      "app_store": 1
    },
    "llm_used": "Gemini"
  }
  ```

### 2. Ingestion Status & Trigger (Admin)
**`POST /api/admin/ingest`**
- **Description:** Triggers the background data ingestion pipeline.
- **Headers Required:** `Authorization: Bearer <ADMIN_SECRET>`
- **Required Params:** `mode` (string: strictly `"demo"` or `"full"`)
- **Response Shape:**
  ```json
  {
    "status": "accepted",
    "message": "Pipeline started in demo mode",
    "run_id": "uuid-string"
  }
  ```

**`GET /api/admin/ingest/status`**
- **Description:** Polls the current live state of the ingestion pipeline.
- **Params:** None
- **Response Shape:**
  ```json
  {
    "status": "idle | running | completed | failed",
    "run_id": "uuid-string | null",
    "message": "Human readable status (e.g., 'Fetching from play_store...')"
  }
  ```

### 3. Pipeline Stats
**`GET /api/stats`**
- **Description:** Fetches historical funnel metrics for completed pipeline runs.
- **Params:** None
- **Response Shape:** Array of stat objects.
  ```json
  [
    {
      "run_id": "uuid-string",
      "source": "app_store",
      "run_timestamp": "2026-07-22T14:17:23Z",
      "raw_ingested": 250,
      "stage1_passed": 120,
      "stage2_tagged": 115,
      "relevant_embedded": 115,
      "irrelevant_discarded": 135
    }
  ]
  ```

## Data Models
- **Citation:** The fundamental unit of proof for the RAG engine, containing the exact text (`snippet`) and the origin (`source`).
- **PipelineStats:** Tracks the attrition of data across the ingestion pipeline (Raw → Filtered → Tagged → Embedded).
- **IngestStatus:** Represents the global state machine of the backend worker (Idle vs. Running).

## Core User Flows

### Flow 1: Insight Discovery (End User)
1. User lands on the main Chat Interface.
2. User types a product question (e.g., *"Why do users order fruits on Blinkit?"*).
3. The UI displays a loading skeleton or spinner (LLM synthesis takes 3–8 seconds).
4. UI renders the synthesized `answer`, visually linking claims to the `citations` list.
5. UI displays badge indicators for the `source_breakdown`.

### Flow 2: Analytics Dashboard (Metrics & Funnel)
1. User clicks on a "Dashboard" or "Stats" tab.
2. UI calls `GET /api/stats` to fetch historical pipeline runs.
3. UI renders a visual representation of the ingestion funnel (e.g., bar charts or a metric table) showing how data drops off: `raw_ingested` → `stage1_passed` (filtered) → `stage2_tagged` (LLM extracted) → `relevant_embedded`.
4. This provides users absolute transparency into how much data exists in the vector database per source.

### Flow 3: Data Ingestion (Admin)
1. Admin clicks a settings/admin toggle to reveal the `IngestionControl` panel.
2. Admin enters the `ADMIN_SECRET` token into a UI input field.
3. The UI must present two distinct, highly visible ingestion buttons:
   - **"Quick Demo Run"**: Triggers `POST /api/admin/ingest` with `{"mode": "demo"}`. (Fast ~45s run, strictly capped at 25 items per source to protect API credits).
   - **"Full Pipeline Run"**: Triggers `POST /api/admin/ingest` with `{"mode": "full"}`. (Long-running background job, processes thousands of items using state-based pagination).
4. Upon clicking either button, the UI immediately disables both triggers and begins polling `/api/admin/ingest/status` every 2-3 seconds.
5. The UI displays the live `message` (e.g., "Extracting app_store taxonomy with LLM...") in a progress bar or status badge.
6. Once `status === "completed"`, the UI stops polling, re-enables the buttons, and optionally triggers a refresh of the Stats dashboard.

## Auth & Permissions
- **Public Chat:** The `/api/chat` and `/api/stats` endpoints are unauthenticated. The chat interface is accessible to anyone.
- **Protected Admin:** The `/api/admin/ingest` endpoint is protected via Bearer token validation. The UI must provide a way for an admin to supply this token (e.g., a modal, a settings gear, or an inline input) before attempting to trigger a run. If an invalid token is passed, the backend throws a `401 Unauthorized`.

## State & Real-Time Behavior
- **Polling Required:** The backend does not use WebSockets. The UI must actively poll `/api/admin/ingest/status` to achieve real-time pipeline updates.
- **Long-Running Chat Requests:** The `/api/chat` POST request holds the connection open while the LLM generates the response. The frontend must handle the timeout/loading state gracefully.

## Edge Cases / Validation Rules
- **Ingestion Active Lock:** If `/api/admin/ingest/status` returns `status === "running"`, the UI **must disable** the "Demo" and "Full" ingest buttons to prevent duplicate background jobs from overlapping.
- **Mode Constraint:** The ingestion payload strictly requires `{"mode": "demo"}` or `{"mode": "full"}`.
- **Empty Prompts:** The Chat UI should disable the Send button if the question input is empty or just whitespace.
- **API Failures:** If the LLM rate limit is breached or a connector fails, the backend will return a 500 error or a `failed` pipeline status. The UI must catch these errors and display a toast/alert rather than crashing.
