import os
import sqlparse
import psycopg2


def is_safe_query(sql: str) -> bool:
    parsed = sqlparse.parse(sql)

    if not parsed:
        return False

    forbidden = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
    ]

    upper_sql = sql.upper()

    # Check for forbidden SQL keywords
    for word in forbidden:
        if word in upper_sql:
            return False

    # Every SQL statement must be SELECT
    for statement in parsed:
        if statement.get_type() != "SELECT":
            return False

    return True


def run_query(sql: str):
    if not is_safe_query(sql):
        return None, None, "Security Violation: Non-SELECT or mutating query rejected."

    conn = None

    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )

        conn.set_session(readonly=True)

        cur = conn.cursor()

        cur.execute(sql)

        rows = cur.fetchall()

        columns = [desc[0] for desc in cur.description]

        cur.close()

        return columns, rows, None

    except psycopg2.Error as db_err:
        sqlstate = db_err.pgcode or "UNKNOWN"
        raw_msg = db_err.pgerror.strip() if db_err.pgerror else str(db_err)

        diagnostic = f"PostgreSQL SQLSTATE [{sqlstate}]: {raw_msg}"

        return None, None, diagnostic

    except Exception as general_err:
        return None, None, f"System Error: {str(general_err)}"

    finally:
        if conn:
            conn.close()