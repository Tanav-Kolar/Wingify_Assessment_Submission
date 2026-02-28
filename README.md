# Financial Document Analyzer

A multi-agent AI pipeline that analyzes financial PDFs and returns structured insights across four specialized agents: **Verifier**, **Financial Analyst**, **Investment Advisor**, and **Risk Assessor**.

Built with [CrewAI](https://crewai.com), [FastAPI](https://fastapi.tiangolo.com), and powered by Google Gemini.

---

## Architecture

```
POST /analyze  ──►  [FastAPI]  ──►  BackgroundTasks queue  ──►  returns job_id instantly
                                            │
                                    ┌───────▼────────┐
                                    │  CrewAI Pipeline│
                                    │  1. Verifier    │
                                    │  2. Fin Analyst │
                                    │  3. Inv Advisor │
                                    │  4. Risk Assess │
                                    └───────┬────────┘
                                            │
                                    SQLite (analysis.db)
                                            │
GET /result/{job_id}  ◄─────────────────────┘
GET /jobs             ◄─── lists all past jobs
```

PDF text is extracted using **pymupdf4llm** which converts financial PDFs into clean markdown — preserving table structure, column layout, and reading order — far superior to plain text extraction for LLM reasoning.

Each agent returns a **typed Pydantic model** (no raw strings), so all API responses are structured JSON.

---

## Bugs Fixed

37 bugs were found and fixed across 6 files. See [`BUGS.md`](./BUGS.md) for the full table. Key critical fixes:

| File | Bug | Fix |
|------|-----|-----|
| `tools.py` | `Pdf(...)` — class never existed | Replaced with `pymupdf4llm.to_markdown()` |
| `tools.py` | Tools inside classes, missing `@tool` decorator, all `async` | Refactored to standalone `@tool` functions |
| `agents.py` | `llm = llm` — undefined self-reference | Configured `LLM(model="gemini/...")` with API key |
| `agents.py` | `tool=[...]` (singular) | Fixed to `tools=[...]` (plural) |
| `agents.py` | Agent goals/backstories encouraged hallucination | Rewrote all four agents with correct prompts |
| `task.py` | Task descriptions instructed agents to make up data | Rewrote all four tasks with correct, grounded instructions |
| `task.py` | `{file_path}` missing from task descriptions | Added so agents receive the correct PDF path |
| `task.py` | `verification` task assigned to `financial_analyst` | Fixed to `verifier` agent |
| `main.py` | `analyze_financial_document` endpoint shadowed the imported Task | Renamed endpoint to `analyze_document` |
| `main.py` | `file_path` never passed to `crew.kickoff()` | Fixed — agents now receive the uploaded file |
| `main.py` | Only 1 of 4 agents included in `Crew` | All four agents and tasks now included |
| `main.py` | `str(response)` returned only the last agent's output | All four agents' outputs now returned individually |
| `requirements.txt` | `python-multipart` missing (needed for file uploads) | Added |

---

## Design Decisions & Tool Notes

### `search_tool` (SerperDevTool) — present but intentionally unused

The original boilerplate imported `SerperDevTool` and created `search_tool`, implying agents should use it for live web search. However, **none of the four agents have `search_tool` assigned to them**, and this is deliberate:

- The brief is to analyze an **uploaded financial document** — all insights must be grounded in the document's actual content, not external sources.
- Web search access would blend external data with document data, making it impossible to audit whether a claim came from the document or the internet.
- `SERPER_API_KEY` is **not required** to run the system. It is retained in `.env` and `tools.py` purely to remain faithful to the original repository structure.

### `analyze_investment_tool` & `risk_assessment_tool` — why mock tools?

The original stubs implied the `investment_advisor` and `risk_assessor` agents should have dedicated tools. These were implemented as **regex-based data extractors** that scan document text for financial figures, percentage metrics, debt figures, and risk keywords.

However, there is a strong argument that **these agents do not need tools at all**:

> In the CrewAI pattern, **tools handle I/O and data extraction — LLMs handle reasoning**. The `financial_analyst` already reads the full document and passes its structured output as context to subsequent agents in the sequential pipeline. The `investment_advisor` and `risk_assessor` receive that analysis directly and can reason over it natively — no tool required.

The mock tools effectively re-extract information the LLM already has in its context window, adding little practical value. **Sending data directly to the LLM for reasoning produces better results** with fewer token round-trips. They are retained in this submission to be faithful to the original codebase's intent of giving each agent a tool.

---

## Prerequisites

- Python 3.12+
- A Google Gemini API key → [Get one free](https://aistudio.google.com/apikey)
- A Serper API key → [Get one free](https://serper.dev) _(optional — see note below)_

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd Wingify_Assessment_Submission
```

### 2. Create and activate the virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### 5. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at `http://localhost:8000`. The SQLite database (`analysis.db`) is created automatically on first run — no setup required.

---

## API Reference

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

---

### `GET /`
Health check.

```bash
curl http://localhost:8000/
```
```json
{ "message": "Financial Document Analyzer API is running", "version": "1.0.0" }
```

---

### `POST /analyze`
Submit a financial PDF for analysis. Returns a `job_id` immediately — processing happens in the background.

**Request** (`multipart/form-data`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | PDF file | ✅ | Financial document to analyze |
| `query` | string | ❌ | Natural language question (default: full analysis) |

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@/path/to/tesla_q2_2025.pdf" \
  -F "query=What was the gross profit in Q4-2024?"
```

**Response** `202 Accepted`:
```json
{
  "job_id": "3f2a1b4c-...",
  "status": "queued",
  "message": "Analysis queued. Poll GET /result/3f2a1b4c-... for results."
}
```

---

### `GET /result/{job_id}`
Poll for the status and result of a submitted job.

**Status values:** `queued` → `running` → `done` | `failed`

> **⏱ Expected latency:** The pipeline runs four sequential LLM calls, each with the full PDF (~30K tokens of context). On the Gemini free tier this typically takes **5–15 minutes** per job. This is a function of the LLM API's latency and rate limits, not a system error — the `running` status confirms the pipeline is actively processing. 

```bash
curl http://localhost:8000/result/3f2a1b4c-...
```

**Response when `done`:**
```json
{
  "job_id": "3f2a1b4c-...",
  "status": "done",
  "query": "What was the gross profit in Q4-2024?",
  "file": "tesla_q2_2025.pdf",
  "created_at": "2025-02-28T07:44:00",
  "completed_at": "2025-02-28T07:46:12",
  "analysis": {
    "verification": {
      "document_status": "VERIFIED",
      "document_type": "Earnings Report",
      "evidence": ["Revenue tables", "EPS figures", "Operating income"],
      "recommendation": "Proceed with full analysis"
    },
    "financial_analysis": {
      "executive_summary": "Tesla reported ...",
      "key_metrics": { "Gross Profit Q4-2024": "$3.7B", "Gross Margin": "16.3%" },
      "trend_analysis": "Gross profit declined 15% YoY ...",
      "highlights": ["Record energy deployment"],
      "concerns": ["Margin compression", "FCF decline"]
    },
    "investment_analysis": { "investment_thesis": "...", "opportunities": [...], ... },
    "risk_assessment": { "risk_summary": "...", "financial_risks": [...], ... }
  }
}
```

**Response when `failed`:**
```json
{ "job_id": "...", "status": "failed", "error": "..." }
```

---

### `GET /jobs`
List all past analysis jobs from the database.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max jobs to return |
| `status` | string | — | Filter: `queued`, `running`, `done`, `failed` |

```bash
# All recent jobs
curl http://localhost:8000/jobs

# Only completed jobs
curl "http://localhost:8000/jobs?status=done&limit=5"
```

```json
[
  {
    "job_id": "3f2a1b4c-...",
    "status": "done",
    "query": "What was gross profit in Q4-2024?",
    "file": "tesla_q2_2025.pdf",
    "created_at": "2025-02-28T07:44:00",
    "completed_at": "2025-02-28T07:46:12"
  }
]
```

---

## Bonus Features

### Queue Worker Model
`POST /analyze` is non-blocking — it enqueues the analysis job and returns immediately with a `job_id`. The four-agent pipeline runs in a background thread via FastAPI `BackgroundTasks`. Multiple requests can be in-flight simultaneously without blocking each other.

### Database Integration
Every job is persisted in a local **SQLite** database (`analysis.db`) via **SQLAlchemy**. The database stores:
- Job ID, status, and timestamps
- The original query and filename
- All four agents' full structured outputs as JSON

The database is created automatically on server startup — no setup required.

---

## Project Structure

```
├── main.py          # FastAPI app, endpoints, BackgroundTasks queue
├── agents.py        # Four CrewAI agents (Verifier, Analyst, Advisor, Assessor)
├── task.py          # Task definitions with correct prompts and tool assignments
├── tools.py         # read_data_tool (pymupdf4llm), investment + risk tools
├── models.py        # Pydantic output models for structured agent responses
├── database.py      # SQLAlchemy engine + session (SQLite)
├── db_models.py     # AnalysisJob ORM model
├── requirements.txt # Python dependencies
├── .env             # API keys (not committed to git)
├── BUGS.md          # Full bug report with 37 bugs documented
└── data/            # Temporary storage for uploaded PDFs (auto-cleaned)
```
