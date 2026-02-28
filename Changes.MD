# Changes Log — Financial Document Analyzer

> Tracks all changes made to fix the original bugs and add new features.
> Each section corresponds to one source file.

---

## `.env` *(New File)*

| Change | Reason |
|--------|--------|
| Created `.env` with `GEMINI_API_KEY` and `SERPER_API_KEY` placeholders | No `.env` file existed — all LLM and tool calls failed at runtime without it |

---

## `requirements.txt`

| Change | Reason |
|--------|--------|
| Added `python-dotenv` | Used by `agents.py` and `tools.py` via `load_dotenv()` but missing from dependencies |
| Added `uvicorn` | Required to serve the FastAPI app; without it `python main.py` fails |
| Added `python-multipart` | FastAPI requires this package to handle `multipart/form-data` file uploads |
| Replaced `openai` with nothing | Project uses Gemini, not OpenAI; unneeded dependency removed |
| Added `pymupdf4llm` | Replaced the non-existent `Pdf(...)` call in `tools.py`; outputs LLM-optimised markdown with tables preserved from financial PDFs |
| Added `sqlalchemy` | Required for SQLite database integration (bonus feature) |

---

## `tools.py`

| Change | Reason |
|--------|--------|
| Removed `from crewai_tools import tools` | `tools` is not a valid importable from `crewai_tools`; caused `ImportError` at startup |
| Added `from crewai.tools import tool` | The `@tool` decorator is required for CrewAI agents to discover and invoke tool functions |
| Replaced class-based tool definitions with standalone `@tool` functions | Instance methods inside classes caused `TypeError` (no `self`); `@tool` must be on a module-level function |
| Removed `async` from all tool functions | CrewAI tools must be synchronous; `async` causes incompatibility with the agent execution loop |
| Replaced `Pdf(file_path=path).load()` with `pymupdf4llm.to_markdown(path)` | `Pdf` never existed; `pymupdf4llm` extracts clean markdown from PDFs, preserving table structure — far superior for LLM reasoning than raw text blobs |
| Implemented `analyze_investment_tool` with regex extraction | Original was a stub; replaced with regex patterns that extract dollar figures, percentage metrics, and EPS values |
| Implemented `risk_assessment_tool` with regex + keyword scanning | Original was a stub; replaced with section detection, debt figure extraction, and category-based risk keyword counting |

---

## `agents.py`

| Change | Reason |
|--------|--------|
| Fixed `from crewai.agents import Agent` → `from crewai import Agent` | `crewai.agents` is not a valid sub-module |
| Removed `llm = llm` (undefined self-reference) | Caused immediate `NameError` at startup |
| Initialised `llm = LLM(model="gemini/gemini-3-flash-preview", api_key=...)` | Uses CrewAI's native `LLM` class to configure Gemini; API key loaded from `.env` |
| Fixed `tool=[...]` → `tools=[...]` on `financial_analyst` | `tool` (singular) is silently ignored by CrewAI; `tools` (plural) is the correct keyword |
| Increased `max_iter=1` → `max_iter=5` on `financial_analyst` | One iteration is insufficient for multi-step financial analysis |
| Rewrote all four agent goals and backstories | Originals encouraged hallucination, fabricated advice, and nonsensical behaviour; replaced with professional, grounded mandates |

---

## `task.py`

| Change | Reason |
|--------|--------|
| Rewrote descriptions and expected_outputs for all four tasks | Originals instructed agents to fabricate data, make up URLs, and ignore the user query |
| Added `{file_path}` interpolation to all task descriptions | Without it, `read_data_tool` always used the hardcoded default path instead of the uploaded file |
| Fixed `verification` task: `agent=financial_analyst` → `agent=verifier` | Task was assigned to the wrong agent |
| Added `output_pydantic=<Model>` to all four tasks | Enforces structured JSON output (typed Pydantic models) instead of raw unstructured strings |

---

## `models.py` *(New File)*

| Change | Reason |
|--------|--------|
| Created four Pydantic output models (`VerificationReport`, `FinancialAnalysisReport`, `InvestmentInsightsReport`, `RiskAssessmentReport`) | Provides typed, validated JSON output for each agent's task; used via `output_pydantic` in `task.py` |

---

## `main.py`

| Change | Reason |
|--------|--------|
| Renamed endpoint `analyze_financial_document` → `analyze_document` | Original name shadowed the imported CrewAI Task of the same name, causing `run_crew()` to receive the endpoint function instead of the Task object |
| Added `file_path` to `crew.kickoff()` inputs | The uploaded file path was accepted but never forwarded; agents always fell back to `data/sample.pdf` |
| Added all four agents and tasks to the `Crew` | Original only included `financial_analyst` + one task; the other three agents never ran |
| Rewrote to collect all task outputs individually | Original returned only `str(response)` — the last agent's raw output. Now all four agents' structured results are collected and returned |
| Replaced synchronous endpoint with `BackgroundTasks` async queue | `POST /analyze` now returns a `job_id` immediately (202); the four-agent pipeline runs in a background thread *(bonus feature)* |
| Added `GET /result/{job_id}` endpoint | Allows polling for job status (`queued → running → done \| failed`) and retrieving structured results *(bonus feature)* |
| Added `GET /jobs` endpoint | Lists all past analysis jobs from the database *(bonus feature)* |
| Changed `uvicorn.run(app, ...)` → `uvicorn.run("main:app", ...)` | `reload=True` requires a string module reference; passing the object raises `ValueError` |

---

## `database.py` *(New File)*

| Change | Reason |
|--------|--------|
| Created SQLAlchemy engine + session factory for SQLite | Enables persistent job storage with no external database server required *(bonus feature)* |

---

## `db_models.py` *(New File)*

| Change | Reason |
|--------|--------|
| Created `AnalysisJob` ORM model | Stores job ID, query, filename, status, structured result JSON, error message, and timestamps for every analysis request *(bonus feature)* |
