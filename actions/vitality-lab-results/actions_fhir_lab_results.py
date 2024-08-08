from datetime import datetime
from typing import List

import json
from sema4ai.actions import action
from fhir_lab_results_service import FHIRLabResultsService

fhir_lab_results_service = FHIRLabResultsService("fhir_lab_results.json")


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()


@action(is_consequential=False)
def list_lab_tests_by_category() -> str:
    """
    Fetches a categorized list of lab tests  with its test names and LOINC codes. Provides a structured overview of a patient's lab test history useful for mapping
    natural language queries to structured data to use with other APIs.

    No parameters are required.

    Returns:
        str: A JSON string representing a mapping of lab test categories to lists of lab tests. Each lab test is described by a dictionary with 'test_name' and 'loinc_code'. This format allows for easy navigation and identification of LOENC codes by lab test category.

        The JSON string will often need to be parsed to collect the LOINC codes and/or categories for specific lab tests, which can then be used to fetch detailed lab results.
    """
    lab_test_category_dict = fhir_lab_results_service.list_lab_tests_by_category()
    # Return compact json string
    return json.dumps(lab_test_category_dict, default=datetime_converter)


@action(is_consequential=False)
def get_yearly_lab_results_snapshot(loinc_codes: str) -> str:
    """
    Fetches the latest lab results within the last year, providing a snapshot of the most recent health status. Designed for quick health checks and monitoring current conditions. This action is not adjustable for periods beyond the last year, making it ideal for recent health trend analysis.

    Args:
        - loinc_codes (str): Comma-separated list of LOINC codes for lab tests, determined by
            'list_lab_tests_by_category'. Example: '12345-6,78910-1'.

        - Example Request:
            {
                "input": {
                    "loinc_codes": "13457-7,14442-8",    }
            }
    """
    loinc_codes_list = get_loinc_codes_list(loinc_codes)
    lab_results = fhir_lab_results_service.get_yearly_lab_results_snapshot(loinc_codes_list)
    return json.dumps(lab_results, default=datetime_converter)


@action(is_consequential=False)
def get_historical_lab_results(loinc_codes: str, start_date: str = "", end_date: str = "") -> str:
    """
    Fetches all lab results based on provided LOINC codes within a specified date range. Ideal for in-depth health analysis for a set of tests, enabling users to trace health trends, compare lab results across multiple years.

    Args:
        - loinc_codes (str): Comma-separated list of LOINC codes for lab tests Example: '12345-6,78910-1'.
        - start_date (str): Optional start date to filter lab results, in 'YYYY-MM-DD' format. Use an empty string if no start date is provided. If both start date and end date is not provided, the method will return all the lab results for the given LOINC codes.
        - end_date (str): Optional end date to filter lab results, in 'YYYY-MM-DD' format.  Use an empty string if no end date is provided.
    """
    loinc_codes_list = get_loinc_codes_list(loinc_codes)
    lab_results = fhir_lab_results_service.get_historical_lab_results(loinc_codes_list, start_date, end_date)
    return json.dumps(lab_results, default=datetime_converter)


def get_loinc_codes_list(loinc_codes) -> List[str]:
    """Parses and returns LOINC codes as a list from the comma-separated string."""
    return [code.strip() for code in loinc_codes.split(",")] if loinc_codes else []
