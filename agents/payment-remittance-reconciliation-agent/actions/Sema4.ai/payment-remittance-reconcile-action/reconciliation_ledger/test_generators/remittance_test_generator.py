from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import random
import json
from reconciliation_ledger.reconciliation_constants import BASE_ACTIONS_DIR
from utils.commons.decimal_utils import DecimalHandler
from utils.commons.path_utils import get_full_path
from utils.logging.reconcile_logging_module import configure_logging
from reconciliation_ledger.db.db_setup_generator import DatabaseSetupGenerator

class RemittanceTestGenerator:
    """
    Generates test remittance documents with controlled discrepancies for testing
    the reconciliation agent.
    """
    
    DEFAULT_DIR_FOR_TEST_CASES = f"{BASE_ACTIONS_DIR}/reconciliation_ledger/test_generators/test_cases"
    
    # Default configurations
    DEFAULT_FACILITY_TYPES = [
        "Greenhouse Complexes",
        "Vertical Farming Units", 
        "Hydroponics Systems",
        "Sustainable Energy Solutions",
        "AgriTech Services"
    ]
    DEFAULT_INVOICE_COUNTS = {
        "Greenhouse Complexes": 6,
        "Vertical Farming Units": 5,
        "Hydroponics Systems": 4,
        "Sustainable Energy Solutions": 6,
        "AgriTech Services": 6
    }
    DEFAULT_RECONCILIATION_THRESHOLD = '0.01'
    
    def __init__(self, config: Optional[Dict] = None, output_dir: Optional[Path] = None):
        self.logger = configure_logging(__name__)
        self.config = config or {}
        self.base_date = datetime(2024, 9, 1)
        
        # Initialize facility types first
        self.facility_types = self.config.get('facility_types', self.DEFAULT_FACILITY_TYPES)
        
        # Get invoice counts from config or create from facility types
        if 'invoice_counts' in self.config:
            self.invoice_counts = self.config['invoice_counts']
        else:
            # Create invoice counts based on facility types
            self.invoice_counts = {
                facility: self.DEFAULT_INVOICE_COUNTS.get(facility, 6)
                for facility in self.facility_types
            }
        
        # Get reconciliation threshold using DecimalHandler
        self.reconciliation_threshold = DecimalHandler.from_str(
            str(self.config.get('threshold', self.DEFAULT_RECONCILIATION_THRESHOLD))
        )
        
        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            default_path = get_full_path(self.DEFAULT_DIR_FOR_TEST_CASES)
            self.output_dir = Path(default_path)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_setup_generator = DatabaseSetupGenerator()

    def _generate_invoice_base(self, 
                             invoice_num: str, 
                             amount: float,
                             facility_id: str,
                             facility_type: str,
                             service_type: str,
                             date_offset: int) -> Dict:
        """Generate base invoice structure using Wire Transfer mappings."""
        invoice_date = self.base_date + timedelta(days=date_offset)
        
        # Convert amount using DecimalHandler
        amount_decimal = DecimalHandler.from_float(amount)
        discount = DecimalHandler.calc_percentage(
            amount_decimal, 
            DecimalHandler.from_str('0.01')
        )
        
        return {
            "Invoice Reference": invoice_num,
            "Amount Due": float(amount_decimal),
            "Payment Sent": float(DecimalHandler.round_decimal(amount_decimal - discount)),
            "Discounts": float(discount),
            "Fees": 0,
            "Date of Invoice": invoice_date.strftime("%m/%d/%Y"),
            "Facility ID": facility_id,
            "Facility Type": facility_type,
            "Service Type": service_type,
            "Usage (kWh/Gallons)": None,
            "CO2 Supplementation (kg)": None
        }

    def _generate_base_invoices(self, rounding_adjustment: bool = False) -> Tuple[List[Dict], Dict[str, DecimalHandler]]:
        """Generate base invoice data structure using configured counts."""
        invoices = []
        facility_subtotals = {facility: DecimalHandler.from_str('0') for facility in self.facility_types}
        
        for facility_type in self.facility_types:
            count = self.invoice_counts[facility_type]
            if facility_type == "Greenhouse Complexes":
                new_invoices = self._generate_greenhouse_invoices(count // 2, rounding_adjustment)
            elif facility_type == "Vertical Farming Units":
                new_invoices = self._generate_vertical_farming_invoices(count // 2, rounding_adjustment)
            elif facility_type == "Hydroponics Systems":
                new_invoices = self._generate_hydroponics_invoices(count // 2, rounding_adjustment)
            elif facility_type == "Sustainable Energy Solutions":
                new_invoices = self._generate_sustainable_energy_invoices(count, rounding_adjustment)
            else:  # AgriTech Services
                new_invoices = self._generate_agritech_invoices(count, rounding_adjustment)
            
            invoices.extend(new_invoices)
            subtotal = sum(
                DecimalHandler.from_str(str(inv['Amount Due'])) 
                for inv in new_invoices
            )
            facility_subtotals[facility_type] = DecimalHandler.round_decimal(subtotal)
        
        return invoices, facility_subtotals

    def _generate_facility_service_invoice(self, 
                                        base_amount_range: Tuple[float, float],
                                        rounding_adjustment: bool,
                                        multiplier: float = 1.0) -> DecimalHandler:
        """Generate service invoice amount with consistent decimal handling."""
        base = DecimalHandler.from_float(random.uniform(*base_amount_range))
        amount = DecimalHandler.round_decimal(base * DecimalHandler.from_str(str(multiplier)))
        
        if rounding_adjustment:
            amount = DecimalHandler.round_decimal(
                amount * DecimalHandler.from_str('1.0005')
            )
        
        return amount

    def _generate_greenhouse_invoices(self, facility_count: int, rounding_adjustment: bool = False) -> List[Dict]:
        """Generate Greenhouse Complex invoices with consistent decimal handling."""
        invoices = []
        for i in range(1, facility_count + 1):
            facility_id = f"FAA-GH-{i:03d}"
            
            # Electricity invoice
            electricity_amount = self._generate_facility_service_invoice(
                (75000, 95000), rounding_adjustment
            )
            
            electricity_invoice = self._generate_invoice_base(
                f"INV-GH-{5000+i*2-1:06d}",
                float(electricity_amount),
                facility_id,
                "Greenhouse Complexes",
                "Electricity",
                (i-1)*4
            )
            electricity_invoice["Usage (kWh/Gallons)"] = f"{random.randint(600000, 800000)} kWh"
            electricity_invoice["CO2 Supplementation (kg)"] = str(random.randint(3000, 4000))
            
            # Water invoice
            water_amount = self._generate_facility_service_invoice(
                (35000, 55000), rounding_adjustment
            )
            
            water_invoice = self._generate_invoice_base(
                f"INV-GH-{5000+i*2:06d}",
                float(water_amount),
                facility_id,
                "Greenhouse Complexes",
                "Water",
                (i-1)*4 + 2
            )
            water_invoice["Usage (kWh/Gallons)"] = f"{random.randint(280000, 480000)} Gallons"
            water_invoice["CO2 Supplementation (kg)"] = "N/A"
            
            invoices.extend([electricity_invoice, water_invoice])
            
        return invoices


    def _save_test_case(
        self,
        case_name: str,
        customer_data: Dict,
        adjusted_invoices: List[Dict],
        original_invoices: List[Dict],
        net_facility_subtotals: Dict[str, DecimalHandler],
        payment_amount: DecimalHandler,
        total_invoice_amount: DecimalHandler,
        total_discounts: DecimalHandler,
        total_fees: DecimalHandler,
        test_metadata: Dict
    ):
        """Save test case with both original and adjusted amounts."""
        try:
            self.logger.info(f"Saving test case: {case_name}")
            
            # Get discrepancy config
            discrepancy_config = test_metadata.get('discrepancy_config', {})
            
            # Generate database setup
            self.db_setup_generator.generate_db_setup(
                case_name,
                customer_data,
                adjusted_invoices,
                discrepancy_config,
                self.output_dir
            )
            
            # Prepare metadata - handle both reconciling and discrepancy cases
            metadata = {
                "customer_data": customer_data,
                "facility_subtotals": {
                    k: float(v) for k, v in net_facility_subtotals.items()
                },
                "payment_amount": float(payment_amount),
                "total_invoice_amount": float(total_invoice_amount),
                "total_discounts": float(total_discounts),
                "total_charges": float(total_fees),
                "database_amounts": {
                    "total": float(total_invoice_amount),
                    "facility_totals": {}
                }
            }
            
            # Handle facility totals based on case type
            if case_name == "reconciling_case":
                # For reconciling case, use same totals
                metadata["database_amounts"]["facility_totals"] = {
                    k: float(v) for k, v in net_facility_subtotals.items()
                }
            else:
                # For discrepancy cases, use adjusted totals from test_metadata
                metadata["database_amounts"]["facility_totals"] = {
                    facility_type: float(total)
                    for facility_type, total in test_metadata.get('calculated_amounts', {}).get('facility_totals', {}).items()
                }
            
            # Update metadata with test-specific data
            metadata.update(test_metadata)
            
            # Generate markdown with original amounts
            md_content = self._generate_markdown_content(
                customer_data,
                original_invoices,
                net_facility_subtotals,
                payment_amount,
                total_invoice_amount,
                total_discounts,
                total_fees
            )
            
            # Save files
            output_dir = self.output_dir / case_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
                
            with open(output_dir / "remittance.md", "w") as f:
                f.write("\n".join(md_content))
                
            self.logger.info(f"Successfully saved test case: {case_name}")
            
        except Exception as e:
            self.logger.error(f"Error saving test case: {str(e)}")
            raise

        
    def _convert_decimals_to_float(self, data: Any) -> Any:
        """Recursively convert all Decimal values to float in a nested structure."""
        if isinstance(data, dict):
            return {key: self._convert_decimals_to_float(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_decimals_to_float(item) for item in data]
        elif isinstance(data, (Decimal, DecimalHandler)):
            return float(data)
        return data


    def _generate_vertical_farming_invoices(self, facility_count: int, rounding_adjustment: bool = False) -> List[Dict]:
        """Generate Vertical Farming Unit invoices with consistent decimal handling."""
        invoices = []
        for i in range(1, facility_count + 1):
            facility_id = f"FAA-VF-{i:03d}"
            
            # Electricity invoice
            electricity_amount = self._generate_facility_service_invoice(
                (110000, 160000), rounding_adjustment
            )
            
            electricity_invoice = self._generate_invoice_base(
                f"INV-VF-{6000+i*2-1:06d}",
                float(electricity_amount),
                facility_id,
                "Vertical Farming Units",
                "Electricity",
                i*4
            )
            electricity_invoice["Usage (kWh/Gallons)"] = f"{random.randint(900000, 1300000)} kWh"
            electricity_invoice["LED Light Hours"] = str(random.randint(650, 800))
            
            # Water invoice
            water_amount = self._generate_facility_service_invoice(
                (20000, 35000), rounding_adjustment
            )
            
            water_invoice = self._generate_invoice_base(
                f"INV-VF-{6000+i*2:06d}",
                float(water_amount),
                facility_id,
                "Vertical Farming Units",
                "Water",
                i*4 + 2
            )
            water_invoice["Usage (kWh/Gallons)"] = f"{random.randint(150000, 300000)} Gallons"
            water_invoice["LED Light Hours"] = "N/A"
            
            invoices.extend([electricity_invoice, water_invoice])
            
        return invoices

    def _generate_hydroponics_invoices(self, facility_count: int, rounding_adjustment: bool = False) -> List[Dict]:
        """Generate Hydroponics System invoices with consistent decimal handling."""
        invoices = []
        for i in range(1, facility_count + 1):
            facility_id = f"FAA-HY-{i:03d}"
            
            # Electricity invoice
            electricity_amount = self._generate_facility_service_invoice(
                (60000, 75000), rounding_adjustment
            )
            
            electricity_invoice = self._generate_invoice_base(
                f"INV-HY-{7000+i*2-1:06d}",
                float(electricity_amount),
                facility_id,
                "Hydroponics Systems",
                "Electricity",
                i*8
            )
            electricity_invoice["Usage (kWh/Gallons)"] = f"{random.randint(500000, 650000)} kWh"
            electricity_invoice["Nutrient Solution (L)"] = str(random.randint(20000, 26000))
            
            # Water invoice
            water_amount = self._generate_facility_service_invoice(
                (30000, 40000), rounding_adjustment
            )
            
            water_invoice = self._generate_invoice_base(
                f"INV-HY-{7000+i*2:06d}",
                float(water_amount),
                facility_id,
                "Hydroponics Systems",
                "Water",
                i*8 + 4
            )
            water_invoice["Usage (kWh/Gallons)"] = f"{random.randint(240000, 350000)} Gallons"
            water_invoice["Nutrient Solution (L)"] = "N/A"
            
            invoices.extend([electricity_invoice, water_invoice])
            
        return invoices

    def _generate_sustainable_energy_invoices(self, service_count: int, rounding_adjustment: bool = False) -> List[Dict]:
        """Generate Sustainable Energy Solution invoices with consistent decimal handling."""
        base_services = [
            ("Solar Panel Generation", DecimalHandler.from_str('45000'), "All Facilities", "380,658"),
            ("Wind Turbine Generation", DecimalHandler.from_str('35000'), "FAA-GH-001, FAA-GH-002", "288,066"),
            ("Biogas Generation", DecimalHandler.from_str('25000'), "FAA-GH-003, FAA-GH-004", "195,473"),
            ("Energy Storage System Maintenance", DecimalHandler.from_str('75000'), "All Facilities", "N/A"),
            ("Smart Grid Integration", DecimalHandler.from_str('55000'), "All Facilities", "N/A"),
            ("Microgrid Control System", DecimalHandler.from_str('45000'), "Vertical Farming Units", "N/A")
        ]
        
        while len(base_services) < service_count:
            base_services.extend(base_services)
        
        invoices = []
        for i in range(service_count):
            service, base_amount, facility, usage = base_services[i]
            
            amount = DecimalHandler.round_decimal(base_amount)
            if rounding_adjustment:
                amount = DecimalHandler.round_decimal(
                    amount * DecimalHandler.from_str('1.0005')
                )
            
            invoice = self._generate_invoice_base(
                f"INV-SE-{8000+i+1:06d}",
                float(amount),
                facility,
                "Sustainable Energy Solutions",
                service,
                25 + i*5
            )
            
            invoice["Energy Generated (kWh)"] = usage
            
            if "Maintenance" in service or "Integration" in service or "System" in service:
                discount = DecimalHandler.calc_percentage(amount, DecimalHandler.from_str('0.01'))
                invoice["Discounts"] = float(discount)
                invoice["Payment Sent"] = float(DecimalHandler.round_decimal(amount - discount))
            
            invoices.append(invoice)
            
        return invoices

    def _generate_agritech_invoices(self, service_count: int, rounding_adjustment: bool = False) -> List[Dict]:
        """Generate AgriTech Service invoices with consistent decimal handling."""
        base_services = [
            ("AI-Powered Crop Monitoring", DecimalHandler.from_str('85000'), "All Facilities", "Precision Agriculture"),
            ("Automated Irrigation Management", DecimalHandler.from_str('65000'), "Greenhouse Complexes", "Water Efficiency"),
            ("Nutrient Delivery Optimization", DecimalHandler.from_str('55000'), "Hydroponics Systems", "Resource Management"),
            ("Climate Control AI", DecimalHandler.from_str('45000'), "Vertical Farming Units", "Energy Efficiency"),
            ("Yield Prediction Analytics", DecimalHandler.from_str('35000'), "All Facilities", "Data Analytics"),
            ("Robotic Harvesting System Lease", DecimalHandler.from_str('25000'), "Greenhouse Complexes", "Automation")
        ]
        
        while len(base_services) < service_count:
            base_services.extend(base_services)
        
        invoices = []
        for i in range(service_count):
            service, base_amount, facility, category = base_services[i]
            
            amount = DecimalHandler.round_decimal(base_amount)
            if rounding_adjustment:
                amount = DecimalHandler.round_decimal(
                    amount * DecimalHandler.from_str('1.0005')
                )
            
            invoice = self._generate_invoice_base(
                f"INV-AT-{9000+i+1:06d}",
                float(amount),
                facility,
                "AgriTech Services",
                service,
                i*5
            )
            
            invoice["Service Category"] = category
            invoices.append(invoice)
            
        return invoices

    def _generate_rd_facility_invoices(self) -> List[Dict]:
        """Generate Research & Development facility invoices with consistent decimal handling."""
        services = [
            ("Lab Equipment Power", DecimalHandler.from_str('45000'), "Power consumption for lab equipment"),
            ("Climate Control", DecimalHandler.from_str('35000'), "Specialized environment maintenance"),
            ("Water Purification", DecimalHandler.from_str('25000'), "Ultra-pure water systems"),
            ("Data Center Cooling", DecimalHandler.from_str('30000'), "Cooling for research computers")
        ]
        
        invoices = []
        for i, (service, base_amount, description) in enumerate(services, 1):
            amount = DecimalHandler.round_decimal(base_amount)
            
            invoice = self._generate_invoice_base(
                f"INV-RD-{1000+i:06d}",
                float(amount),
                "FAA-RD-001",
                "Research & Development",
                service,
                i*3
            )
            invoice["Description"] = description
            invoice["Usage (kWh/Gallons)"] = self._generate_usage_for_service(service)
            invoices.append(invoice)
            
        return invoices
    
    def _get_discrepancy_config(self, case_name: str, test_metadata: Dict) -> Optional[Dict]:
        """Generate appropriate discrepancy configuration based on test case type."""
        if case_name == "single_facility_discrepancy":
            return {
                'type': 'single_facility',
                'adjustments': {
                    'Greenhouse Complexes': float(DecimalHandler.from_str('1.02'))
                }
            }
        elif case_name == "multi_facility_discrepancy":
            return {
                'type': 'multi_facility',
                'adjustments': {
                    'Greenhouse Complexes': float(DecimalHandler.from_str('1.015')),
                    'Vertical Farming Units': float(DecimalHandler.from_str('0.99')),
                    'Hydroponics Systems': {
                        'condition': 'water_service',
                        'factor': float(DecimalHandler.from_str('1.02'))
                    }
                }
            }
        elif case_name == "threshold_adjustment_case":
            return {
                'type': 'threshold',
                'threshold': float(DecimalHandler.from_str(str(test_metadata.get('threshold', '0.0005')))),
                'adjustments': {}
            }
        
        return None    


    # 2. _generate_threshold_adjustment_case
    def _generate_threshold_adjustment_case(self):
        """Generate test case for threshold adjustment scenario."""
        customer_data = {
            "customer_name": "RootRite Farm Group",
            "customer_id": "FAA-62405",
            "payment_date": "2024-10-11",
            "account_number": "*****9544",
            "payment_reference": "WIRE2024100505",
            "payment_method": "Wire Transfer",
            "remittance_notes": "Q3 2024 Utility Services with minor rounding differences"
        }
        
        # Generate valid document invoices
        invoices, facility_subtotals = self._generate_base_invoices()
        
        # Calculate document totals with small threshold difference
        total_invoice_amount = sum(
            DecimalHandler.from_str(str(inv['Amount Due'])) 
            for inv in invoices
        )
        total_discounts = sum(
            DecimalHandler.from_str(str(inv['Discounts'])) 
            for inv in invoices
        )
        total_fees = DecimalHandler.from_str('0')
        net_amount = DecimalHandler.round_decimal(total_invoice_amount - total_discounts)
        
        # Create 0.05% difference
        threshold_difference = DecimalHandler.round_decimal(
            net_amount * DecimalHandler.from_str('0.0005')
        )
        payment_amount = DecimalHandler.round_decimal(net_amount - threshold_difference)
        
        self._save_test_case(
            "threshold_adjustment_case",
            customer_data,
            invoices,
            facility_subtotals,
            payment_amount,
            total_invoice_amount,
            total_discounts,
            total_fees,
            {
                "discrepancy_type": "Threshold",
                "discrepancy_amount": float(threshold_difference),
                "current_threshold": "0.01%",
                "suggested_threshold": "0.05%",
                "expected_reconciliation": {
                    "with_default_threshold": {
                        "status": "DISCREPANCY_FOUND",
                        "total_discrepancy": float(threshold_difference)
                    },
                    "with_adjusted_threshold": {
                        "status": "MATCHED",
                        "total_discrepancy": float(threshold_difference)
                    }
                }
            }
        )

    # 3. _generate_reconciling_case
    def _generate_reconciling_case(self, customer_data: Dict):
        """Generate a test case that perfectly reconciles."""
        # Generate base invoices with exact matching amounts
        invoices, facility_subtotals = self._generate_base_invoices()
        
        # Calculate totals using DecimalHandler
        total_invoice_amount = sum(
            DecimalHandler.from_str(str(inv['Amount Due'])) 
            for inv in invoices
        )
        total_discounts = sum(
            DecimalHandler.from_str(str(inv['Discounts'])) 
            for inv in invoices
        )
        total_fees = sum(
            DecimalHandler.from_str(str(inv['Fees'])) 
            for inv in invoices
        )
        
        # Set payment to exactly match (for reconciling case)
        payment_amount = DecimalHandler.round_decimal(
            total_invoice_amount - total_discounts + total_fees
        )
        
        self._save_test_case(
            "reconciling_case",
            customer_data,
            invoices,
            facility_subtotals,
            payment_amount,
            total_invoice_amount,
            total_discounts,
            total_fees,
            {
                "case_type": "Reconciling",
                "expected_reconciliation": {
                    "status": "MATCHED",
                    "total_discrepancy": 0.0,
                    "facility_discrepancies": {}
                }
            }
        )

    # 4. _generate_single_facility_discrepancy
    def _generate_single_facility_discrepancy(self, customer_data: Dict):
        """Generate test case where discrepancy is concentrated in one facility type."""
        # Generate base invoices (no increases applied)
        invoices, facility_subtotals = self._generate_base_invoices()
        
        # Calculate the expected discrepancy amount for metadata
        base_gh_amount = sum(
            DecimalHandler.from_str(str(inv['Amount Due']))
            for inv in invoices
            if inv['Facility Type'] == "Greenhouse Complexes"
        )
        discrepancy_amount = DecimalHandler.round_decimal(
            base_gh_amount * DecimalHandler.from_str('0.02')
        )
        
        # Calculate totals from base amounts
        total_invoice_amount = sum(
            DecimalHandler.from_str(str(inv['Amount Due'])) 
            for inv in invoices
        )
        total_discounts = sum(
            DecimalHandler.from_str(str(inv['Discounts'])) 
            for inv in invoices
        )
        total_charges = sum(
            DecimalHandler.from_str(str(inv.get('Additional Charges', '0'))) 
            for inv in invoices
        )
        net_amount = DecimalHandler.round_decimal(
            total_invoice_amount - total_discounts + total_charges
        )
        
        # Payment should match document amounts
        payment_amount = net_amount
        
        self._save_test_case(
            "single_facility_discrepancy",
            customer_data,
            invoices,
            facility_subtotals,
            payment_amount,
            total_invoice_amount,
            total_discounts,
            total_charges,
            {
                "discrepancy_type": "Single Facility",
                "affected_facility": "Greenhouse Complexes",
                "discrepancy_amount": float(discrepancy_amount),
                "discrepancy_pattern": "2% higher in database for Greenhouse Complex invoices",
                "expected_reconciliation": {
                    "status": "DISCREPANCY_FOUND",
                    "total_discrepancy": float(discrepancy_amount),
                    "facility_discrepancies": {
                        "Greenhouse Complexes": float(discrepancy_amount)
                    }
                }
            }
        )

    # 5. _generate_multi_facility_discrepancy
    def _generate_multi_facility_discrepancy(self, customer_data: Dict):
        """Generate test case where discrepancies are spread across multiple facilities."""
        # Generate base invoices (no adjustments)
        invoices, facility_subtotals = self._generate_base_invoices()
        
        # Calculate expected discrepancy amounts for metadata
        gh_base = facility_subtotals["Greenhouse Complexes"]
        gh_discrepancy = DecimalHandler.round_decimal(
            gh_base * DecimalHandler.from_str('0.015')
        )
        
        vf_base = facility_subtotals["Vertical Farming Units"]
        vf_discrepancy = DecimalHandler.round_decimal(
            vf_base * DecimalHandler.from_str('-0.01')
        )
        
        # Calculate Hydroponics water service discrepancy
        hy_water_base = sum(
            DecimalHandler.from_str(str(inv['Amount Due']))
            for inv in invoices
            if inv['Facility Type'] == "Hydroponics Systems" 
            and inv['Service Type'] == "Water"
        )
        hy_discrepancy = DecimalHandler.round_decimal(
            hy_water_base * DecimalHandler.from_str('0.02')
        )
        
        # Calculate totals from base amounts
        total_invoice_amount = sum(
            DecimalHandler.from_str(str(inv['Amount Due'])) 
            for inv in invoices
        )
        total_discounts = sum(
            DecimalHandler.from_str(str(inv['Discounts'])) 
            for inv in invoices
        )
        total_fees = DecimalHandler.from_str('0')
        
        # Payment should match document amounts
        payment_amount = DecimalHandler.round_decimal(
            total_invoice_amount - total_discounts + total_fees
        )
        
        self._save_test_case(
            "multi_facility_discrepancy",
            customer_data,
            invoices,
            facility_subtotals,
            payment_amount,
            total_invoice_amount,
            total_discounts,
            total_fees,
            {
                "discrepancy_type": "Multi Facility",
                "discrepancy_pattern": {
                    "Greenhouse Complexes": "1.5% higher in database",
                    "Vertical Farming Units": "1% lower in database",
                    "Hydroponics Systems": "2% higher for water invoices in database"
                },
                "expected_reconciliation": {
                    "status": "DISCREPANCY_FOUND",
                    "facility_discrepancies": {
                        "Greenhouse Complexes": float(gh_discrepancy),
                        "Vertical Farming Units": float(vf_discrepancy),
                        "Hydroponics Systems": float(hy_discrepancy)
                    }
                }
            }
        )
        
   
    def _generate_markdown_content(
        self,
        customer_data: Dict,
        original_invoices: List[Dict],  # Original amounts
        net_facility_subtotals: Dict[str, DecimalHandler],  # Pre-calculated NET amounts per facility
        payment_amount: DecimalHandler,
        total_amount_due: DecimalHandler,  # DB total with 2% adjustment
        total_discounts: DecimalHandler,
        total_fees: DecimalHandler
    ) -> List[str]:
        """Generate markdown using original amounts but showing adjusted total amount due."""
        
        # Header section
        content = [
            "# AquaEnergy Solutions - Wire Transfer Remittance\n",
            f"Payer Name: {customer_data['customer_name']}  ",
            f"Client ID: {customer_data['customer_id']}  ",
            f"Wire Transfer Date: {customer_data['payment_date']}  ",
            f"Beneficiary Account Number: {customer_data['account_number']}  ",
            f"Total Wire Amount: ${float(payment_amount):,.2f}  ",
            f"Wire Transfer Reference: {customer_data['payment_reference']}  ",
            f"Payment Type: {customer_data['payment_method']}  ",
            f"Additional Payment Notes: {customer_data['remittance_notes']}\n",
            "## Remittance Details\n"
        ]
        
        # Group invoices by facility type
        grouped_invoices = {}
        for invoice in original_invoices:  # Use original invoices
            facility_type = invoice['Facility Type']
            if facility_type not in grouped_invoices:
                grouped_invoices[facility_type] = []
            grouped_invoices[facility_type].append(invoice)
        
        # Generate facility sections
        for facility_type in self.facility_types:
            if facility_type in grouped_invoices:
                content.extend([
                    f"### {facility_type}\n",
                    self._generate_facility_table(facility_type, grouped_invoices[facility_type]),
                    f"\nSubtotal for {facility_type}: ${float(net_facility_subtotals[facility_type]):,.2f}\n\n"
                ])
        
        # Verify totals match
        total_from_net_subtotals = sum(
            DecimalHandler.from_str(str(subtotal))
            for subtotal in net_facility_subtotals.values()
        )
        assert abs(float(total_from_net_subtotals) - float(payment_amount)) < 0.03, (
            f"Payment amount {float(payment_amount):,.2f} doesn't match "
            f"sum of net subtotals {float(total_from_net_subtotals):,.2f}"
        )
        
        # Add summary section showing both original NET total and DB total amount due
        content.extend([
            f"Total Invoices: {len(original_invoices)}  ",
            f"Total Amount Due: ${float(total_amount_due):,.2f}  ",  # DB amount with 2% adjustment
            f"Total Payment Sent: ${float(payment_amount):,.2f}  ",  # Sum of NET amounts
            f"Total Discounts: ${float(total_discounts):,.2f}  ",
            f"Total Fees: ${float(total_fees):,.2f}\n",
            "\nPlease apply payments as detailed above. For any questions, contact agri.billing@aquaenergy.com."
        ])
        
        return content
    
   
    
    
    def _generate_facility_table(self, facility_type: str, invoices: List[Dict]) -> str:
        """Generate markdown table with improved PDF rendering."""
        # Add more spacing around table and force page break before each facility section
        table = [
            "\n\n<div style='page-break-before: always;'>\n",  # Force page break before new facility
            "\n"  # Extra spacing
        ]
        
        # Make headers with consistent column widths
        headers = [
            "Invoice Reference    ",  # Add padding spaces
            "Amount Due          ",
            "Payment Sent        ",
            "Discounts          ", 
            "Fees      ",
            "Date of Invoice    ",
            "Facility ID        ",
            "Service Type       ",
            "Usage (kWh/Gallons)         "
        ]
        
        # Add facility-specific column with padding
        if facility_type == "Greenhouse Complexes":
            headers.append("CO2 Supplementation (kg)    ")
        elif facility_type == "Vertical Farming Units":
            headers.append("LED Light Hours    ")
        elif facility_type == "Hydroponics Systems":
            headers.append("Nutrient Solution (L)    ")
        elif facility_type == "Sustainable Energy Solutions":
            headers[-1] = "Energy Generated (kWh)        "  # Replace usage column
        elif facility_type == "AgriTech Services":
            headers.append("Service Category        ")

        # Create table with extra spacing and column alignment
        table.extend([
            "| " + " | ".join(headers) + " |",
            "|" + "|".join([":" + "-"*max(len(h)-1, 15) + ":" for h in headers]) + "|"  # Center-align with minimum width
        ])
        
        # Add rows with consistent spacing
        for invoice in invoices:
            # Get amounts with proper decimal handling
            amount_due = DecimalHandler.from_str(str(invoice['Amount Due']))
            discounts = DecimalHandler.from_str(str(invoice.get('Discounts', '0')))
            fees = DecimalHandler.from_str(str(invoice.get('Fees', '0')))
            payment_sent = DecimalHandler.round_decimal(amount_due - discounts + fees)
            
            # Build row with padded cells
            row = [
                f"{invoice['Invoice Reference']:<15}",
                f"${float(amount_due):>14,.2f}",
                f"${float(payment_sent):>14,.2f}",
                f"${float(discounts):>12,.2f}",
                f"${float(fees):>7,.2f}",
                f"{invoice['Date of Invoice']:<15}",
                f"{invoice['Facility ID']:<15}",
                f"{invoice.get('Service Type', ''):<15}"
            ]
            
            # Safe handling of usage/energy data with None protection
            if facility_type == "Sustainable Energy Solutions":
                energy_value = invoice.get('Energy Generated (kWh)') or 'N/A'
                row.append(f"{str(energy_value):<20}")
            else:
                usage_value = invoice.get('Usage (kWh/Gallons)') or 'N/A'
                row.append(f"{str(usage_value):<20}")
            
            # Add facility-specific column with None protection
            if facility_type == "Greenhouse Complexes":
                co2_value = invoice.get('CO2 Supplementation (kg)') or 'N/A'
                row.append(f"{str(co2_value):<20}")
            elif facility_type == "Vertical Farming Units":
                led_value = invoice.get('LED Light Hours') or 'N/A'
                row.append(f"{str(led_value):<15}")
            elif facility_type == "Hydroponics Systems":
                nutrient_value = invoice.get('Nutrient Solution (L)') or 'N/A'
                row.append(f"{str(nutrient_value):<20}")
            elif facility_type == "AgriTech Services":
                category_value = invoice.get('Service Category') or 'N/A'
                row.append(f"{str(category_value):<20}")
            
            table.append("| " + " | ".join(row) + " |")
        
        # Add closing div and extra spacing
        table.extend([
            "\n</div>\n\n"  # Close div and add spacing
        ])
        
        return "\n".join(table)