from pathlib import Path
from typing import Optional, Any, Dict, Union
from datetime import datetime
import json
from models.validate_models import (
    ProcessingPhase,
    ProcessingEvent,
    ProcessingSummary,
    AgentInsightContext,
    ProcessingContext,
    ValidationResults,
    TableExtractionMetrics,
)
from utils.context.base_agent_context_manager import BaseAgentContextManager
from validation.validation_constants import DatabaseConstants


class ValidationAgentContextManager(BaseAgentContextManager):
    """Manages context for document validation processing."""

    def __init__(
        self,
        document_id: str,
        document_name: str,
        db_path: Optional[Union[str, Path]] = None,
        load_existing: bool = False,
    ):
        """
        Initialize ValidationAgentContextManager.

        Args:
            document_id: Document identifier
            document_name: Document name
            db_path: Optional custom database path
            load_existing: Whether to load existing context
        """
        if not db_path:
            db_path = DatabaseConstants.get_default_validation_db_path()

        db_path = str(db_path) if isinstance(db_path, Path) else db_path
        super().__init__(document_id, document_name, db_path)

        if load_existing:
            self.logger.info(
                f"Loading existing validation context for document_id: {document_id}"
            )
            self.agent_context = self.load_context()
            if self.agent_context is None:
                self.logger.warning(
                    "No existing context found. Creating new validation context."
                )
                self.agent_context = AgentInsightContext(
                    document_id=document_id, document_name=document_name
                )
        else:
            self.agent_context = AgentInsightContext(
                document_id=document_id, document_name=document_name
            )

        self.current_phase: Optional[ProcessingPhase] = None

    def _create_tables(self, conn):
        """Create validation-specific database tables."""
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_context (
                document_id VARCHAR PRIMARY KEY,
                document_name VARCHAR NOT NULL,
                context_data JSON,
                created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
                updated_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP)
            )
            """)
            self.logger.info("Validation tables created successfully")
        except Exception as e:
            self.logger.error(f"Error creating validation tables: {str(e)}")
            raise

    def store_context(self):
        """Store validation context to database."""
        try:
            context_json = self.agent_context.model_dump_json()
            with self.duckdb_connection() as conn:
                # Note: Using NOW() for timestamp in DuckDB
                query = """
                INSERT INTO validation_context (
                    document_id, document_name, context_data, updated_at
                ) VALUES (?, ?, ?, NOW())
                ON CONFLICT (document_id) DO UPDATE SET
                    document_name = EXCLUDED.document_name,
                    context_data = EXCLUDED.context_data,
                    updated_at = NOW()
                """
                conn.execute(
                    query, [self.document_id, self.document_name, context_json]
                )
            self.logger.info(
                f"Stored validation context for document_id: {self.document_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Error storing validation context for document_id {self.document_id}: {str(e)}"
            )
            raise

    def load_context(self) -> Optional[AgentInsightContext]:
        """Load validation context from database."""
        try:
            with self.duckdb_connection() as conn:
                result = conn.execute(
                    """
                    SELECT context_data 
                    FROM validation_context 
                    WHERE document_id = ?
                """,
                    [self.document_id],
                ).fetchone()

                if result:
                    context_data = json.loads(result[0])
                    return AgentInsightContext(**context_data)
                return None
        except Exception as e:
            self.logger.error(f"Error loading validation context: {str(e)}")
            return None

    def start_phase(self, phase: ProcessingPhase):
        """Start a validation processing phase."""
        self.current_phase = phase
        context = ProcessingContext(
            document_id=self.agent_context.document_id,
            document_name=self.agent_context.document_name,
            processing_phase=phase,
            summary=ProcessingSummary(phase=phase, start_time=datetime.utcnow()),
        )
        setattr(self.agent_context, f"{phase.value.lower()}_context", context)
        self.logger.info(f"Started validation phase: {phase}")

    def end_phase(self):
        """End current validation phase."""
        if self.current_phase:
            context_name = f"{self.current_phase.value.lower()}_context"
            context = getattr(self.agent_context, context_name, None)
            if context and context.summary:
                context.summary.end_time = datetime.utcnow()
                duration = (
                    context.summary.end_time - context.summary.start_time
                ).total_seconds()
                self.agent_context.overall_processing_time += duration
                self.logger.info(
                    f"Ended validation phase: {self.current_phase}. Duration: {self._format_duration(duration)}"
                )

    def add_event(
        self,
        event_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Add event to current validation phase."""
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context and context.summary:
                context.summary.processing_events.append(
                    ProcessingEvent(
                        event_type=event_type, description=description, details=details
                    )
                )
                self._log_event(event_type, description, details)

    def update_metrics(self, metrics_update: Dict[str, Any]):
        """Update metrics for current validation phase."""
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context and context.summary and context.summary.data_metrics:
                for key, value in metrics_update.items():
                    setattr(context.summary.data_metrics, key, value)
                self._store_metrics(metrics_update)

    def get_validation_context(self) -> AgentInsightContext:
        """Get current validation context."""
        return self.agent_context

    # Validation-specific methods
    def add_validation_results(self, validation_results: ValidationResults):
        """Add validation results to current phase."""
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context:
                context.validation_results = validation_results

    def get_table_extraction_metrics(self) -> TableExtractionMetrics:
        """Get table extraction metrics for current phase."""
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context and context.summary:
                return (
                    context.summary.table_extraction_metrics or TableExtractionMetrics()
                )
        return TableExtractionMetrics()

    def add_document_type_config(self, doc_type_config: Dict[str, Any]):
        """
        Add document type configuration.

        Args:
            doc_type_config (Dict[str, Any]): The document type configuration to add.
        """
        if hasattr(self.agent_context, "extraction_context"):
            self.agent_context.extraction_context.configuration_used[
                "document_type"
            ] = doc_type_config
        else:
            self.logger.warning("No extraction_context found in agent_context")

    def add_document_format_config(self, doc_format_config: Dict[str, Any]):
        """
        Add document format configuration.


        Args:
            doc_format_config (Dict[str, Any]): The document format configuration to add.
        """
        if hasattr(self.agent_context, "extraction_context"):
            self.agent_context.extraction_context.configuration_used[
                "document_format"
            ] = doc_format_config
        else:
            self.logger.warning("No extraction_context found in agent_context")

    def add_additional_context(self, key: str, value: Any):
        """
        Add additional context to the current phase.

        Args:
            key (str): The context key.
            value (Any): The context value.
        """
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context:
                if not hasattr(context, "additional_context"):
                    context.additional_context = {}
                context.additional_context[key] = value
            else:
                self.logger.warning(
                    f"Unable to add additional context: {self.current_phase.value.lower()}_context not found"
                )
        else:
            self.logger.warning(
                "Unable to add additional context: No current phase set"
            )

    def add_context(self, key: str, value: Any):
        """
        Add context to the current phase.

        Args:
            key (str): The context key.
            value (Any): The context value.
        """
        self.add_additional_context(key, value)

    def get_context(self, key: str, default: Any = None):
        """
        Retrieve context from the current phase.

        Args:
            key (str): The context key.
            default (Any): The default value if the key is not found.

        Returns:
            Any: The context value or the default value if the key is not found.
        """
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context and hasattr(context, "additional_context"):
                return context.additional_context.get(key, default)
        return default

    def update_tables_per_page(self, page_num: int, table_count: int):
        """Update the tables per page metric."""
        metrics = self.get_table_extraction_metrics()
        metrics.tables_per_page[page_num] = table_count
        self.update_table_extraction_metrics(
            {"tables_per_page": metrics.tables_per_page}
        )

    def add_empty_column_dropped(self, column_name: str):
        """Add a column name to the empty columns dropped metric."""
        metrics = self.get_table_extraction_metrics()
        metrics.empty_columns_dropped.append(column_name)
        self.update_table_extraction_metrics(
            {"empty_columns_dropped": metrics.empty_columns_dropped}
        )

    def rename_column(self, original_name: str, new_name: str):
        """Update the columns renamed metric."""
        metrics = self.get_table_extraction_metrics()
        metrics.columns_renamed[original_name] = new_name
        self.update_table_extraction_metrics(
            {"columns_renamed": metrics.columns_renamed}
        )

    def update_table_extraction_metrics(self, metrics_update: Dict[str, Any]):
        """Update the table extraction metrics."""
        if self.current_phase:
            context = getattr(
                self.agent_context, f"{self.current_phase.value.lower()}_context"
            )
            if context and context.summary and context.summary.table_extraction_metrics:
                for key, value in metrics_update.items():
                    setattr(context.summary.table_extraction_metrics, key, value)
            else:
                self.logger.warning(
                    f"Unable to update table extraction metrics: {self.current_phase.value.lower()}_context not found or incomplete"
                )
        else:
            self.logger.warning(
                "Unable to update table extraction metrics: No current phase set"
            )
