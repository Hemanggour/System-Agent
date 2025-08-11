import sqlite3


class DatabaseManager:
    """Handles database operations"""

    @staticmethod
    def execute_sqlite_query(db_path: str, query: str) -> str:
        """Execute SQLite query"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(query)

            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]

                if results:
                    result_str = f"Query results ({len(results)} rows):\n"
                    result_str += " | ".join(columns) + "\n"
                    result_str += "-" * (len(" | ".join(columns))) + "\n"

                    for row in results[:50]:
                        result_str += " | ".join(str(cell) for cell in row) + "\n"

                    if len(results) > 50:
                        result_str += f"... and {len(results) - 50} more rows\n"

                    conn.close()
                    return result_str
                else:
                    conn.close()
                    return "Query executed successfully but returned no results"
            else:
                conn.commit()
                affected_rows = cursor.rowcount
                conn.close()
                return f"Query executed successfully. Rows affected: {affected_rows}"

        except Exception as e:
            return f"Database error: {str(e)}"
