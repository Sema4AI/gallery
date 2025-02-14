"""
A simple AI Action template showcasing some more advanced configuration features

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions/blob/master/README.md

"""

from sema4ai.actions import action, Response
from models import PDFContent, Matches, Match
from support import _get_pdf_content


@action(is_consequential=False)
def read_text_from_pdf(filename: str) -> Response[PDFContent]:
    """
    Returns text from a PDF file.

    Can be used to extract text from a PDF file and then
    summarize the text, extract keywords, or perform any other
    NLP tasks.

    Args:
        filename: The name of the file to read.

    Returns:
        Text content of the file per page.
    """
    pdf = _get_pdf_content(filename)
    return Response(result=pdf)


@action(is_consequential=False)
def find_text_in_pdf(
    text_to_find: str, filename: str, case_sensitive: bool = False
) -> Response[Matches]:
    """
    Returns the pages where the text was found in the PDF.

    Report to user paragraphs where the text was found in the PDF.

    Args:
        text_to_find: The text to find in the PDF.
        filename: The name of the file to read.
        case_sensitive: Whether the search should be case sensitive (default False)

    Returns:
        Matches found in the PDF.
    """
    pdf = _get_pdf_content(filename)
    matches = Matches(items=[])
    text_find = text_to_find if case_sensitive else text_to_find.lower()
    for page, content in pdf.content.items():
        match_content = content if case_sensitive else content.lower()
        if text_find in match_content:
            match = Match(text={"page": page, "content": content})
            matches.items.append(match)
    return Response(result=matches)
