import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DatabaseManager:
    """Database connection and management class"""
    
    def __init__(self):
        self.db_path = Path(settings.DATABASE_PATH)
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_db_directory()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if necessary"""
        if self.connection is None:
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Set journal mode for better performance
            self.connection.execute("PRAGMA journal_mode = WAL")
            # Set synchronous mode
            self.connection.execute("PRAGMA synchronous = NORMAL")
            
            logger.info(f"Database connection established: {self.db_path}")
        
        return self.connection
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def execute_query(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            logger.debug(f"Query executed: {query[:50]}... - {affected_rows} rows affected")
            return affected_rows
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            conn.rollback()
            raise
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from SELECT query"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error fetching one row: {e}")
            raise
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from SELECT query"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        except Exception as e:
            logger.error(f"Error fetching all rows: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.fetch_one(query, (table_name,))
        return result is not None
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "default_value": col[4],
                    "pk": bool(col[5])
                }
                for col in columns
            ]
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            raise
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table"""
        try:
            result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
            return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Error getting count for table {table_name}: {e}")
            return 0

# Global database manager instance
db_manager = DatabaseManager()

# Async wrapper functions for compatibility
async def init_db():
    """Initialize database connection - assumes database is already provided"""
    try:
        # Check if database file exists
        if not db_manager.db_path.exists():
            logger.error(f"Database file not found: {db_manager.db_path}")
            raise FileNotFoundError(f"Database file not found: {db_manager.db_path}")
        
        # Test connection
        await check_db_connection()
        logger.info("Database connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        # Try to execute a simple query
        result = db_manager.fetch_one("SELECT 1 as test")
        return result is not None and result.get("test") == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

# Utility functions for external use
def execute_query(query: str, params: tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE query"""
    return db_manager.execute_query(query, params)

def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute INSERT query and return the ID of the inserted row"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        inserted_id = cursor.lastrowid
        cursor.close()
        logger.debug(f"Insert query executed: {query[:50]}... - ID: {inserted_id}")
        return inserted_id
    except Exception as e:
        logger.error(f"Error executing insert query: {e}")
        conn.rollback()
        raise

def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch single row from SELECT query"""
    return db_manager.fetch_one(query, params)

def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all rows from SELECT query"""
    return db_manager.fetch_all(query, params)

def get_table_count(table_name: str) -> int:
    """Get row count for a table"""
    return db_manager.get_table_count(table_name)

# Cleanup function
def cleanup():
    """Cleanup database connections"""
    db_manager.close_connection()
