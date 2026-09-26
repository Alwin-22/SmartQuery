from engine import inspect_for_ambiguity, generate_sql, heal_sql_query
from db import run_query

MAX_HEALING_ATTEMPTS = 3


def execute_with_self_healing(question: str, initial_sql: str, context: str):
  """
  Executes the SQL query and attempts self-healing if a database error occurs.
  """
  current_sql = initial_sql

  for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):
    print(f"\n[Attempt {attempt}/{MAX_HEALING_ATTEMPTS}] Executing SQL on PostgreSQL...")

    columns, rows, error_diagnostic = run_query(current_sql)

    # EARLY EXIT: Query succeeded 
    if error_diagnostic is None:
      print(" Execution successful!")
      return current_sql, columns, rows

      # ERROR OCCURRED
      print(" Execution Failed!")
      print(f"   Diagnostic: {error_diagnostic}")

      if attempt < MAX_HEALING_ATTEMPTS:
        print("\n  Triggering Self-Healing Reflection Agent...")
        correction = heal_sql_query(
        original_question=question,
        failed_sql=current_sql,
        error_diagnostic=error_diagnostic,
        context=context
        )
        print(f"  [AI Diagnosis]: {correction.error_analysis}")
        print(f"  [Changes Made]: {correction.changes_made}")
        print(f"  [Corrected SQL]:\n    {correction.fixed_sql_query}")

        current_sql = correction.fixed_sql_query
      else:
        print("\n Maximum retry attempts exhausted. Unable to resolve query.")
        return current_sql, None, None


        def main():
          print("======================================================")
          print("   Deterministic Agentic Text-to-SQL Engine")
          print("======================================================")

          # 1. Accept user question
          question = input("\nAsk a question about the database: ").strip()
          if not question:
            print("Empty question received. Exiting.")
            return

            # STAGE 1: Ambiguity Detection
            print("\n[Stage 1] Inspecting question for semantic ambiguity...")
            ambiguity_check = inspect_for_ambiguity(question)
            clarification_context = ""

            if ambiguity_check.is_ambiguous:
              print(f"\n[Ambiguity Detected]: {ambiguity_check.clarification_question}")
              if ambiguity_check.possible_interpretations:
                print("Suggested Interpretations:")
                for index, option in enumerate(ambiguity_check.possible_interpretations, start=1):
                  print(f"  {index}. {option}")

                  user_choice = input("\nYour clarification: ").strip()
                  clarification_context = f"User clarified: {user_choice}"
                else:
                  print(" Question is clear and unambiguous. Proceeding directly.")

                  # STAGE 2: SQL Generation
                  print("\n[Stage 2] Generating PostgreSQL SELECT query...")
                  generation = generate_sql(question, context=clarification_context)
                  print(f"Generated SQL:\n{generation.sql_query}")
                  print(f"Strategy: {generation.explanation}")

                  # STAGE 3 & 4: Execution & Self-Healing Loop
                  print("\n[Stage 3 & 4] Entering Database Execution & Reflection Pipeline...")
                  final_sql, columns, rows = execute_with_self_healing(
                  question=question,
                  initial_sql=generation.sql_query,
                  context=clarification_context
                  )

                  # STAGE 5: Render Results
                  if columns is not None and rows is not None:
                    print("\n" + "=" * 50)
                    print("QUERY RESULTS")
                    print("=" * 50)
                    print(" | ".join(columns))
                    print("-" * 50)

                    if not rows:
                      print("(Query succeeded, but returned 0 rows matching criteria)")
                    else:
                      for row in rows:
                        print(" | ".join(str(val) for val in row))
                        print("=" * 50)


                        # THIS MUST BE AT THE BOTTOM OUTSIDE ANY FUNCTION:
                        if __name__ == "__main__":
                          main()