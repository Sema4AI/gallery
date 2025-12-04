# Google Documents

Action Package interacting with Google Documents.

Possible actions with this package are:

- Get Document By Name (with optional download)
- Get Document By Id (with optional download)
- Create Document
- Append To Document By Id
- Append To Document By Name

Please note that the current implementation return the documents in Extended Markdown.

## Download Features

The `get_document_by_name` and `get_document_by_id` actions now support downloading Google Docs files in various formats and automatically attaching them to chat:

### Supported Export Formats
- **PDF** (`application/pdf`) - Portable Document Format
- **DOCX** (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`) - Microsoft Word Document
- **TXT** (`text/plain`) - Plain Text
- **HTML** (`text/html`) - HyperText Markup Language
- **RTF** (`application/rtf`) - Rich Text Format
- **ODT** (`application/vnd.oasis.opendocument.text`) - OpenDocument Text

### Usage Examples

```python
# Get document content and download as PDF (attached to chat)
get_document_by_name(
    name="My Document",
    download=True,
    export_format="application/pdf"
)

# Get document by ID and download as DOCX
get_document_by_id(
    document_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    download=True,
    export_format="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Get document content only (no download)
get_document_by_name(
    name="My Document",
    download=False  # This is the default
)
```

When `download=True`, the file is automatically attached to the chat using `chat.attach_file_content()`, making it available for further processing or analysis. The response includes both the markdown content and download information.

## Prompts

```
Give me a one phrase summary of the Leo document.
```

> It seems there are multiple documents with similar names. Please specify which one you would like a summary of:
>
> * Leo Story Bis
> * Totally not Leo Story
> * Leo Story
>
> Let me know which one to proceed with!

```
Give me a one paragraph summary of the Leo Story
```

> In "Leo Story," Leo, a curious and adventurous house cat, finds himself in the attic seeking refuge from a chaotic household situation caused by a burst water pipe. While exploring the attic, he inadvertently becomes a hero when he encounters a thief attempting to escape on the roof. Leo's brave confrontation with the thief, marked by a hiss and a leap, startles the intruder, leading to his capture by the police. This unexpected adventure not only brings excitement to Leo's otherwise peaceful day but also earns him the gratitude of his family, who were unaware of his courageous act until the police mentioned it.


The AI can parse Document URLs as well.
```
Give me a one phrase summary of https://docs.google.com/...
```

> The document titled "Leo Story" can be summarized in one phrase as:
> **"A cat named Leo inadvertently helps catch a thief while seeking a quiet spot in the attic."**


## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/drive.readonly (used when searching a document by name)
    - https://www.googleapis.com/auth/documents.readonly (used when reading a document by ID)
    - https://www.googleapis.com/auth/drive.file (used when creating / updating a document)
