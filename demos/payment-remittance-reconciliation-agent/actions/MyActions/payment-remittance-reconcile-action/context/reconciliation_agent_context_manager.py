from pathlib import Path
from typing import Optional, Any, Dict, Union
from datetime import datetime
import json
from models.reconciliation_models import (
    ReconciliationPhase, ReconciliationAgentInsightContext, 
    ReconciliationContext, ProcessingEvent, ValidationResults
)
from reconciliation_ledger.reconciliation_constants import DatabaseConstants
from utils.context.base_agent_context_manager import BaseAgentContextManager

class ReconciliationAgentContextManager(BaseAgentContextManager):
    """Manages context for payment reconciliation processing."""
    
    def __init__(self, 
                 document_id: str, 
                 document_name: str, 
                 customer_id: str,
                 db_path: Optional[Union[str, Path]] = None,
                 load_existing: bool = False):
        """
        Initialize ReconciliationAgentContextManager.
        
        Args:
            document_id: Document identifier
            document_name: Document name
            customer_id: Customer identifier
            db_path: Optional custom database path
            load_existing: Whether to load existing context
        """
        if not db_path:
            db_path = DatabaseConstants.get_default_reconciliation_context_db_path()
            
        db_path = str(db_path) if isinstance(db_path, Path) else db_path
        super().__init__(document_id, document_name, db_path)
        self.customer_id = customer_id
        
        if load_existing:
            self.logger.info(f"Loading existing reconciliation context for document_id: {document_id}")
            self.agent_context = self.load_context()
            if self.agent_context is None:
                self.logger.warning(f"No existing context found. Creating new reconciliation context.")
                self.agent_context = ReconciliationAgentInsightContext(
                    document_id=document_id,
                    document_name=document_name,
                    customer_id=customer_id
                )
        else:
            self.agent_context = ReconciliationAgentInsightContext(
                document_id=document_id,
                document_name=document_name,
                customer_id=customer_id
            )
            
        self.current_phase: Optional[ReconciliationPhase] = None

    def _create_tables(self, conn):
        """Create reconciliation-specific database tables."""
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS reconciliation_context (
                document_id VARCHAR PRIMARY KEY,
                customer_id VARCHAR NOT NULL,
                document_name VARCHAR NOT NULL,
                context_data JSON,
                created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
                updated_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP)
            )
            """)
            self.logger.info("Reconciliation tables created successfully")
        except Exception as e:
            self.logger.error(f"Error creating reconciliation tables: {str(e)}")
            raise

    def store_context(self):
        """Store reconciliation context to database."""
        try:
            context_json = self.agent_context.model_dump_json()
            with self.duckdb_connection() as conn:
                query = """
                INSERT INTO reconciliation_context (
                    document_id, 
                    customer_id, 
                    document_name, 
                    context_data, 
                    updated_at
                ) VALUES (?, ?, ?, ?, NOW())
                ON CONFLICT (document_id) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    document_name = EXCLUDED.document_name,
                    context_data = EXCLUDED.context_data,
                    updated_at = NOW()
                """
                conn.execute(query, [
                    self.document_id,
                    self.customer_id,
                    self.document_name,
                    context_json
                ])
            self.logger.info(f"Stored reconciliation context for document_id: {self.document_id}")
        except Exception as e:
            self.logger.error(f"Error storing reconciliation context for document_id {self.document_id}: {str(e)}")
            raise

    def load_context(self) -> Optional[ReconciliationAgentInsightContext]:
        """Load reconciliation context from database."""
        try:
            with self.duckdb_connection() as conn:
                result = conn.execute("""
                    SELECT context_data 
                    FROM reconciliation_context 
                    WHERE document_id = ? AND customer_id = ?
                """, [self.document_id, self.customer_id]).fetchone()
                
                if result:
                    context_data = json.loads(result[0])
                    return ReconciliationAgentInsightContext(**context_data)
                return None
        except Exception as e:
            self.logger.error(f"Error loading reconciliation context: {str(e)}")
            return None

    def start_phase(self, phase: ReconciliationPhase):
        """Start a reconciliation processing phase."""
        self.current_phase = phase
        context = ReconciliationContext(
            phase=phase,
            start_time=datetime.utcnow()
        )
        self.agent_context.set_phase_context(phase, context)
        self.logger.info(f"Started reconciliation phase: {phase}")

    def end_phase(self):
        """End current reconciliation phase."""
        if self.current_phase:
            context = self.agent_context.get_phase_context(self.current_phase)
            if context:
                context.end_time = datetime.utcnow()
                duration = (context.end_time - context.start_time).total_seconds()
                self.agent_context.overall_processing_time += duration
                self.logger.info(f"Ended reconciliation phase: {self.current_phase}. Duration: {self._format_duration(duration)}")

    def add_event(self, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
        """Add event to current reconciliation phase."""
        if self.current_phase:
            context = self.agent_context.get_phase_context(self.current_phase)
            if context:
                context.events.append(
                    ProcessingEvent(
                        event_type=event_type,
                        description=description,
                        details=details
                    )
                )
                self._log_event(event_type, description, details)

    def update_metrics(self, metrics_update: Dict[str, Any]):
        """Update metrics for current reconciliation phase."""
        if self.current_phase:
            context = self.agent_context.get_phase_context(self.current_phase)
            if context and context.metrics:
                for key, value in metrics_update.items():
                    setattr(context.metrics, key, value)
                self._store_metrics(metrics_update)

    def get_reconciliation_context(self) -> ReconciliationAgentInsightContext:
        """Get current reconciliation context."""
        return self.agent_context