## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor   
# I/O and data-extraction tools — LLM reasoning stays at the agent level.
from tools import search_tool, read_data_tool, analyze_investment_tool, risk_assessment_tool

## Creating a task to analyze the uploaded financial document
analyze_financial_document = Task(
    description=(
        "Analyze the uploaded financial document in detail to address the user's query: {query}.\n"
        "Use the Financial Document Reader tool with the file path '{file_path}' to extract the full text.\n"
        "Identify and summarize:\n"
        "  1. Key financial metrics (revenue, profit, EPS, debt ratios, etc.)\n"
        "  2. Year-over-year or quarter-over-quarter trends\n"
        "  3. Business highlights and management commentary\n"
        "  4. Any red flags or notable concerns mentioned in the document.\n"
        "Base your analysis strictly on the content of the document."
    ),
    expected_output=(
        "A structured financial analysis report containing:\n"
        "- Executive Summary: 2–3 sentence overview of the document's key findings\n"
        "- Key Financial Metrics: a table or bullet list of the most important figures\n"
        "- Trend Analysis: year-over-year or quarter-over-quarter comparisons\n"
        "- Notable Highlights: positive developments from the document\n"
        "- Concerns / Risk Indicators: any financial warning signs found in the document\n"
        "All points must be directly supported by data from the uploaded document."
    ),
    agent=financial_analyst,
    tools=[read_data_tool],
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description=(
        "Based on the financial document at '{file_path}', provide investment insights relevant "
        "to the user's query: {query}.\n"
        "Use the Investment Data Extractor tool with the full text from the document to extract "
        "concrete financial figures (revenue, EPS, margins, YoY deltas).\n"
        "Provide investment considerations strictly grounded in the document's data.\n"
        "Clearly distinguish between what the document states and any external context."
    ),
    expected_output=(
        "An investment insights report containing:\n"
        "- Investment Thesis: a clear, evidence-based view on the company's investment case\n"
        "- Opportunities: specific positive indicators from the document\n"
        "- Risks: specific risk factors highlighted in the document\n"
        "- Suggested Considerations: balanced investment considerations (not guarantees)\n"
        "- Data Sources: references to the specific sections of the document used"
    ),
    agent=investment_advisor,
    tools=[analyze_investment_tool],
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description=(
        "Perform a structured risk assessment of the financial document at '{file_path}' "
        "for the query: {query}.\n"
        "Use the Risk Data Extractor tool with the full document text to scan for formal risk "
        "sections, count disclosure mentions by category, and surface debt/legal figures.\n"
        "Evaluate the severity and likelihood of each identified risk based on "
        "the financial figures and commentary in the document."
    ),
    expected_output=(
        "A structured risk assessment report containing:\n"
        "- Risk Summary: overall risk profile of the company based on the document\n"
        "- Financial Risks: leverage, liquidity, profitability risks with supporting data\n"
        "- Market Risks: competitive, macroeconomic, or sector-specific risks mentioned\n"
        "- Regulatory / Compliance Risks: any legal or regulatory issues noted\n"
        "- Risk Ratings: a simple High / Medium / Low rating for each risk category\n"
        "All risks must be grounded in data from the uploaded document."
    ),
    agent=risk_assessor,
    tools=[risk_assessment_tool],
    async_execution=False,
)


verification = Task(
    description=(
        "Verify that the uploaded file at '{file_path}' is a valid financial document before analysis begins.\n"
        "Use the Financial Document Reader tool with path '{file_path}' to extract the document text.\n"
        "Check for the presence of financial indicators such as:\n"
        "  - Revenue, profit, or loss figures\n"
        "  - Balance sheet items (assets, liabilities, equity)\n"
        "  - Cash flow statements\n"
        "  - Earnings per share or financial ratios\n"
        "If the document does not contain financial data, clearly reject it with an explanation."
    ),
    expected_output=(
        "A short verification report stating:\n"
        "- Document Status: VERIFIED (is a financial document) or REJECTED (not a financial document)\n"
        "- Evidence: 2-3 specific financial indicators found (if verified) or reason for rejection\n"
        "- Document Type: e.g., Earnings Report, 10-K, Balance Sheet, Investment Prospectus\n"
        "- Recommendation: whether to proceed with full analysis or return the file to the user"
    ),
    agent=verifier,
    tools=[read_data_tool],
    async_execution=False
)