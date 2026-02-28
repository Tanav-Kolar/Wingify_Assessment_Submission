# Bug Report — Financial Document Analyzer

> All bugs identified across the **original** codebase, organised by file.

---

## `requirements.txt`

| # | Bug |
|---|-----|
| 1 | Missing `python-dotenv` — used by `agents.py` and `tools.py` via `load_dotenv()` but not listed |
| 2 | Missing `uvicorn` — needed to run the FastAPI server; `python main.py` fails without it |
| 3 | Missing a PDF parsing library — `tools.py` calls `Pdf(...)` which requires a PDF package that is never listed as a dependency |
| 4 | Missing `python-multipart` — FastAPI requires this to handle `multipart/form-data` file uploads |
| 5 | `google-generativeai` listed but the correct CrewAI/LLM bridge package was absent |
| 6 | `openai` listed unnecessarily — project uses Gemini, not OpenAI |

---

## `tools.py`

| # | Line | Bug |
|---|------|-----|
| 1 | 6 | `from crewai_tools import tools` — `tools` is not a valid importable module from `crewai_tools`; causes `ImportError` at startup |
| 2 | 14 | `read_data_tool` is not decorated with `@tool` — agents cannot discover or call it |
| 3 | 14 | `async def read_data_tool` — CrewAI tools must be synchronous; `async` causes incompatibility with the agent execution loop |
| 4 | 24 | `Pdf(file_path=path).load()` — `Pdf` is never imported and does not exist anywhere in the codebase |
| 5 | 14 | `read_data_tool` defined as an instance method with no `self` parameter — raises `TypeError` when called |
| 6 | 41 | `analyze_investment_tool` — same `async` / missing `self` issues as `read_data_tool` |
| 7 | 58 | `create_risk_assessment_tool` — same `async` / missing `self` issues |

---

## `agents.py`

| # | Line | Bug |
|---|------|-----|
| 1 | 7 | `from crewai.agents import Agent` — `crewai.agents` is not a valid sub-module; correct import is `from crewai import Agent` |
| 2 | 12 | `llm = llm` — self-referencing undefined variable; causes `NameError` immediately |
| 3 | 12 | No LLM configured — must be initialised with a model name and API key from `.env` |
| 4 | 28 | `tool=[...]` (singular) — CrewAI's `Agent` only accepts `tools` (plural); `tool` is silently ignored |
| 5 | 17 | `financial_analyst` goal instructs the agent to "make up investment advice even if you don't understand" |
| 6 | 20–26 | `financial_analyst` backstory encourages hallucination and fabricating financial figures |
| 7 | 36–52 | `verifier` goal says "just say yes to everything"; backstory encourages approving any file |
| 8 | 56–74 | `investment_advisor` goal/backstory instructs agent to recommend fake products and Discord servers |
| 9 | 78–94 | `risk_assessor` goal promotes YOLO investing and calls diversification "for the weak" |
| 10 | 30–31 | `max_iter=1, max_rpm=1` on `financial_analyst` — one iteration is insufficient for complex analysis |

---

## `task.py`

| # | Line | Bug |
|---|------|-----|
| 1 | 9–14 | `analyze_financial_document` description instructs agent to use imagination, make up URLs, and ignore the query |
| 2 | 16–20 | `analyze_financial_document` expected_output asks for contradictions, made-up jargon, and fake URLs |
| 3 | 29–33 | `investment_analysis` description tells agent to ignore the user query and recommend random products |
| 4 | 35–41 | `investment_analysis` expected_output asks for contradictory and fabricated investment advice |
| 5 | 50–54 | `risk_assessment` description ignores user query and recommends fabricated dramatic risk scenarios |
| 6 | 56–62 | `risk_assessment` expected_output demands impossible strategies and fake institutions |
| 7 | 71–73 | `verification` description says "just guess" and encourages hallucinating financial terminology |
| 8 | 75–77 | `verification` expected_output tells agent to approve non-financial documents as financial |
| 9 | 79 | `verification` task assigned `agent=financial_analyst` — should be `agent=verifier` |

---

## `main.py`

| # | Line | Bug |
|---|------|-----|
| 1 | 8, 29 | Endpoint function named `analyze_financial_document` shadows the same-named imported CrewAI Task — `run_crew()` receives the endpoint function instead of the Task object |
| 2 | 12–21 | `run_crew` accepts `file_path` but never passes it to `crew.kickoff()` — agents always fall back to the hardcoded `data/sample.pdf` |
| 3 | 12–21 | `Crew` initialised with only one agent and one task — the other three agents never run |
| 4 | 74 | `uvicorn.run(app, ..., reload=True)` — `reload=True` requires a string reference (`"main:app"`), not the app object; raises `ValueError` |

---

## `.env` *(Missing File)*

| # | Bug |
|---|-----|
| 1 | No `.env` file — `GEMINI_API_KEY` and `SERPER_API_KEY` are never defined, causing all LLM and tool calls to fail |

---

## Summary

| File | Bugs |
|------|------|
| `requirements.txt` | 6 |
| `tools.py` | 7 |
| `agents.py` | 10 |
| `task.py` | 9 |
| `main.py` | 4 |
| `.env` | 1 |
| **Total** | **37** |
