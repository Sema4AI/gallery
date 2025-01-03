from abc import ABC, abstractmethod
import logging
import json
import traceback
from typing import Optional, Any, Dict
from contextlib import contextmanager
import duckdb
from datetime import datetime
import functools
import time

from utils.logging.ultimate_serializer import serialize_any_object_safely

class BaseAgentContextManager(ABC):
    """
    Base class for managing agent context across processing phases.
    Provides common functionality for context management and database operations.
    """
    def __init__(self, document_id: str, document_name: str, db_path: str):
        if not document_id:
            raise ValueError("document_id cannot be None or empty")
        if not document_name:
            raise ValueError("document_name cannot be None or empty")
            
        self.document_id = document_id
        self.document_name = document_name
        self.db_path = db_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database
        try:
            self.initialize_database()
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise
        
    def initialize_database(self):
        """Initialize database schema."""
        self.logger.debug("Starting database initialization")
        
        with self.duckdb_connection() as conn:
            try:
                # Create tables
                self._create_tables(conn)
                self.logger.debug("Database initialization completed successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {str(e)}")
                raise
            
    @staticmethod
    def track_method_execution(method_name):
        """
        Decorator to track the execution time of methods.

        Args:
            method_name (str): The name of the method being tracked.

        Returns:
            A wrapped function that logs its execution time as an event.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                start_time = time.time()
                result = func(self, *args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time

                if hasattr(self, 'add_event'):
                    self.add_event(
                        f"{method_name} execution",
                        f"Executed in {execution_time:.2f} seconds"
                    )

                return result
            return wrapper
        return decorator

    @contextmanager
    def duckdb_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            connection = duckdb.connect(self.db_path)
            yield connection
        except duckdb.IOException as e:
            self.logger.error(f"DuckDB connection error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
            raise
        finally:
            if connection:
                try:
                    connection.close()
                    self.logger.debug("Database connection closed successfully.")
                except Exception as e:
                    self.logger.error(f"Error closing DuckDB connection: {str(e)}")

    @abstractmethod
    def _create_tables(self, conn):
        """Create required database tables."""
        pass

    @abstractmethod
    def store_context(self):
        """Store context to database."""
        pass

    @abstractmethod
    def load_context(self):
        """Load context from database."""
        pass

    @abstractmethod
    def add_event(self, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
        """Add event to current processing phase."""
        pass

    @abstractmethod
    def update_metrics(self, metrics_update: Dict[str, Any]):
        """Update metrics for current phase."""
        pass

    @abstractmethod
    def start_phase(self, phase):
        """Start a new processing phase."""
        pass

    @abstractmethod
    def end_phase(self):
        """End current processing phase."""
        pass

    @contextmanager
    def phase_context(self, phase):
        """Context manager for processing phases."""
        self.start_phase(phase)
        try:
            yield
        finally:
            self.end_phase()

    def _log_event(self, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
        """Common logging functionality."""
        # Just log to logger, don't try to store in database
        self.logger.debug(f"Event: {event_type} - {description}")
        if details:
            self.logger.debug(f"Event details: {serialize_any_object_safely(details)}")

    def _store_metrics(self, metrics: Dict[str, Any]):
        """Common metrics storage functionality."""
        # Just log metrics, don't try to store in separate table
        self.logger.debug(f"Updating metrics: {serialize_any_object_safely(metrics)}")

    @staticmethod
    def _format_duration(duration_seconds: float) -> str:
        """Format duration in human-readable format."""
        minutes, seconds = divmod(int(duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    
    def get_agent_context(self):
        """
        Retrieve the collected context for the processed document.

        Returns:
            The context object (AgentInsightContext or ReconciliationAgentInsightContext) 
            containing all relevant information and events for the document's processing lifecycle.
        """
        return self.agent_context