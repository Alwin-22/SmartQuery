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
def inspect_for_ambiguity(user_question: str) -> AmbiguityCheckResult:
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
  def generate_sql(user_question: str, context: str = "") -> SQLGenerationResult:
    system_prompt = (
    "You are an expert PostgreSQL database engineer.\n"
    f"Database Schema:\n{DB_SCHEMA}\n"
    "Rules:\n"
    "1. Write standard, compatible PostgreSQL SELECT queries only.\n"
    "2. When calculating metrics like revenue or spend, always filter by `status = 'completed'` unless requested otherwise.\n"
    "3. Only use tables and columns defined in the schema."
    )
    def heal_sql_query(
    original_question: str,
    failed_sql: str,
    error_diagnostic: str,
    context: str = "") -> SQLCorrectionResult: