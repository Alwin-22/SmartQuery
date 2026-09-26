from pydantic import BaseModel, Field
from typing import Optional, List

# SCHEMA 1: Ambiguity Evaluation Output
class AmbiguityCheckResult(BaseModel):
    is_ambiguous: bool = Field(
        description="True if the question contains ambiguous terms, vague metrics, or multiple meanings. False if clear."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="The follow-up question asking the user to choose between different interpretations."
    )
    possible_interpretations: Optional[List[str]] = Field(
        default=None,
        description="A list of 2-3 specific choices (e.g., ['By total spend', 'By order volume'])."
    )

# SCHEMA 2: Initial SQL Generation Output
class SQLGenerationResult(BaseModel):
    sql_query: str = Field(
        description="The PostgreSQL SELECT statement created to fulfill the user request."
    )
    explanation: str = Field(
        description="A concise summary of how the query resolves the user request."
    )

# SCHEMA 3: Self-Healing & Error Resolution Output
class SQLCorrectionResult(BaseModel):
    error_analysis: str = Field(
        description="Technical explanation of why the database rejected the previous SQL query."
    )
    fixed_sql_query: str = Field(
        description="The corrected read-only PostgreSQL SELECT query."
    )
    changes_made: str = Field(
        description="A summary of the syntactic or relational changes applied."
    )