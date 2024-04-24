"""Actions for sending email.
"""

from robocorp.actions import action, Secret

from dotenv import load_dotenv

# NOTE. Recipients should be a comma separated list of email addresses.


@action(is_consequential=False)
def send_email(subject: str, body: str, recipients: str) -> str:
    """Gets the text content, form elements, links and other elements of a website.

    If url ends with .csv then use 'download_file' action.

    Args:
        url (str): URL of the website

    Returns:
        WebPage: Text content, form elements and elements of the website
    """
    pass
