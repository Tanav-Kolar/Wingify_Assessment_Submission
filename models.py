"""Pydantic models for structured CrewAI task output.

Each model corresponds to one agent's output task. CrewAI enforces the schema
when `output_pydantic` is set on a Task — the LLM must return valid JSON that
matches the model, which FastAPI can then serialise directly.
"""
from pydantic import BaseModel, Field


class VerificationReport(BaseModel):
    """Output of the document-verification task."""
    document_status: str = Field(
        description="'VERIFIED' if the file is a financial document, otherwise 'REJECTED'."
    )
    document_type: str = Field(
        description="e.g. 'Earnings Report', '10-K', 'Balance Sheet', 'Investment Prospectus'."
    )
    evidence: list[str] = Field(
        description="2-3 specific financial indicators found that confirm (or deny) the document type."
    )
    recommendation: str = Field(
        description="'Proceed with full analysis' or 'Return file to user — not a financial document'."
    )


class FinancialAnalysisReport(BaseModel):
    """Output of the financial-analyst task."""
    executive_summary: str = Field(
        description="2-3 sentence overview of the document's key findings."
    )
    key_metrics: dict[str, str] = Field(
        description=(
            "Most important financial figures as a flat dict, e.g. "
            "{'Revenue Q2-2025': '$22.5B', 'Gross Margin': '18.0%', 'EPS': '$0.52'}."
        )
    )
    trend_analysis: str = Field(
        description="Year-over-year or quarter-over-quarter comparisons in plain text."
    )
    highlights: list[str] = Field(
        description="Positive developments directly supported by data from the document."
    )
    concerns: list[str] = Field(
        description="Financial warning signs or risk indicators found in the document."
    )


class InvestmentInsightsReport(BaseModel):
    """Output of the investment-advisor task."""
    investment_thesis: str = Field(
        description="Clear, evidence-based view on the company's investment case."
    )
    opportunities: list[str] = Field(
        description="Specific positive indicators from the document."
    )
    risks: list[str] = Field(
        description="Specific risk factors highlighted in the document."
    )
    suggested_considerations: list[str] = Field(
        description="Balanced investment considerations — not guarantees."
    )
    data_sources: list[str] = Field(
        description="References to specific sections of the document used as evidence."
    )


class RiskAssessmentReport(BaseModel):
    """Output of the risk-assessor task."""
    risk_summary: str = Field(
        description="Overall risk profile of the company based on the document."
    )
    financial_risks: list[str] = Field(
        description="Leverage, liquidity, and profitability risks with supporting data."
    )
    market_risks: list[str] = Field(
        description="Competitive, macroeconomic, or sector-specific risks mentioned."
    )
    regulatory_risks: list[str] = Field(
        description="Legal or regulatory issues noted in the document."
    )
    risk_ratings: dict[str, str] = Field(
        description=(
            "Simple High/Medium/Low rating per risk category, e.g. "
            "{'Financial': 'Medium', 'Market': 'High', 'Regulatory': 'Low'}."
        )
    )
