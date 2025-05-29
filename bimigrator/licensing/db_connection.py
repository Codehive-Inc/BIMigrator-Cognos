"""Database connection module for the BIMigrator licensing system."""

import os
import psycopg2
from psycopg2 import pool
from typing import Optional, Dict, Any, Tuple
import logging

# Import environment loader
from bimigrator.licensing.env_loader import get_db_config, get_env_var

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager for PostgreSQL licensing database."""
    
    _connection_pool = None
    
    @classmethod
    def get_connection_params(cls) -> Dict[str, str]:
        """Get database connection parameters from environment variables.
        
        Environment variables:
            BIMIGRATOR_DB_HOST: PostgreSQL host (default: localhost)
            BIMIGRATOR_DB_PORT: PostgreSQL port (default: 5432)
            BIMIGRATOR_DB_NAME: PostgreSQL database name (default: bimigrator_db)
            BIMIGRATOR_DB_USER: PostgreSQL username (default: app_user)
            BIMIGRATOR_DB_PASSWORD: PostgreSQL password (required, no default)
            BIMIGRATOR_DB_POOL_MIN: Minimum connections in pool (default: 1)
            BIMIGRATOR_DB_POOL_MAX: Maximum connections in pool (default: 5)
            
        Returns:
            Dictionary with connection parameters
        """
        # Get database connection parameters from environment variables
        params = get_db_config()
        
        # Log connection attempt (without password)
        log_params = params.copy()
        if 'password' in log_params:
            log_params['password'] = '********'
        logger.debug(f"Database connection parameters: {log_params}")
        
        return params
    
    @classmethod
    def initialize_pool(cls) -> None:
        """Initialize the connection pool if it doesn't exist."""
        if cls._connection_pool is None:
            try:
                # Get connection parameters
                params = cls.get_connection_params()
                
                # Get pool size from environment variables
                min_connections = int(get_env_var('BIMIGRATOR_DB_POOL_MIN', '1'))
                max_connections = int(get_env_var('BIMIGRATOR_DB_POOL_MAX', '5'))
                
                # Create connection pool
                cls._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=min_connections,
                    maxconn=max_connections,
                    **params
                )
                logger.info(f"Database connection pool initialized with {min_connections}-{max_connections} connections")
            except Exception as e:
                logger.error(f"Failed to initialize database connection pool: {str(e)}")
                raise
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool.
        
        Returns:
            Database connection object
            
        Raises:
            Exception: If connection pool is not initialized or connection cannot be obtained
        """
        if cls._connection_pool is None:
            cls.initialize_pool()
            
        try:
            connection = cls._connection_pool.getconn()
            return connection
        except Exception as e:
            logger.error(f"Failed to get database connection: {str(e)}")
            raise
    
    @classmethod
    def release_connection(cls, connection):
        """Return a connection to the pool.
        
        Args:
            connection: Database connection to return to the pool
        """
        if cls._connection_pool is not None:
            cls._connection_pool.putconn(connection)
    
    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool."""
        if cls._connection_pool is not None:
            cls._connection_pool.closeall()
            cls._connection_pool = None
            logger.info("All database connections closed")


def get_connection():
    """Convenience function to get a database connection."""
    return DatabaseConnection.get_connection()


def release_connection(connection):
    """Convenience function to release a database connection."""
    DatabaseConnection.release_connection(connection)


def execute_query(query: str, params: Tuple = None, fetch_one: bool = False) -> Optional[Any]:
    """Execute a query and optionally return results.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetch_one: Whether to fetch one result or all results
        
    Returns:
        Query results or None if no results
        
    Raises:
        Exception: If query execution fails
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith(('SELECT', 'WITH')):
            if fetch_one:
                return cursor.fetchone()
            else:
                return cursor.fetchall()
        else:
            connection.commit()
            return None
    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Query execution failed: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            release_connection(connection)
