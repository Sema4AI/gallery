from contextlib import contextmanager
from functools import partial
from io import BytesIO
from pprint import pprint
from typing import Callable, TypeVar

import xlsxwriter
from httpx import Client as HTTPXClient
from httpx import HTTPStatusError
from pydantic import BaseModel
from sema4ai.actions import ActionError, OAuth2Secret

from microsoft_excel._constants import EXCEL_MIME_TYPE
from microsoft_excel.models import APIResponse
from microsoft_excel.models.workbook import Workbook
from microsoft_excel.models.worksheet import WorksheetInfo

T = TypeVar("T", bound=BaseModel)


class Client:
    def __init__(self, client: HTTPXClient):
        self.httpx = client

    def get(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(
            model, partial(self.httpx.get, url.lstrip("/"), **kwargs)
        )

    def post(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(
            model, partial(self.httpx.post, url.lstrip("/"), **kwargs)
        )

    def put(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(
            model, partial(self.httpx.put, url.lstrip("/"), **kwargs)
        )

    def patch(self, model: type[T], url: str, **kwargs) -> T:
        return self._make_request(
            model, partial(self.httpx.patch, url.lstrip("/"), **kwargs)
        )

    @staticmethod
    def _make_request(model: type[T], method: Callable) -> T:
        raw_result = method()
        pprint(raw_result.json())
        raw_result.raise_for_status()
        return model.model_validate_json(raw_result.content)

    def close(self):
        self.httpx.close()


@contextmanager
def get_client(token: OAuth2Secret) -> Client:
    session = HTTPXClient(
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        },
        base_url="https://graph.microsoft.com/v1.0/",
    )

    client = Client(session)
    try:
        yield client
    except HTTPStatusError as exc:
        # TODO add specific error handling
        if exc.response:
            raise ActionError(exc.response.text)
        raise exc
    finally:
        client.close()


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
