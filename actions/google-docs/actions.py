from typing import Literal

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from sema4ai.actions import (
    ActionError,
    OAuth2Secret,
    Response,
    action,
)

from models import Document


class Context:
    def __init__(self, secret: OAuth2Secret):
        self._secret = secret
        self._docs = None
        self._drive = None

    @property
    def documents(self) -> Resource:
        if self._docs is None:
            self._docs = build(
                "docs", "v1", credentials=Credentials(token=self._secret.access_token)
            )
        return self._docs.documents()

    @property
    def files(self) -> Resource:
        if self._drive is None:
            self._drive = build(
                "drive", "v3", credentials=Credentials(token=self._secret.access_token)
            )

        return self._drive.files()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._docs is not None:
            self._docs.close()

        if self._drive is not None:
            self._drive.close()

        if isinstance(exc_val, RefreshError):
            raise ActionError("Access token expired") from None


@action
def get_document_by_name(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
    name: str,
) -> Response[Document]:
    """Get a Google Document by its name.
    Apostrophes in the title need to be escaped with a backslash.
    The result is the Document formatted using the Extended Markdown Syntax.

    Args:
        oauth_access_token: The OAuth2 Google access token
        name: The Google Document name
    Returns:
        The Google Document as a markdown formatted string.
    """

    with Context(oauth_access_token) as ctx:
        return Response(result=_load_document(ctx, _get_document_id(ctx, name)))


@action
def get_document_by_id(
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly"]],
    ],
    document_id: str,
) -> Response[Document]:
    """Get a Google Document by its ID. The result is the Document formatted using the Extended Markdown Syntax.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: The Google Document ID.
    Returns:
        The Google Document as a markdown formatted string.
    """
    # oauth_access_token = _load_token()

    with Context(oauth_access_token) as ctx:
        return Response(result=_load_document(ctx, document_id))


def _get_document_id(ctx: Context, name: str) -> str:
    name = name.strip()

    response = ctx.files.list(
        fields="files/id,files/name",
        q=f"name contains '{name}' and mimeType='application/vnd.google-apps.document'",
    ).execute()

    if not (files := response.get("files")):
        raise ActionError("Could not find document.")

    if len(files) > 1:
        choices = []
        for f in files:
            if name == f["name"]:
                return f["id"]

            choices.append(f["name"])

        choices = ", ".join(choices)

        raise ActionError(
            f"Multiple files found, you must choose one of the following: {choices}."
        )

    return response["files"][0]["id"]


def _load_document(ctx: Context, document_id: str) -> Document:
    document_id = document_id.strip()
    raw_doc = ctx.documents.get(documentId=document_id).execute()
    doc = Document.from_google_response(raw_doc)
    return doc
