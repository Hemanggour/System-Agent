import sqlite3
from typing import List

from langchain.tools import StructuredTool


class DatabaseManager:
    """Handles database operations"""

    @staticmethod
    def execute_sqlite_query(db_path: str, query: str) -> str:
        """Execute a query on an SQLite database.

        Args:
            db_path: Path to the SQLite database file
            query: SQL query to execute

        Returns:
            str: Query results or error message
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if it's a SELECT query
            is_select = query.strip().upper().startswith("SELECT")

            if is_select:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                if not rows:
                    return "Query returned no results."

                # Format results as a table
                result = " | ".join(columns) + "\n"
                result += "-" * len(result) * 2 + "\n"

                for row in rows:
                    result += " | ".join(str(value) for value in row) + "\n"

                return result
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                cursor.execute(query)
                conn.commit()
                return f"Query executed successfully. Rows affected: {cursor.rowcount}"

        except sqlite3.Error as e:
            return f"SQLite error: {str(e)}"
        except Exception as e:
            return f"Error executing query: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for database operations."""
        return [
            StructuredTool(
                name="execute_sqlite_query",
                func=self.execute_sqlite_query,
                description="""Execute a query on an SQLite database.

                Args:
                    db_path (str): Path to the SQLite database file
                    query (str): SQL query to execute
                JSON: {"db_path": "database.db", "query": "SELECT * FROM users WHERE id = 1"}

                Returns:
                - For SELECT queries: Query results with column headers
                - For other queries: Number of affected rows""",
                args_schema={
                    "db_path": {
                        "type": "string",
                        "description": "Path to the SQLite database file",
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute",
                    },
                },
            )
        ]
