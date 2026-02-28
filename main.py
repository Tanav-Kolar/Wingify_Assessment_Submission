from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from crewai import Crew, Process, Task
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from models import VerificationReport, FinancialAnalysisReport, InvestmentInsightsReport, RiskAssessmentReport
from database import engine, get_db, Base
from db_models import AnalysisJob

# Import task descriptors (description, expected_output, tools) for template reuse.
# Fresh Task instances are created per request to avoid shared .output state.
from task import (
    analyze_financial_document as _analysis_desc,
    verification as _verify_desc,
    investment_analysis as _invest_desc,
    risk_assessment as _risk_desc,
)

# Create all DB tables on startup (SQLite file created automatically)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Financial Document Analyzer",
    description="Multi-agent AI pipeline for financial document analysis.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_output(task: Task, model_class):
    """Safely extract a task's Pydantic output, falling back to its raw text."""
    if task.output is None:
        return None
    if task.output.pydantic:
        return task.output.pydantic.model_dump()
    return {"raw": task.output.raw}


def run_crew(query: str, file_path: str) -> dict:
    """Run the four-agent CrewAI pipeline and return ALL task outputs.

    Creates fresh Task instances per call so .output state is never shared
    between concurrent requests.

    Returns:
        dict with keys: verification, financial_analysis,
                        investment_analysis, risk_assessment
    """
    t_verify = Task(
        description=_verify_desc.description,
        expected_output=_verify_desc.expected_output,
        agent=verifier,
        tools=_verify_desc.tools,
        output_pydantic=VerificationReport,
        async_execution=False,
    )
    t_analyze = Task(
        description=_analysis_desc.description,
        expected_output=_analysis_desc.expected_output,
        agent=financial_analyst,
        tools=_analysis_desc.tools,
        output_pydantic=FinancialAnalysisReport,
        async_execution=False,
    )
    t_invest = Task(
        description=_invest_desc.description,
        expected_output=_invest_desc.expected_output,
        agent=investment_advisor,
        tools=_invest_desc.tools,
        output_pydantic=InvestmentInsightsReport,
        async_execution=False,
    )
    t_risk = Task(
        description=_risk_desc.description,
        expected_output=_risk_desc.expected_output,
        agent=risk_assessor,
        tools=_risk_desc.tools,
        output_pydantic=RiskAssessmentReport,
        async_execution=False,
    )

    crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[t_verify, t_analyze, t_invest, t_risk],
        process=Process.sequential,
    )

    crew.kickoff(inputs={"query": query, "file_path": file_path})

    return {
        "verification":        _task_output(t_verify,  VerificationReport),
        "financial_analysis":  _task_output(t_analyze, FinancialAnalysisReport),
        "investment_analysis": _task_output(t_invest,  InvestmentInsightsReport),
        "risk_assessment":     _task_output(t_risk,    RiskAssessmentReport),
    }


def _background_analysis(job_id: str, query: str, file_path: str):
    """Background worker function — runs the crew pipeline and writes results to DB.

    Runs in a separate thread via FastAPI BackgroundTasks.
    Handles status transitions: queued → running → done | failed.
    Always cleans up the uploaded PDF file when finished.
    """
    from database import SessionLocal
    db = SessionLocal()
    try:
        # Mark as running
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        job.status = "running"
        db.commit()

        # Execute the four-agent pipeline
        result = run_crew(query=query, file_path=file_path)

        # Persist structured result
        job.status = "done"
        job.result = result
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

    finally:
        db.close()
        # Clean up uploaded file after processing completes
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Health check — confirms the API is running."""
    return {"message": "Financial Document Analyzer API is running", "version": "1.0.0"}


@app.post("/analyze", tags=["Analysis"], status_code=202)
async def analyze_document(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="PDF financial document to analyse"),
    query: str = Form(
        default="Analyze this financial document for investment insights",
        description="Natural language query — e.g. 'What was gross profit in Q4-2024?'",
    ),
):
    """Submit a financial document for async AI analysis.

    Returns a `job_id` immediately. The four-agent pipeline runs in the
    background. Poll `GET /result/{job_id}` to retrieve the structured output.
    """
    if not query or query.strip() == "":
        query = "Analyze this financial document for investment insights"

    # Save uploaded file to disk (background task reads it)
    os.makedirs("data", exist_ok=True)
    job_id = str(uuid.uuid4())
    file_path = f"data/job_{job_id}.pdf"

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # Persist job record with status=queued
    job = AnalysisJob(
        job_id=job_id,
        query=query.strip(),
        filename=file.filename or "upload.pdf",
        status="queued",
    )
    db.add(job)
    db.commit()

    # Enqueue background processing (runs in a thread pool)
    background_tasks.add_task(_background_analysis, job_id, query.strip(), file_path)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Analysis queued. Poll GET /result/{job_id} for results.",
    }


@app.get("/result/{job_id}", tags=["Analysis"])
async def get_result(job_id: str, db: Session = Depends(get_db)):
    """Poll the status and result of a previously submitted analysis job.

    Status values:
    - `queued`  — job is waiting to start
    - `running` — agents are actively processing the document
    - `done`    — structured results are available in the `analysis` field
    - `failed`  — an error occurred; see the `error` field
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    response = {
        "job_id": job.job_id,
        "status": job.status,
        "query": job.query,
        "file": job.filename,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }

    if job.status == "done":
        response["analysis"] = job.result
    elif job.status == "failed":
        response["error"] = job.error

    return response


@app.get("/jobs", tags=["Analysis"])
async def list_jobs(
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all past analysis jobs stored in the database.

    Optional query params:
    - `limit`  — max number of jobs to return (default 20)
    - `status` — filter by status (queued / running / done / failed)
    """
    query = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc())
    if status:
        query = query.filter(AnalysisJob.status == status)
    jobs = query.limit(limit).all()

    return [
        {
            "job_id": j.job_id,
            "status": j.status,
            "query": j.query,
            "file": j.filename,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)