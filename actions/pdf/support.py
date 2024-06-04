import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
from models import PDFContent


def _read_text_from_pdf(filename: str, pdf: PDFContent) -> str:
    pages = convert_from_path(filename, dpi=300)

    for page_number, page in enumerate(pages, start=1):
        text = _ocr_image(page)
        pdf.length += len(text)
        pdf.content[page_number + 1] = text


def _ocr_image(image):
    text = pytesseract.image_to_string(image)
    return text


def _get_pdf_content(filename: str):
    reader = PdfReader(filename)
    pdf = PDFContent(pages=len(reader.pages), content={}, length=0)

    for page_number in range(pdf.pages):
        page = reader.pages[page_number]
        text = page.extract_text()
        pdf.length += len(text)
        pdf.content[page_number + 1] = text
    if pdf.length == 0:
        _read_text_from_pdf(filename, pdf)
    return pdf
