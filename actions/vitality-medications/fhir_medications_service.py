import json
import os
from datetime import datetime


class FHIRMedicationsService:
    def __init__(self, file_name):
        self.medication_data = self.load_json_data(file_name)

    def load_json_data(self, file_name):
        module_dir = os.path.dirname(__file__)
        file_path = os.path.join(module_dir, "data", file_name)
        """Loads lab results data from a JSON file."""
        with open(file_path, 'r') as file:
            return json.load(file)

    def get_current_medications(self):
        """Fetches summaries of current medications sorted by treatment start date."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_medications = []

        for med in self.medication_data:
            if 'dispenseRequest' in med and bool(med['dispenseRequest'].get('validityPeriod')):
                validity = med['dispenseRequest']['validityPeriod']
                if validity['start'] <= current_date <= validity.get('end', current_date):
                    if med['status'] == 'active':
                        current_medications.append(med)

        return sorted(current_medications, key=lambda x: x['dispenseRequest']['validityPeriod']['start'])

    def get_entire_medication_history(self, start_date=None, end_date=None):
        """Retrieves the medication history for a given date range."""
        filtered_medications = []

        for med in self.medication_data:
            if 'dispenseRequest' in med and bool(med['dispenseRequest'].get('validityPeriod')):
                start = med['dispenseRequest']['validityPeriod']['start']
                end = med['dispenseRequest']['validityPeriod'].get('end')

                if ((start_date is None or start >= start_date) and
                        (end_date is None or (end is not None and end <= end_date))):
                    filtered_medications.append(med)

        return filtered_medications

    def get_medication_history_by_rxnorm(self, rxnorm_code):
        """Retrieves a medication's history for a given RxNorm code."""
        medication_history = []

        for med in self.medication_data:
            if 'contained' in med:
                for item in med['contained']:
                    for coding in item.get('code', {}).get('coding', []):
                        if coding.get('system') == 'http://www.nlm.nih.gov/research/umls/rxnorm' and coding.get(
                                'code') == rxnorm_code:
                            dispense_request = med.get('dispenseRequest')
                            if dispense_request:
                                validity_period = dispense_request.get('validityPeriod')
                                if validity_period and validity_period.get('start'):
                                    medication_history.append(med)
                                    break

        return sorted(medication_history, key=lambda x: x['dispenseRequest']['validityPeriod']['start'])