from contextlib import contextmanager
from functools import partial
from pprint import pprint
from typing import Callable, TypeVar

from httpx import Client as HTTPXClient
from httpx import HTTPStatusError
from pydantic import BaseModel
from sema4ai.actions import OAuth2Secret

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
        raise exc
    finally:
        client.close()
