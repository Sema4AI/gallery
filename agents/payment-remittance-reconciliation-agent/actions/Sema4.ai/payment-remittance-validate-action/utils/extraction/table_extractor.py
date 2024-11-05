from abc import ABC, abstractmethod
import logging
import re
import pandas as pd
from typing import List, Optional, Dict, Any

from context.validate_agent_context_manager import ValidationAgentContextManager

# Define the regex pattern for extracting table sections
TABLE_REGEX_PATTERN = r"<!--SOT-->(.*?)<!--EOT-->"


class TableStrategy(ABC):
    def __init__(self, agent_insight_context_manager: ValidationAgentContextManager):
        self.insight_context_manager = agent_insight_context_manager
        self.metrics = {}  # Base metrics dictionary, can be extended in subclasses

    @abstractmethod
    def process_table(
        self, table_content: str, page_num: str, table_num: int
    ) -> Optional[pd.DataFrame]:
        pass

    def _process_table_section(
        self, table_section: str, page_num: str, table_num: int
    ) -> Optional[pd.DataFrame]:
        lines = table_section.strip().split("\n")
        if len(lines) < 3:
            self.insight_context_manager.add_warning(
                f"Invalid table structure in Table {table_num} on page {page_num}"
            )
            return None

        headers = [h.strip() for h in lines[0].split("|") if h.strip()]
        self.insight_context_manager.add_event(
            "Table Headers", f"Table {table_num} on page {page_num} headers: {headers}"
        )

        data = []
        for line in lines[2:]:
            row = [cell.strip() for cell in line.split("|") if cell.strip()]
            if row:
                data.append(row)

        if not headers or not data:
            self.insight_context_manager.add_warning(
                f"Empty table found: Table {table_num} on page {page_num}"
            )
            return None

        if len(headers) != len(data[0]):
            self.insight_context_manager.add_warning(
                f"Mismatch in column count for table {table_num} on page {page_num}. Headers: {len(headers)}, Data: {len(data[0])}"
            )

        df = pd.DataFrame(data, columns=headers)
        df["Page"] = page_num
        df["Table"] = table_num

        # self.insight_context_manager.add_event("Table Processed", f"Processed table {table_num} from page {page_num} with {len(df)} rows and {len(df.columns)} columns")
        return df


class InvoiceDetailsStrategy(TableStrategy):
    def __init__(self, agent_insight_context_manager: ValidationAgentContextManager):
        super().__init__(agent_insight_context_manager)
        self.metrics = {
            "total_rows_processed": 0,
            "valid_rows_processed": 0,
            "total_amount_due": 0.0,
            "total_payment_sent": 0.0,
            "discrepancy_count": 0,
            "null_amount_due_count": 0,
            "null_payment_sent_count": 0,
            "max_amount_due": 0.0,
            "max_payment_sent": 0.0,
            "min_amount_due": float("inf"),
            "min_payment_sent": float("inf"),
        }

    def process_table(
        self, table_content: str, page_num: str, table_num: int
    ) -> Optional[pd.DataFrame]:
        df = self._process_table_section(table_content, page_num, table_num)
        if df is not None:
            self.metrics["total_rows_processed"] += len(df)

            for col in ["Amount Due", "Payment Sent"]:
                if col in df.columns:
                    df[col] = df[col].replace("[\$,]", "", regex=True).astype(float)
                    self.metrics[f'total_{col.lower().replace(" ", "_")}'] = df[
                        col
                    ].sum()
                    valid_values = df[col].dropna()
                    self.metrics["valid_rows_processed"] += len(valid_values)
                    self.metrics[f'null_{col.lower().replace(" ", "_")}_count'] = (
                        df[col].isna().sum()
                    )
                    if not valid_values.empty:
                        self.metrics[f'max_{col.lower().replace(" ", "_")}'] = (
                            valid_values.max()
                        )
                        self.metrics[f'min_{col.lower().replace(" ", "_")}'] = (
                            valid_values.min()
                        )

            if "Amount Due" in df.columns and "Payment Sent" in df.columns:
                self.metrics["discrepancy_count"] = (
                    df["Amount Due"] != df["Payment Sent"]
                ).sum()

            self._log_metrics(page_num, table_num)

        return df

    def _log_metrics(self, page_num: str, table_num: int):
        event_description = (
            f"Invoice Details Processing Metrics for Page {page_num}, Table {table_num}:\n"
            f"- Total rows processed: {self.metrics['total_rows_processed']}\n"
            f"- Valid rows processed: {self.metrics['valid_rows_processed']}\n"
            f"- Total Amount Due: ${self.metrics['total_amount_due']:.2f}\n"
            f"- Total Payment Sent: ${self.metrics['total_payment_sent']:.2f}\n"
            f"- Discrepancies: {self.metrics['discrepancy_count']}\n"
            f"- Null Amount Due entries: {self.metrics['null_amount_due_count']}\n"
            f"- Null Payment Sent entries: {self.metrics['null_payment_sent_count']}\n"
            f"- Max Amount Due: ${self.metrics['max_amount_due']:.2f}\n"
            f"- Max Payment Sent: ${self.metrics['max_payment_sent']:.2f}\n"
            f"- Min Amount Due: ${self.metrics['min_amount_due']:.2f}\n"
            f"- Min Payment Sent: ${self.metrics['min_payment_sent']:.2f}"
        )

        self.insight_context_manager.add_event(
            "Invoice Details Processing Metrics", event_description
        )

        # self.insight_context_manager.add_event(
        #     "Invoice Discrepancy Alert",
        #     f"Found {self.metrics['discrepancy_count']} discrepancies between Amount Due and Payment Sent"
        # )

        if (
            self.metrics["null_amount_due_count"] > 0
            or self.metrics["null_payment_sent_count"] > 0
        ):
            self.insight_context_manager.add_event(
                "Null Values in Invoice Details",
                f"Detected {self.metrics['null_amount_due_count']} null Amount Due entries and "
                f"{self.metrics['null_payment_sent_count']} null Payment Sent entries",
            )


class SummaryTableStrategy(TableStrategy):
    def __init__(self, agent_insight_context_manager: ValidationAgentContextManager):
        super().__init__(agent_insight_context_manager)
        self.metrics = {
            "total_rows_processed": 0,
            "total_subtotal_amount": 0.0,
            "facility_types": set(),
        }

    def process_table(
        self, table_content: str, page_num: str, table_num: int
    ) -> Optional[pd.DataFrame]:
        df = self._process_table_section(table_content, page_num, table_num)
        if df is not None:
            self.metrics["total_rows_processed"] += len(df)

            if "Subtotal Invoice Amount" in df.columns:
                df["Subtotal Invoice Amount"] = (
                    df["Subtotal Invoice Amount"]
                    .replace("[\$,]", "", regex=True)
                    .astype(float)
                )
                self.metrics["total_subtotal_amount"] += df[
                    "Subtotal Invoice Amount"
                ].sum()

            if "Facility Type" in df.columns:
                self.metrics["facility_types"].update(df["Facility Type"].unique())

            self._log_metrics(page_num, table_num)

        return df

    def _log_metrics(self, page_num: str, table_num: int):
        event_description = (
            f"Summary Table Processing Metrics for Page {page_num}, Table {table_num}:\n"
            f"- Total rows processed: {self.metrics['total_rows_processed']}\n"
            f"- Total Subtotal Invoice Amount: ${self.metrics['total_subtotal_amount']:.2f}\n"
            f"- Facility Types: {', '.join(self.metrics['facility_types'])}"
        )

        self.insight_context_manager.add_event(
            "Summary Table Processing Metrics", event_description
        )

        self.insight_context_manager.add_event(
            "Summary Table Processed",
            f"Processed summary table {table_num} from page {page_num}",
            {
                "page_num": page_num,
                "table_num": table_num,
                "rows": self.metrics["total_rows_processed"],
                "total_subtotal_amount": self.metrics["total_subtotal_amount"],
                "facility_types": list(self.metrics["facility_types"]),
            },
        )


class TableExtractor:
    """
    TableExtractor is responsible for extracting tabular data from the raw content of a document.

    Attributes:
        document (SourceDocument): The source document containing metadata and content.
        agent_insight_context_manager (AgentInsightContextManager): The context manager for logging events and metrics.
    """

    def __init__(
        self,
        document: Any,
        agent_insight_context_manager: ValidationAgentContextManager,
    ):
        self._logger = logging.getLogger(__name__)
        self.document = document
        self.agent_insight_context_manager = agent_insight_context_manager
        self.table_strategies: Dict[str, TableStrategy] = {
            "invoice_details": InvoiceDetailsStrategy(agent_insight_context_manager),
            "summary": SummaryTableStrategy(agent_insight_context_manager),
        }

    @ValidationAgentContextManager.track_method_execution(
        method_name="extract_tables_from_pages"
    )
    def extract_tables_from_pages(self, raw_content_pages: List[Any]) -> Dict[str, Any]:
        self.agent_insight_context_manager.add_event(
            "Table Extraction Start",
            f"Starting table extraction for document {self.document.document_name} with {len(raw_content_pages)} pages",
            {
                "document_name": self.document.document_name,
                "page_count": len(raw_content_pages),
            },
        )

        all_tables: Dict[str, List[pd.DataFrame]] = {
            "invoice_details": [],
            "summary": [],
        }
        metrics = {
            "total_raw_tables": 0,
            "total_raw_rows": 0,
            "extracted_tables": 0,
            "extracted_rows": 0,
        }
        pages_data = []

        for page_num, page in enumerate(raw_content_pages, 1):
            page_tables = self._extract_tables_from_page(page.text, str(page_num))

            page_raw_rows = sum(
                len(df) for tables in page_tables.values() for df in tables
            )
            page_raw_tables = sum(len(tables) for tables in page_tables.values())

            all_tables["invoice_details"].extend(page_tables["invoice_details"])
            all_tables["summary"].extend(page_tables["summary"])

            metrics["total_raw_rows"] += page_raw_rows
            metrics["total_raw_tables"] += page_raw_tables

            self.agent_insight_context_manager.update_tables_per_page(
                page_num, page_raw_tables
            )

            pages_data.append({"page_num": str(page_num), "tables": page_tables})

        self.agent_insight_context_manager.update_table_extraction_metrics(metrics)

        result = {
            "invoice_details": pd.DataFrame(),
            "summary": pd.DataFrame(),
            "pages_data": pages_data,
            "metrics": metrics,
        }

        for table_type in ["invoice_details", "summary"]:
            if all_tables[table_type]:
                result[table_type] = pd.concat(
                    all_tables[table_type], ignore_index=True
                )
                extracted_rows = len(result[table_type])
                extracted_tables = result[table_type]["Table"].nunique()

                result["metrics"][f"{table_type}_extracted_rows"] = extracted_rows
                result["metrics"][f"{table_type}_extracted_tables"] = extracted_tables
                result["metrics"]["extracted_rows"] += extracted_rows
                result["metrics"]["extracted_tables"] += extracted_tables

                self.agent_insight_context_manager.update_table_extraction_metrics(
                    {
                        f"{table_type}_extracted_tables": extracted_tables,
                        f"{table_type}_extracted_rows": extracted_rows,
                    }
                )

                self._check_for_mismatches(
                    table_type,
                    metrics["total_raw_rows"],
                    extracted_rows,
                    metrics["total_raw_tables"],
                    extracted_tables,
                )

        self._process_summary_tables(all_tables["summary"], result)

        self._log_extraction_results(result["metrics"])

        return result

    @ValidationAgentContextManager.track_method_execution(
        method_name="extract_tables_from_page"
    )
    def _extract_tables_from_page(
        self, page_text: str, page_num: str
    ) -> Dict[str, List[pd.DataFrame]]:
        # self.agent_insight_context_manager.add_event(
        #     "Page Processing Start",
        #     f"Starting processing for page {page_num}",
        #     {"page_number": page_num}
        # )

        table_sections = re.findall(r"<!--SOT-->(.*?)<!--EOT-->", page_text, re.DOTALL)
        self.agent_insight_context_manager.add_event(
            "Table Sections Found",
            f"Found {len(table_sections)} table sections on page {page_num}",
            {"page_number": page_num, "table_sections_count": len(table_sections)},
        )

        page_tables: Dict[str, List[pd.DataFrame]] = {
            "invoice_details": [],
            "summary": [],
        }

        for i, table_section in enumerate(table_sections, 1):
            table_type = self._determine_table_type(table_section)
            df = self.table_strategies[table_type].process_table(
                table_section, page_num, i
            )
            if df is not None:
                page_tables[table_type].append(df)

        self.agent_insight_context_manager.add_event(
            "Page Processing Complete",
            f"Processed {sum(len(tables) for tables in page_tables.values())} tables from page {page_num}",
            {
                "page_number": page_num,
                "processed_tables_count": sum(
                    len(tables) for tables in page_tables.values()
                ),
            },
        )
        return page_tables

    def _determine_table_type(self, table_content: str) -> str:
        return (
            "summary"
            if "Subtotal Invoice Amount" in table_content
            else "invoice_details"
        )

    def _check_for_mismatches(
        self,
        table_type: str,
        total_raw_rows: int,
        extracted_rows: int,
        total_raw_tables: int,
        extracted_tables: int,
    ):
        pass
        # if extracted_rows != total_raw_rows:
        #     self.agent_insight_context_manager.add_event(
        #         f"{table_type.capitalize()} Row Count Mismatch",
        #         f"{table_type.capitalize()} row count mismatch detected. Raw rows: {total_raw_rows}, Extracted rows: {extracted_rows}",
        #         {"raw_rows": total_raw_rows, "extracted_rows": extracted_rows}
        #     )
        # if extracted_tables != total_raw_tables:
        #     self.agent_insight_context_manager.add_event(
        #         f"{table_type.capitalize()} Table Count Mismatch",
        #         f"{table_type.capitalize()} table count mismatch detected. Raw tables: {total_raw_tables}, Extracted tables: {extracted_tables}",
        #         {"raw_tables": total_raw_tables, "extracted_tables": extracted_tables}
        #     )

    def _process_summary_tables(
        self, summary_tables: List[pd.DataFrame], result: Dict[str, Any]
    ):
        if summary_tables:
            combined_summary = pd.concat(summary_tables, ignore_index=True)
            result["summary"] = combined_summary

            summary_metrics = {
                "total_rows": len(combined_summary),
                "total_subtotal": combined_summary["Subtotal Invoice Amount"].sum()
                if "Subtotal Invoice Amount" in combined_summary.columns
                else 0,
                "unique_facility_types": combined_summary["Facility Type"].nunique()
                if "Facility Type" in combined_summary.columns
                else 0,
            }

            self.agent_insight_context_manager.add_event(
                "Combined Summary Table",
                f"Combined {len(summary_tables)} summary tables",
                summary_metrics,
            )

            result["metrics"].update(
                {
                    "combined_summary_rows": summary_metrics["total_rows"],
                    "combined_summary_total": summary_metrics["total_subtotal"],
                    "combined_summary_facility_types": summary_metrics[
                        "unique_facility_types"
                    ],
                }
            )
        else:
            result["summary"] = pd.DataFrame()

    def _log_extraction_results(self, metrics: Dict[str, int]):
        if metrics["extracted_rows"] > 0:
            self.agent_insight_context_manager.add_event(
                "Table Extraction Complete",
                f"Successfully extracted {metrics['extracted_rows']} rows from {metrics['extracted_tables']} tables",
                {
                    "extracted_rows": metrics["extracted_rows"],
                    "extracted_tables": metrics["extracted_tables"],
                },
            )
        else:
            self.agent_insight_context_manager.add_event(
                "No Tables Extracted",
                "No tables were extracted from the document",
                {"document_name": self.document.document_name},
            )
