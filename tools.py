## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

# BUG FIX: Removed invalid import and fixed with the correct import.
# SerperDevTool is imported directly from crewai_tools.
from crewai_tools import SerperDevTool

# BUG FIX: Added missing `tool` decorator import from crewai.
# CrewAI agents can only discover and invoke functions decorated with @tool.
from crewai.tools import tool

# pymupdf4llm converts PDF pages to LLM-optimised markdown,
# preserving table structure, column layout, and reading order —
# significantly better than pypdf for financial documents with data tables.
import pymupdf4llm

## Creating search tool
search_tool = SerperDevTool()

# BUG FIX: Removed class wrapper around tool functions.
# Tools are created using the @tool decorator on standalone functions.
# Class methods cause issues with CrewAI's tool registration mechanism.

@tool("Financial Document Reader")
def read_data_tool(path: str = 'data/sample.pdf') -> str:
    """Reads a PDF financial document and returns its full content as clean markdown.

    Uses pymupdf4llm which respects multi-column layout, preserves reading order,
    and renders financial tables (income statements, balance sheets, cash-flow
    statements) as proper markdown tables — far superior for LLM reasoning than
    the raw text blob produced by pypdf.

    Args:
        path (str): Path to the PDF file. Defaults to 'data/sample.pdf'.

    Returns:
        str: Full document content as LLM-optimised markdown.
    """
    return pymupdf4llm.to_markdown(path, pages=None, show_progress=False)


@tool("Investment Data Extractor")
def analyze_investment_tool(financial_document_data: str) -> str:
    """Extracts structured financial metrics from raw PDF text for investment analysis.

    Uses regex and arithmetic to pull concrete figures (revenue, EPS, margins,
    YoY deltas) from raw PDF text. Returns structured data that the Investment
    Advisor agent's LLM can reason over — rather than having the LLM guess numbers
    from unstructured prose.

    Args:
        financial_document_data (str): Raw text extracted from the financial document.

    Returns:
        str: Structured block of extracted financial metrics and computed YoY deltas.
    """
    import re
    from collections import defaultdict

    text = financial_document_data

    # ── 1. Extract dollar figures with their surrounding label ─────────────────
    money_pattern = re.compile(
        r'([\w\s]{1,40}?)\s*[:\-\u2013]?\s*'
        r'\$\s*([\d,]+(?:\.\d+)?)\s*'
        r'(billion|million|bn|b|m|k)?',
        re.IGNORECASE
    )
    plain_number_pattern = re.compile(
        r'(revenue|sales|income|profit|loss|eps|earnings per share|'
        r'gross margin|operating margin|net margin|free cash flow|capex)'
        r'[\s\w]{0,30}?'
        r'([\d,]+(?:\.\d+)?)\s*(billion|million|bn|b|m|k|%)?',
        re.IGNORECASE
    )

    multipliers = {'billion': 1000, 'bn': 1000, 'b': 1000,
                   'million': 1, 'm': 1, 'k': 0.001}

    extracted = defaultdict(list)

    for match in money_pattern.finditer(text):
        label = match.group(1).strip().lower()
        value_str = match.group(2).replace(',', '')
        unit = (match.group(3) or '').lower()
        try:
            extracted[label].append((float(value_str), unit))
        except ValueError:
            pass

    for match in plain_number_pattern.finditer(text):
        label = match.group(1).strip().lower()
        value_str = match.group(2).replace(',', '')
        unit = (match.group(3) or '').lower()
        try:
            extracted[label].append((float(value_str), unit))
        except ValueError:
            pass

    # ── 2. EPS extraction ──────────────────────────────────────────────────────
    eps_values = re.findall(
        r'(?:eps|earnings per share)[^\d$]{0,20}[\$]?\s*([\d]+\.[\d]+)',
        text, re.IGNORECASE
    )

    # ── 3. Percentage metrics (margins, growth rates) ──────────────────────────
    pct_pattern = re.compile(
        r'(gross margin|operating margin|net margin|revenue growth|yoy|year.over.year)'
        r'[^\d]{0,20}([\d]+\.?[\d]*)\s*%',
        re.IGNORECASE
    )
    percentages = [(m.group(1).strip(), m.group(2)) for m in pct_pattern.finditer(text)]

    # ── 4. YoY delta: if same metric appears ≥2 times, compute % change ───────
    # This catches current-period vs prior-period figures in the same document.
    yoy_deltas = {}
    for label, vals in extracted.items():
        if len(vals) >= 2:
            v1, u1 = vals[0]
            v2, u2 = vals[1]
            norm1 = v1 * multipliers.get(u1, 1)
            norm2 = v2 * multipliers.get(u2, 1)
            if norm2 != 0:
                delta = round((norm1 - norm2) / norm2 * 100, 2)
                yoy_deltas[label] = {
                    'current': f"${v1}{u1}",
                    'prior': f"${v2}{u2}",
                    'change_pct': delta
                }

    # ── 5. Build structured output for the agent ───────────────────────────────
    lines = ["=== EXTRACTED INVESTMENT METRICS ===", "", "--- Key Financial Figures ---"]
    shown = set()
    for label, vals in list(extracted.items())[:12]:
        k = label[:40]
        if k not in shown:
            lines.append(f"  {k.title()}: " + ", ".join(f"${v}{u}" for v, u in vals[:2]))
            shown.add(k)

    if eps_values:
        lines.append(f"  EPS: ${', $'.join(eps_values[:3])}")

    lines += ["", "--- Margin & Growth Percentages ---"]
    if percentages:
        for label, pct in percentages[:6]:
            lines.append(f"  {label.title()}: {pct}%")
    else:
        lines.append("  No explicit margin/growth percentages detected.")

    lines += ["", "--- Year-over-Year Deltas (computed) ---"]
    if yoy_deltas:
        for label, d in list(yoy_deltas.items())[:6]:
            arrow = "\u25b2" if d['change_pct'] > 0 else "\u25bc"
            lines.append(
                f"  {label.title()}: {d['current']} vs {d['prior']} "
                f"\u2192 {arrow} {abs(d['change_pct'])}% YoY"
            )
    else:
        lines.append("  Insufficient comparable figures for YoY computation.")

    lines += [
        "",
        "NOTE: Extracted via regex from raw PDF text. "
        "The Investment Advisor agent will interpret these values in context."
    ]
    return "\n".join(lines)


@tool("Risk Data Extractor")
def risk_assessment_tool(financial_document_data: str) -> str:
    """Extracts structured risk disclosure data from raw PDF text for risk assessment.

    Locates formal risk-factor sections (e.g., 10-K Item 1A), counts risk-keyword
    mentions by category, and surfaces debt/legal figures as structured data.
    Returns concrete findings that the Risk Assessment Specialist agent's LLM
    can reason over — not keyword-match opinions.

    Args:
        financial_document_data (str): Raw text extracted from the financial document.

    Returns:
        str: Structured risk disclosure summary with counts and extracted snippets.
    """
    import re

    text = financial_document_data
    text_lower = text.lower()

    # ── 1. Locate formal risk-factor section (10-K / annual report pattern) ───
    section_match = re.search(
        r'(item\s+1a\.?\s*risk\s+factors|risk\s+factors\s*\n|principal\s+risks)',
        text, re.IGNORECASE
    )
    section_found = bool(section_match)
    excerpt = (text[section_match.start():section_match.start() + 400].strip()
               if section_match else "")

    # ── 2. Count risk mentions by category ────────────────────────────────────
    # Each category has sub-patterns; total count tells the agent where to focus.
    risk_categories = {
        "Financial / Liquidity": [
            r'net loss', r'operating loss', r'cash burn', r'negative cash flow',
            r'debt covenant', r'liquidity', r'going concern', r'impairment', r'write.?down'
        ],
        "Market / Competitive": [
            r'competition', r'market share', r'demand decline', r'inflation',
            r'interest rate', r'foreign exchange', r'supply chain', r'tariff', r'geopolit'
        ],
        "Regulatory / Legal": [
            r'litigation', r'lawsuit', r'legal proceed', r'regulatory',
            r'investigation', r'class action', r'sanction', r'antitrust', r'data privacy'
        ],
        "Operational": [
            r'product recall', r'manufactur', r'quality', r'cybersecurity',
            r'data breach', r'key personnel', r'supply disrupt', r'restructur', r'layoff'
        ]
    }

    counts = {}
    examples = {}
    for cat, patterns in risk_categories.items():
        hits = []
        for pat in patterns:
            hits.extend(re.findall(r'.{0,35}' + pat + r'.{0,35}', text_lower)[:2])
        counts[cat] = len(hits)
        examples[cat] = hits[0].strip() if hits else None

    # ── 3. Debt figures extraction ─────────────────────────────────────────────
    debt_figures = [
        f"${m.group(1)}{m.group(2) or ''}"
        for m in re.finditer(
            r'(?:total debt|long.term debt|borrowings?|credit facilit)'
            r'[^\d$]{0,20}[\$]?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|bn|b|m)?',
            text, re.IGNORECASE
        )
    ][:4]

    # ── 4. Legal mention count ─────────────────────────────────────────────────
    legal_count = len(re.findall(
        r'(?:legal proceedings?|litigation|lawsuits?|claims?)', text, re.IGNORECASE
    ))

    # ── 5. Build structured output for the agent ───────────────────────────────
    lines = [
        "=== EXTRACTED RISK DISCLOSURE DATA ===", "",
        "--- Formal Risk Section ---",
        f"  Risk Factors Section Found: {'YES' if section_found else 'NO'}"
    ]
    if excerpt:
        lines.append(f"  Opening excerpt: \"{excerpt[:250]}...\"")

    lines += ["", "--- Risk Mention Counts by Category ---"]
    for cat, count in counts.items():
        severity = "HIGH" if count >= 6 else "MEDIUM" if count >= 3 else "LOW"
        lines.append(f"  {cat}: {count} mentions  [{severity}]")
        if examples[cat]:
            lines.append(f"    e.g.: \"...{examples[cat]}...\"")

    lines += ["", "--- Debt Disclosures ---"]
    lines.append(
        f"  Figures found: {', '.join(debt_figures)}" if debt_figures
        else "  No explicit debt figures detected."
    )

    lines += [
        "", "--- Legal Proceedings ---",
        f"  Legal/litigation mentions in document: {legal_count}"
    ]

    high_cats = [c for c, n in counts.items() if n >= 6]
    total = sum(counts.values())
    lines += ["", "--- Overall Risk Signal ---"]
    if high_cats:
        lines.append(f"  ELEVATED \u2014 high mention count in: {', '.join(high_cats)}")
    elif total >= 5:
        lines.append("  MODERATE \u2014 multiple risk categories have disclosures.")
    else:
        lines.append("  LOW \u2014 few risk disclosures detected in document.")

    lines += [
        "",
        "NOTE: Counts extracted via regex from raw PDF text. "
        "The Risk Assessment Specialist agent will perform qualitative analysis "
        "on top of these extracted signals."
    ]
    return "\n".join(lines)
