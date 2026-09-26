MAX_HEALING_ATTEMPTS = 3
def execute_with_self_healing(question: str, initial_sql: str, context: str):
  current_sql = initial_sql

  for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):
    columns, rows, error_diagnostic = run_query(current_sql)

    # Early exit on success
    if error_diagnostic is None:
      return current_sql, columns, rows

      # If an error occurred and retry attempts remain:
      if attempt < MAX_HEALING_ATTEMPTS:
        correction = heal_sql_query(
        original_question=question,
        failed_sql=current_sql,
        error_diagnostic=error_diagnostic,
        context=context
        )
        current_sql = correction.fixed_sql_query
      else:
        return current_sql, None, None
