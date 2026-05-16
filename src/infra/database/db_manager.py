import sqlite3
import os
from typing import List, Dict, Any, Optional
from src.core.utils.logger import system_logger

class DatabaseManager:
    """
    Handles SQLite connection with WAL mode and basic execution.
    Targeted for dev-first, production-ready later transition.
    """
    def __init__(self, db_path: str = "trader_suit.db", schema_path: str = "src/infra/database/schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        self._initialize_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for concurrent read/write
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _initialize_db(self):
        """Initializes schema if not present."""
        if not os.path.exists(self.schema_path):
            system_logger.error(f"Schema file not found at {self.schema_path}")
            return
            
        with open(self.schema_path, 'r') as f:
            schema_sql = f.read()
            
        conn = self._get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            system_logger.info("Database initialized successfully.")
        except Exception as e:
            system_logger.error(f"Failed to initialize database: {e}")
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> int:
        """Executes a write query and returns lastrowid."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            system_logger.error(f"Query execution failed: {e}\nQuery: {query}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_batch(self, query: str, params_list: List[tuple]):
        """Executes multiple insert/updates in one transaction."""
        conn = self._get_connection()
        try:
            conn.executemany(query, params_list)
            conn.commit()
        except Exception as e:
            system_logger.error(f"Batch execution failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

# Global singleton or instance
db_manager = DatabaseManager()
