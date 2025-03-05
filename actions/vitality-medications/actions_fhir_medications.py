import json
from datetime import datetime

from fhir_medications_service import FHIRMedicationsService
from sema4ai.actions import Response, action

fhir_medications_service = FHIRMedicationsService("fhir_medications.json")


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()


@action(is_consequential=False)
def get_current_medications() -> Response[str]:
    """
    Fetches summaries of current medications
    sorted by treatment start date.

    Returns:
        list of dicts: A list of current medications
        with summary data including medication name,
        reason, status,treatment period,
        dosage instruction, etc

    Description:
        The fhir_schema.json file uploaded
        to the Knowledge should be used
        to learn more about dict in the returned list

    Note:
        - Key information to always display to
        user are: medication name, reason, status,
        treatment period start and dosage instruction.
    """

    current_medications = fhir_medications_service.get_current_medications()
    return Response(result=json.dumps(current_medications, default=datetime_converter))


@action(is_consequential=False)
def get_entire_medication_history(start_date: str, end_date: str) -> Response[str]:
    """
     Retrieves the medication history dict for the given date ranged sorted by treatmentPeriodStart keyed by RxNorm
     If start_date and end_date are None, all history is returned.

    Args:
        start_date (str): The start date  history. Date should be in "YYYY-MM-DD" format.
        end_date (str): The end date  history. Date should be in "YYYY-MM-DD" format.

    Returns:
        str: A JSON string representing the patient's medication history.
    """
    history_start = None
    if start_date:
        history_start = start_date

    history_end = None
    if end_date:
        history_end = end_date

    medication_history = fhir_medications_service.get_entire_medication_history(
        history_start, history_end
    )
    return Response(result=json.dumps(medication_history, default=datetime_converter))


@action(is_consequential=False)
def get_medication_history_by_rxnorm(rxnorm_code: str) -> str:
    """
    Retrieves a medication's  history sorted by treatmentPeriodStart for a given RxNorm code.
    The most important information to show: medication name, treatment period, dosage quantity and status
    Used to identify changes to dosage quantity or name (generic to brandname or vice versa)
    """

    medication_history = fhir_medications_service.get_medication_history_by_rxnorm(
        rxnorm_code
    )

    # Return compact json string
    return Response(result=json.dumps(medication_history, default=datetime_converter))
