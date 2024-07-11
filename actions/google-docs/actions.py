from typing import Literal

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleApiHttpError
from sema4ai.actions import (
    ActionError,
    OAuth2Secret,
    Response,
    action,
)
from typing_extensions import Self

from models.documents import DocumentInfo, MarkdownDocument, RawDocument
from models.update_operations import BatchUpdateBody


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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._docs is not None:
            self._docs.close()

        if self._drive is not None:
            self._drive.close()

        if isinstance(exc_val, RefreshError):
            raise ActionError("Access token expired") from None
        elif isinstance(exc_val, GoogleApiHttpError):
            raise ActionError(exc_val.reason) from None

@action
def get_document_by_name(
    name: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.readonly"]],
    ],
) -> Response[MarkdownDocument]:
    """Get a Google Document by its name.

    If multiple documents with the same name are found,
    you need to use the ID of the document to load it.
    Hint: Copy-pasting the URL of the document in the Agent will allow it to fetch the document by ID

    Apostrophes in the title need to be escaped with a backslash.
    The result is the Document formatted using the Extended Markdown Syntax.

    Args:
        oauth_access_token: The OAuth2 Google access token
        name: The Google Document name
    Returns:
        The Google Document as a markdown formatted string.
    """

    with Context(oauth_access_token) as ctx:
        return Response(
            result=MarkdownDocument.from_raw_document(
                _load_raw_document(ctx, _get_document_id(ctx, name))
            )
        )


@action
def get_document_by_id(
    document_id: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/documents.readonly"]],
    ],
) -> Response[MarkdownDocument]:
    """Get a Google Document by its ID. The result is the Document formatted using the Extended Markdown Syntax.

    Args:
        oauth_access_token: The OAuth2 Google access token
        document_id: The Google Document ID.
    Returns:
        The Google Document as a markdown formatted string.
    """

    with Context(oauth_access_token) as ctx:
        raw_doc = _load_raw_document(ctx, document_id)
        doc = MarkdownDocument(
            title=raw_doc.title,
            documentId=raw_doc.documentId,
            body=raw_doc.to_markdown(),
        )

        return Response(result=doc)


@action(is_consequential=True)
def create_document(
    title: str,
    body: str,
    oauth_access_token: OAuth2Secret[
        Literal["google"],
        list[Literal["https://www.googleapis.com/auth/drive.file"]],
    ],
) -> Response[DocumentInfo]:
    """Create a new Google Document from an Extended Markdown string.

     Args:
        title: The Google Document title
        body: The Google Document body as an Extended Markdown string.
        oauth_access_token: The OAuth2 Google access token

    Returns:
        A structure containing the Document
    """

    with Context(oauth_access_token) as ctx:
        doc = _create_document(ctx, title)
        try:
            ctx.documents.batchUpdate(
                documentId=doc.documentId,
                body=BatchUpdateBody.from_markdown(body).get_body(),
            ).execute()
        except Exception:
            # Clean-up in case of error.
            ctx.files.delete(fileId=doc.documentId).execute()
            raise

        return Response(result=doc)


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


def _load_raw_document(ctx: Context, document_id: str) -> RawDocument:
    document_id = document_id.strip()
    raw_doc = ctx.documents.get(documentId=document_id).execute()
    return RawDocument.from_google_response(raw_doc)


def _create_document(ctx, title: str) -> DocumentInfo:
    return DocumentInfo.model_validate(
        ctx.documents.create(body={"title": title}).execute()
    )
