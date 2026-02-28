## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

#BUG FIX: Corrected import path for Agent and LLM classes from crewai.
from crewai import Agent
from crewai import LLM

# Genuine I/O and data-extraction tools — analysis/reasoning is done by each agent's LLM.
from tools import search_tool, read_data_tool, analyze_investment_tool, risk_assessment_tool


# BUG FIX: The original code had `llm = llm` which is a self-referencing undefined variable.
# Used LLM class from crewai to initialize the LLM.
llm = LLM(
    model="gemini/gemini-3-flash-preview",  # Gemini 2.5 Flash Preview
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7
)


#Financial Analyst agent
financial_analyst = Agent(
    # BUG FIX: Rewrote role, goal, and backstory to be professional and accurate.
    role="Senior Financial Analyst",
    goal=(
        "Thoroughly analyze the uploaded financial document and provide accurate, evidence-based insights in response to the user query: {query}."
        "Identify key financial metrics, trends, and risks described in the document."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a seasoned financial analyst with 15 years of experience analyzing corporate earnings reports, balance sheets, and investment documents. "
        "You rely strictly on the data present in the document and credible external sources. "
        "You never fabricate facts or invent financial figures. "
        "You communicate clearly and professionally, citing specific sections of the document."
    ),
    # BUG FIX: Changed `tool` (invalid keyword) to `tools`. 
    tools=[read_data_tool],
    llm=llm,
    # BUG FIX: Increased max_iter from 1 to 5.
    max_iter=5,
    max_rpm=10,
    allow_delegation=False  # Single analyst — no delegation needed for primary analysis
)

# Creating a document verifier agent
verifier = Agent(
    # BUG FIX: Rewrote role, goal, and backstory to be professional and accurate.
    role="Financial Document Verifier",
    goal=(
        "Verify that the uploaded document is a legitimate financial document "
        "(e.g., earnings report, balance sheet, 10-K, investment prospectus). "
        "Confirm the document contains structured financial data before proceeding with analysis."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a meticulous document compliance specialist with a background in financial auditing."
        "You carefully review every document to confirm it contains genuine financial content such as revenue figures, balance sheet items, or investment data. You reject non-financial documents with a clear explanation."
    ),
    llm=llm,
    # BUG FIX: Increased max_iter from 1 to 3. 
    max_iter=3,
    max_rpm=10,
    allow_delegation=False # Single agent — no delegation needed.
)


investment_advisor = Agent(
    # BUG FIX: Rewrote role, goal, and backstory to be professional and accurate.
    role="Investment Strategy Advisor",
    goal=(
        "Based on the financial document analysis, provide balanced and evidence-based investment insights."
        "Highlight opportunities and risks found in the document. "
        "All recommendations must be grounded in the document's actual data."
    ),
    verbose=True,
    backstory=(
        "You are a chartered financial analyst (CFA) with deep expertise in equity research and portfolio strategy."
        "You provide objective, data-driven investment insights strictly derived from the documents and market data at hand."
        "You always disclose relevant risks and never guarantee returns."
    ),
    llm=llm,
    #Changes: Increased max_iter from 1 to 3.
    max_iter=3,
    max_rpm=10,
    allow_delegation=False
)


risk_assessor = Agent(
    # BUG FIX: Rewrote role, goal, and backstory to be professional and accurate.
    role="Risk Assessment Specialist",
    goal=(
        "Identify and evaluate financial, market, and operational risks described in the financial document. Provide a structured risk assessment with likelihood and impact ratings based on the data in the document."
    ),
    verbose=True,
    backstory=(
        "You are a risk management professional with experience in quantitative risk modeling, regulatory compliance, and portfolio risk analysis."
        "You follow established frameworks such as VaR and stress testing to deliver measured, evidence-based risk assessments."
        "You avoid speculation and clearly distinguish between documented risks and assumptions."
    ),
    llm=llm,
    max_iter=3,
    max_rpm=10,
    allow_delegation=False
)
