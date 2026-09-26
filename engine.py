import os
from openai import OpenAI
from dotenv import load_dotenv

# Import our Pydantic contracts from models.py
from models import AmbiguityCheckResult, SQLGenerationResult, SQLCorrectionResult

# Load environment variables from .env
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database schema ground truth
DB_SCHEMA = """
Table: customers
  - id (INTEGER, PRIMARY KEY)
  - name (VARCHAR)
  - email (VARCHAR, UNIQUE)
  - signup_date (DATE)

Table: orders
  - id (INTEGER, PRIMARY KEY)
  - customer_id (INTEGER, FOREIGN KEY references customers.id)
  - total_amount (NUMERIC)
  - status (VARCHAR: allowed values: 'completed', 'cancelled', 'refunded')
  - order_date (DATE)
"""


# ------------------------------------------------------------------------------
# AGENT 1: Ambiguity Inspector (Human-in-the-Loop Gate)
# ------------------------------------------------------------------------------
def inspect_for_ambiguity(user_question: str) -> AmbiguityCheckResult:
    """
    Analyzes the user's question against the schema to detect ambiguities.
    """
    system_prompt = (
        "You are an expert database architect.\n"
        "Your task: Check if the user's natural language question contains ambiguities, "
        "missing parameters, or vague business terms when compared to the schema.\n"
        f"Database Schema:\n{DB_SCHEMA}"
    )

    user_prompt = (
        f"User Question: '{user_question}'\n\n"
        "Ambiguity Guidelines:\n"
        "- 'Who are our best customers?' is AMBIGUOUS (Could mean highest total spend OR most orders).\n"
        "- 'Show recent orders' is AMBIGUOUS (Could mean last 7 days, last 30 days, or last 5 orders).\n"
        "- 'How many customers signed up in 2026?' is NOT AMBIGUOUS.\n"
        "- 'List all completed orders with amount > 1000' is NOT AMBIGUOUS."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=AmbiguityCheckResult
    )

    return completion.choices[0].message.parsed


# ------------------------------------------------------------------------------
# AGENT 2: SQL Generator
# ------------------------------------------------------------------------------
def generate_sql(user_question: str, context: str = "") -> SQLGenerationResult:
    """
    Produces the SQL query based on the question and user clarification.
    """
    system_prompt = (
        "You are an expert PostgreSQL database engineer.\n"
        f"Database Schema:\n{DB_SCHEMA}\n"
        "Rules:\n"
        "1. Write standard, compatible PostgreSQL SELECT queries only.\n"
        "2. When calculating metrics like revenue or spend, always filter by `status = 'completed'` unless requested otherwise.\n"
        "3. Only use tables and columns defined in the schema."
    )

    user_prompt = (
        f"User Question: '{user_question}'\n"
        f"Additional Clarification/Context: '{context}'\n\n"
        "Generate the appropriate SQL query to fulfill this request."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=SQLGenerationResult
    )

    return completion.choices[0].message.parsed


# ------------------------------------------------------------------------------
# AGENT 3: Self-Healing Reflection Agent
# ------------------------------------------------------------------------------
def heal_sql_query(
    original_question: str,
    failed_sql: str,
    error_diagnostic: str,
    context: str = ""
) -> SQLCorrectionResult:
    """
    Analyzes database error diagnostics and produces a corrected query.
    """
    system_prompt = (
        "You are a PostgreSQL debugging specialist.\n"
        f"Database Schema:\n{DB_SCHEMA}\n"
        "A previously generated SQL query failed when executed on PostgreSQL.\n"
        "Your task:\n"
        "1. Analyze the PostgreSQL error diagnostic message carefully.\n"
        "2. Identify what was wrong with the failed SQL (e.g., column misnaming, GROUP BY omissions, type errors).\n"
        "3. Return a corrected, executable PostgreSQL SELECT query."
    )

    user_prompt = (
        f"Original User Question: '{original_question}'\n"
        f"Clarification Context: '{context}'\n\n"
        f"Failed SQL Query:\n```sql\n{failed_sql}\n```\n\n"
        f"PostgreSQL Error Diagnostic:\n{error_diagnostic}\n\n"
        "Diagnose the failure and return the corrected query."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=SQLCorrectionResult
    )

    return completion.choices[0].message.parsed