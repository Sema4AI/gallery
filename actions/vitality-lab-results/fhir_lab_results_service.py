import json
import os
from datetime import datetime, timedelta


class FHIRLabResultsService:
    def __init__(self, file_name):
        self.lab_results_data = self.load_json_data(file_name)

    def load_json_data(self, file_name):
        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "data", file_name)
        """Loads lab results data from a JSON file."""
        with open(file_path, 'r') as file:
            return json.load(file)

    def list_lab_tests_by_category(self):
        """Organizes lab tests by their category based on the 'basedOn.display' and groups them by LOINC codes."""
        categorized_tests = {}
        for result in self.lab_results_data:
            based_on = result.get('basedOn', [])
            if not based_on or not isinstance(based_on, list) or 'display' not in based_on[0]:
                continue
            category = based_on[0]['display']

            code = result.get('code', {})
            test_name = code.get('text', 'Unknown')
            loinc_codes = [coding['code'] for coding in code.get('coding', []) if
                           coding.get('system') == "http://loinc.org"]

            if category not in categorized_tests:
                categorized_tests[category] = []
            for loinc_code in loinc_codes:
                categorized_tests[category].append({'test_name': test_name, 'loinc_code': loinc_code})
        return categorized_tests

    def get_yearly_lab_results_snapshot(self, loinc_codes):
        """Fetches lab results from the last year for specified LOINC codes."""
        one_year_ago = datetime.now() - timedelta(days=365)
        results = []
        for result in self.lab_results_data:
            effective_date_str = result.get('effectiveDateTime')
            if not effective_date_str:
                continue
            try:
                effective_date = datetime.strptime(effective_date_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
            if effective_date > one_year_ago:
                code = result.get('code')
                if code is None:
                    continue
                coding = code.get('coding', [])
                if coding is None:
                    continue
                if any(coding_entry.get('code') in loinc_codes for coding_entry in coding if 'code' in coding_entry):
                    results.append(result)
        return results

    def get_historical_lab_results(self, loinc_codes, start_date, end_date):
        """Fetches lab results within a specified date range for given LOINC codes."""
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        filtered_results = []
        for result in self.lab_results_data:
            effective_date_str = result.get('effectiveDateTime')
            if not effective_date_str:
                continue
            try:
                effective_date = datetime.strptime(effective_date_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
            if (not start_datetime or effective_date >= start_datetime) and (
                    not end_datetime or effective_date <= end_datetime):
                code = result.get('code')
                if code is None:
                    continue
                coding = code.get('coding', [])
                if coding is None:
                    continue
                if any(coding_entry.get('code') in loinc_codes for coding_entry in coding if 'code' in coding_entry):
                    filtered_results.append(result)
        return filtered_results
