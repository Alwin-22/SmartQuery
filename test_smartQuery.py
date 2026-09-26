import pytest
from unittest.mock import patch, MagicMock

# Import the contracts and functions from your project files
from models import AmbiguityCheckResult, SQLCorrectionResult
from db import is_safe_query, run_query
from main import execute_with_self_healing


# ==============================================================================
# 1. UNIT TESTS: Security Filter (db.is_safe_query)
# ==============================================================================
class TestSecurityGuards:
  def test_allows_valid_select_query(self):
    """Verifies that a standard SELECT statement passes validation."""
    query = "SELECT id, name FROM customers WHERE id = 1;"
    assert is_safe_query(query) is True

    def test_allows_valid_join_and_aggregate_query(self):
      """Verifies that complex, analytical SELECT queries pass validation."""
      query = """
      SELECT c.name, SUM(o.total_amount) AS total
      FROM customers c
      JOIN orders o ON c.id = o.customer_id
      WHERE o.status = 'completed'
      GROUP BY c.name;
      """
      assert is_safe_query(query) is True

      @pytest.mark.parametrize("malicious_query", [
      "DROP TABLE customers;",
      "DELETE FROM orders WHERE id = 5;",
      "UPDATE customers SET name = 'Hacked';",
      "INSERT INTO customers (name, email) VALUES ('Mal', 'mal@test.com');",
      "TRUNCATE TABLE orders;",
      "ALTER TABLE customers DROP COLUMN email;",
      "SELECT * FROM customers; DROP TABLE orders;"  # Stacked query attack
      ])
      def test_blocks_destructive_and_mutating_queries(self, malicious_query):
        """Ensures that any data-modifying or destructive query is rejected."""
        assert is_safe_query(malicious_query) is False


        # ==============================================================================
        # 2. UNIT TESTS: Database Mocking & Error Capture (db.run_query)
        # ==============================================================================
        class TestDatabaseRunnerMocked:
          @patch("db.psycopg2.connect")
          def test_successful_query_execution(self, mock_connect):
            """Simulates a successful query returning two customer rows."""
            # 1. Create fake connection and cursor objects
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur

            # 2. Define what the fake database returns
            mock_cur.description = [("id",), ("name",)]
            mock_cur.fetchall.return_value = [(1, "Rahul Sharma"), (2, "Priya Patel")]

            # 3. Call the actual function
            cols, rows, error = run_query("SELECT id, name FROM customers;")

            # 4. Verify outcomes
            assert error is None
            assert cols == ["id", "name"]
            assert len(rows) == 2
            mock_conn.set_session.assert_called_once_with(readonly=True)

            @patch("db.psycopg2.connect")
            def test_captures_postgres_sqlstate_error(self, mock_connect):
              """Simulates PostgreSQL throwing an undefined column error (SQLSTATE 42703)."""
              import psycopg2

              # 1. Set up the fake database to raise an error
              mock_conn = MagicMock()
              mock_cur = MagicMock()
              mock_connect.return_value = mock_conn
              mock_conn.cursor.return_value = mock_cur

              mock_db_error = psycopg2.DatabaseError("column 'user_email' does not exist")
              mock_db_error.pgcode = "42703"
              mock_db_error.pgerror = (
              "ERROR: column 'user_email' does not exist\n"
              "LINE 1: SELECT user_email FROM customers;"
              )
              mock_cur.execute.side_effect = mock_db_error

              # 2. Run the function
              cols, rows, error = run_query("SELECT user_email FROM customers;")

              # 3. Verify the error diagnostic string was assembled properly
              assert cols is None
              assert rows is None
              assert error is not None
              assert "SQLSTATE [42703]" in error
              assert "column 'user_email' does not exist" in error


              # ==============================================================================
              # 3. UNIT TESTS: Ambiguity Interception (engine.inspect_for_ambiguity)
              # ==============================================================================
              class TestAmbiguityEngine:
                @patch("engine.client.beta.chat.completions.parse")
                def test_detects_ambiguous_question(self, mock_parse):
                  """Verifies the system detects ambiguous questions and extracts choices."""
                  from engine import inspect_for_ambiguity

                  # 1. Create a fake Pydantic response from the AI
                  mock_parsed_result = AmbiguityCheckResult(
                  is_ambiguous=True,
                  clarification_question="How would you like to define 'best customers'?",
                  possible_interpretations=[
                  "By total completed order spend",
                  "By lifetime order count"
                  ]
                  )
                  mock_response = MagicMock()
                  mock_response.choices = [MagicMock(message=MagicMock(parsed=mock_parsed_result))]
                  mock_parse.return_value = mock_response

                  # 2. Run the ambiguity inspector
                  result = inspect_for_ambiguity("Who are our best customers?")

                  # 3. Verify the result
                  assert result.is_ambiguous is True
                  assert "best customers" in result.clarification_question
                  assert len(result.possible_interpretations) == 2

                  @patch("engine.client.beta.chat.completions.parse")
                  def test_passes_unambiguous_question(self, mock_parse):
                    """Verifies that clear questions pass through without interruption."""
                    from engine import inspect_for_ambiguity

                    mock_parsed_result = AmbiguityCheckResult(
                    is_ambiguous=False,
                    clarification_question=None,
                    possible_interpretations=None
                    )
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock(message=MagicMock(parsed=mock_parsed_result))]
                    mock_parse.return_value = mock_response

                    result = inspect_for_ambiguity("List all orders placed in 2026")

                    assert result.is_ambiguous is False
                    assert result.clarification_question is None


                    # ==============================================================================
                    # 4. INTEGRATION TESTS: Self-Healing Loop (main.execute_with_self_healing)
                    # ==============================================================================
                    class TestSelfHealingLoop:
                      @patch("main.heal_sql_query")
                      @patch("main.run_query")
                      def test_recovers_after_one_database_error(self, mock_run_query, mock_heal_sql):
                        """
                        Flow under test:
                        1. Attempt 1 fails with an invalid column name.
                        2. Reflection agent proposes a fix.
                        3. Attempt 2 executes the fixed query and succeeds.
                        """
                        initial_broken_sql = "SELECT user_name FROM customers;"
                        healed_sql = "SELECT name FROM customers;"
                        error_msg = "PostgreSQL SQLSTATE [42703]: ERROR: column 'user_name' does not exist"

                        # Mock query execution: 1st call fails, 2nd call succeeds
                        mock_run_query.side_effect = [
                        (None, None, error_msg),
                        (["name"], [("Rahul Sharma",), ("Priya Patel",)], None)
                        ]

                        # Mock the healing agent response
                        mock_heal_sql.return_value = SQLCorrectionResult(
                        error_analysis="The column 'user_name' was used, but the schema defines it as 'name'.",
                        fixed_sql_query=healed_sql,
                        changes_made="Changed 'user_name' to 'name'."
                        )

                        final_sql, cols, rows = execute_with_self_healing(
                        question="Show all customer names",
                        initial_sql=initial_broken_sql,
                        context=""
                        )

                        # Assertions
                        assert final_sql == healed_sql
                        assert cols == ["name"]
                        assert len(rows) == 2
                        assert mock_run_query.call_count == 2
                        mock_heal_sql.assert_called_once_with(
                        original_question="Show all customer names",
                        failed_sql=initial_broken_sql,
                        error_diagnostic=error_msg,
                        context=""
                        )

                        @patch("main.heal_sql_query")
                        @patch("main.run_query")
                        def test_exhausts_retries_when_unrecoverable(self, mock_run_query, mock_heal_sql):
                          """Ensures that repeated failures stop at MAX_HEALING_ATTEMPTS (3 attempts)."""
                          persistent_error = "PostgreSQL SQLSTATE [42P01]: ERROR: relation 'non_existent_table' does not exist"

                          # Always return an error
                          mock_run_query.return_value = (None, None, persistent_error)

                          mock_heal_sql.return_value = SQLCorrectionResult(
                          error_analysis="Attempted to query missing table.",
                          fixed_sql_query="SELECT * FROM non_existent_table;",
                          changes_made="None"
                          )

                          final_sql, cols, rows = execute_with_self_healing(
                          question="Invalid request",
                          initial_sql="SELECT * FROM non_existent_table;",
                          context=""
                          )

                          # Confirm clean failure without unhandled exceptions
                          assert cols is None
                          assert rows is None
                          assert mock_run_query.call_count == 3
                          assert mock_heal_sql.call_count == 2