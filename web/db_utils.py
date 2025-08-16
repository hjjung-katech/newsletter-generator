"""
Database utility functions with logging support
"""

import logging
import sqlite3
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def execute_query(
    cursor: sqlite3.Cursor,
    query: str,
    params: Optional[Tuple] = None,
    log_level: str = "DEBUG",
) -> sqlite3.Cursor:
    """
    Execute a database query with logging

    Args:
        cursor: SQLite cursor object
        query: SQL query string
        params: Query parameters (optional)
        log_level: Logging level for the query (DEBUG, INFO, etc.)

    Returns:
        Cursor object after execution
    """
    # Determine actual log level
    log_func = getattr(logger, log_level.lower(), logger.debug)

    # Log the query (truncate if too long)
    query_preview = query[:200] + "..." if len(query) > 200 else query
    query_preview = " ".join(query_preview.split())  # Normalize whitespace

    if params:
        log_func(f"SQL: {query_preview} | Params: {params}")
    else:
        log_func(f"SQL: {query_preview}")

    try:
        # Execute the query
        if params:
            result = cursor.execute(query, params)
        else:
            result = cursor.execute(query)

        # Log affected rows for write operations
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            logger.debug(f"Affected rows: {cursor.rowcount}")

        return result

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        logger.error(f"Failed query: {query_preview}")
        if params:
            logger.error(f"Parameters: {params}")
        raise


def execute_many(
    cursor: sqlite3.Cursor, query: str, params_list: list, log_level: str = "DEBUG"
) -> sqlite3.Cursor:
    """
    Execute multiple database queries with logging

    Args:
        cursor: SQLite cursor object
        query: SQL query string
        params_list: List of parameter tuples
        log_level: Logging level for the query

    Returns:
        Cursor object after execution
    """
    log_func = getattr(logger, log_level.lower(), logger.debug)

    query_preview = query[:200] + "..." if len(query) > 200 else query
    query_preview = " ".join(query_preview.split())

    log_func(f"SQL (batch): {query_preview} | Count: {len(params_list)}")

    try:
        result = cursor.executemany(query, params_list)
        logger.debug(f"Total affected rows: {cursor.rowcount}")
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error in batch operation: {e}")
        logger.error(f"Failed query: {query_preview}")
        raise


def log_db_operation(operation_name: str):
    """
    Decorator for logging database operations

    Usage:
        @log_db_operation("Update schedule")
        def update_schedule(schedule_id, data):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"Starting DB operation: {operation_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed DB operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed DB operation: {operation_name} - {e}")
                raise

        return wrapper

    return decorator
