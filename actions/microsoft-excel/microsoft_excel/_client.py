from io import BytesIO
from pprint import pprint
from typing import Callable, TypeVar

import sema4ai_http
import xlsxwriter
from pydantic import BaseModel
from sema4ai.actions import OAuth2Secret

from microsoft_excel._constants import EXCEL_MIME_TYPE
from microsoft_excel.models import APIResponse
from microsoft_excel.models.workbook import Workbook
from microsoft_excel.models.worksheet import WorksheetInfo

T = TypeVar("T", bound=BaseModel)


class Client:
    def __init__(self, token: OAuth2Secret):
        self.token = token

    def get(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(model, sema4ai_http.get, url, **kwargs)

    def post(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(model, sema4ai_http.post, url, **kwargs)

    def put(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(model, sema4ai_http.put, url, **kwargs)

    def patch(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(model, sema4ai_http.patch, url, **kwargs)

    def _make_request(self, model: type[T], method: Callable, url: str, **kwargs) -> T:
        url = url.lstrip("/")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            headers.update(extra_headers)

        raw_result = method(url, headers, **kwargs)
        raw_result.raise_for_status()

        pprint(raw_result.json())
        return model.model_validate_json(raw_result.content)


def _create_workbook(client: Client, workbook_name: str) -> Workbook:
    output = BytesIO()
    workbook_name = f"{workbook_name}.xlsx"
    with xlsxwriter.Workbook(output, {"in_memory": True}) as local_workbook:
        local_worksheet = local_workbook.add_worksheet()
        local_worksheet.activate()

    workbook = client.put(
        Workbook,
        f"/me/drive/root:/{workbook_name}:/content",
        headers={"Content-Type": EXCEL_MIME_TYPE},
        data=output.getvalue(),
    )

    return workbook


def _create_worksheet(
    client: Client, *, workbook_id: str, worksheet_name: str | None = None
) -> WorksheetInfo:
    if worksheet_name and worksheet_name.strip():
        request_kwargs = {"json": {"name": worksheet_name}}
    else:
        request_kwargs = {}

    return client.post(
        WorksheetInfo,
        f"/me/drive/items/{workbook_id}/workbook/worksheets/add",
        **request_kwargs,
    )


def _load_worksheets_for_workbook(client: Client, workbook: Workbook) -> Workbook:
    if workbook.worksheets is None:
        worksheet_info = client.get(
            APIResponse[WorksheetInfo],
            f"/me/drive/items/{workbook.id}/workbook/worksheets",
        )

        workbook.worksheets = worksheet_info.value

    return workbook
