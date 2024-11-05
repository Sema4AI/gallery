from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import logging

from utils.commons.decimal_utils import DecimalHandler


class DatabaseSetupGenerator:
    """Generates database setup files for test cases."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def generate_db_setup(
        self,
        case_name: str,
        customer_data: Dict,
        adjusted_invoices: List[Dict],
        discrepancy_config: Optional[Dict] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict:
        """
        Generate database setup using pre-adjusted invoices.
        """
        self.logger.info(f"Generating database setup for case: {case_name}")

        try:
            # Generate setup with already adjusted amounts
            db_setup = {
                "case_type": case_name,
                "customer": {
                    "customer_id": customer_data["customer_id"],
                    "customer_name": customer_data["customer_name"],
                    "account_number": customer_data["account_number"],
                },
                "facilities": self._generate_facility_records(adjusted_invoices),
                "invoices": self._generate_invoice_records(adjusted_invoices),
            }

            if discrepancy_config:
                db_setup["discrepancy_config"] = discrepancy_config

            if output_dir:
                output_path = output_dir / case_name / "db_setup.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(db_setup, f, indent=2)

            return db_setup

        except Exception as e:
            self.logger.error(f"Error generating database setup: {str(e)}")
            raise

    def _calculate_database_amounts(
        self, invoices: List[Dict], discrepancy_config: Optional[Dict]
    ) -> Tuple[DecimalHandler, Dict[str, DecimalHandler], List[Dict]]:
        """Calculate amounts with consistent decimal handling."""
        logger = self.logger
        logger.info("\n=== Calculating Database Amounts ===")

        # Initialize tracking with DecimalHandler
        facility_types = set(inv["Facility Type"] for inv in invoices)
        db_facility_totals = {
            facility_type: DecimalHandler.from_str("0")
            for facility_type in facility_types
        }

        # First calculate original totals
        original_totals = {}
        for facility_type in facility_types:
            facility_invoices = [
                inv for inv in invoices if inv["Facility Type"] == facility_type
            ]
            total = DecimalHandler.from_str("0")
            for inv in facility_invoices:
                amount = DecimalHandler.from_str(
                    str(inv["Amount Due"]).replace(",", "")
                )
                total = DecimalHandler.round_decimal(total + amount)
            original_totals[facility_type] = total

        # Get adjustments from config
        adjustments = {}
        if discrepancy_config and "adjustments" in discrepancy_config:
            for facility, adj in discrepancy_config["adjustments"].items():
                if isinstance(adj, dict):
                    adjustments[facility] = {
                        "condition": adj["condition"],
                        "factor": DecimalHandler.from_str(str(adj["factor"])),
                    }
                else:
                    adjustments[facility] = DecimalHandler.from_str(str(adj))

        # Process invoices with careful decimal handling
        adjusted_invoices = []
        total_db_amount = DecimalHandler.from_str("0")

        for invoice in invoices:
            facility_type = invoice["Facility Type"]
            base_amount = DecimalHandler.from_str(
                str(invoice["Amount Due"]).replace(",", "")
            )

            adjusted_amount = base_amount
            if facility_type in adjustments:
                adjustment = adjustments[facility_type]
                if isinstance(adjustment, dict):
                    if (
                        adjustment["condition"] == "water_service"
                        and invoice["Service Type"] == "Water"
                    ):
                        adjusted_amount = DecimalHandler.round_decimal(
                            base_amount * adjustment["factor"]
                        )
                else:
                    adjusted_amount = DecimalHandler.round_decimal(
                        base_amount * adjustment
                    )

            # Create adjusted invoice
            adjusted_invoice = invoice.copy()
            adjusted_invoice["Amount Due"] = str(adjusted_amount)
            adjusted_invoices.append(adjusted_invoice)

            # Update totals
            db_facility_totals[facility_type] = DecimalHandler.round_decimal(
                db_facility_totals[facility_type] + adjusted_amount
            )
            total_db_amount = DecimalHandler.round_decimal(
                total_db_amount + adjusted_amount
            )

            # Detailed logging
            logger.debug(
                f"Processing {invoice['Invoice Reference']}:\n"
                f"  Base: {base_amount}\n"
                f"  Adjusted: {adjusted_amount}\n"
                f"  Running facility total: {db_facility_totals[facility_type]}"
            )

        return total_db_amount, db_facility_totals, adjusted_invoices

    def _generate_facility_records(self, invoices: List[Dict]) -> List[Dict]:
        """Generate unique facility records from invoices."""
        facilities_seen = set()
        facility_records = []

        for invoice in invoices:
            facility_id = invoice["Facility ID"]
            if facility_id not in facilities_seen:
                facility_records.append(
                    {
                        "facility_id": facility_id,
                        "facility_name": facility_id,
                        "facility_type": invoice["Facility Type"],
                    }
                )
                facilities_seen.add(facility_id)

        return facility_records

    def _evaluate_condition(self, condition_str: str, invoice: Dict) -> bool:
        """Evaluate condition string against invoice."""
        if condition_str == "water_service":
            return invoice.get("Service Type") == "Water"
        return False

    def _generate_invoice_records(self, adjusted_invoices: List[Dict]) -> List[Dict]:
        """Generate invoice records from pre-adjusted invoices."""
        invoice_records = []

        for invoice in adjusted_invoices:
            # Use amounts that are already adjusted
            amount = DecimalHandler.from_str(str(invoice["Amount Due"]))
            discounts = DecimalHandler.from_str(str(invoice["Discounts"]))
            fees = DecimalHandler.from_str(str(invoice.get("Fees", 0)))

            # Extract usage data
            usage_amount = self._extract_usage_amount(invoice)
            co2_amount = self._extract_co2(invoice)

            invoice_records.append(
                {
                    "invoice_number": invoice["Invoice Reference"],
                    "invoice_amount": float(amount),
                    "discounts_applied": float(discounts),
                    "additional_charges": float(fees),
                    "facility_id": invoice["Facility ID"],
                    "facility_type": invoice["Facility Type"],
                    "service_type": invoice.get("Service Type", ""),
                    "invoice_date": self._format_date(invoice["Date of Invoice"]),
                    "usage_amount": float(usage_amount) if usage_amount else None,
                    "usage_unit": self._extract_usage_unit(invoice),
                    "co2_supplementation": float(co2_amount) if co2_amount else None,
                    "status": "PENDING",
                }
            )

        return invoice_records

    @staticmethod
    def _extract_usage_amount(invoice: Dict) -> Optional[float]:
        """Extract numeric usage amount with decimal handling."""
        usage_str = invoice.get("Usage (kWh/Gallons)", "")
        if not usage_str or usage_str == "N/A":
            return None
        try:
            amount = usage_str.split()[0].replace(",", "")
            return float(DecimalHandler.from_str(amount))
        except (IndexError, ValueError):
            return None

    @staticmethod
    def _extract_usage_unit(invoice: Dict) -> Optional[str]:
        """Extract usage unit."""
        usage_str = invoice.get("Usage (kWh/Gallons)", "")
        if not usage_str or usage_str == "N/A":
            return None
        try:
            return usage_str.split()[1]
        except IndexError:
            return None

    @staticmethod
    def _extract_co2(invoice: Dict) -> Optional[float]:
        """Extract CO2 supplementation value with decimal handling."""
        co2_str = invoice.get("CO2 Supplementation (kg)", "N/A")
        if not co2_str or co2_str == "N/A":
            return None
        try:
            return float(DecimalHandler.from_str(co2_str.replace(",", "")))
        except ValueError:
            return None

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Convert MM/DD/YYYY to YYYY-MM-DD format."""
        try:
            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            logging.error(f"Error parsing date {date_str}: {e}")
            raise

    def debug_generate_invoice_records(
        self, invoices: List[Dict], facility_type: str = "Greenhouse Complexes"
    ) -> None:
        """Debug invoice record generation for a specific facility type"""
        logger = logging.getLogger("setup_debug")

        total = DecimalHandler.from_str("0")

        for invoice in invoices:
            if invoice["Facility Type"] != facility_type:
                continue

            # Track original amount
            original = DecimalHandler.from_str(
                str(invoice["Amount Due"]).replace(",", "")
            )
            logger.info(
                f"Original amount for {invoice['Invoice Reference']}: {original}"
            )

            # Track after adjustment
            adjusted = DecimalHandler.round_decimal(
                original * DecimalHandler.from_str("1.02")
            )
            logger.info(
                f"Adjusted amount for {invoice['Invoice Reference']}: {adjusted}"
            )

            total = DecimalHandler.round_decimal(total + adjusted)

        logger.info(f"Total for {facility_type}: {total}")
        return str(total)
