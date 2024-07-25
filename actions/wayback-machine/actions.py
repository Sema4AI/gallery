"""A simple AI Action template for comparing timezones.

Please checkout the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions#readme
"""

from datetime import datetime

import pytz
from sema4ai.actions import action
from waybackpy import WaybackMachineCDXServerAPI
from datetime import datetime, timedelta


@action
def get_wayback_changes(url: str, days: int) -> str:
    """Uses the Wayback Machine to get a comma-seperated list of archive URLs for a given website within the number of days from today.

    Args:
        url: Website to check for changes
            Example: "https://sema4.ai"
        days: Number of days to go back looking for changes
            Example: "7"

    Returns:
        A comma-seperated list of urls for each Wayback Machine archive available within the number of days from today.
    """
    user_agent = "Sema4.ai Studio"
    cdx_api = WaybackMachineCDXServerAPI(url, user_agent)
    end_date = datetime.now()
    start_date = end_date - timedelta(days)
    start_archive = cdx_api.near(
        year=start_date.year,
        month=start_date.month,
        day=start_date.day,
        hour=start_date.hour,
        minute=start_date.minute,
    )
    end_archive = cdx_api.near(
        year=end_date.year,
        month=end_date.month,
        day=end_date.day,
        hour=end_date.hour,
        minute=end_date.minute,
    )
    print(start_archive.archive_url)
    print(end_archive.archive_url)
    return ",".join([start_archive.archive_url, end_archive.archive_url])


@action
def get_wayback_snapshots(url: str, days: int) -> str:
    """Gets a list of snapshots from the Wayback Machine for a given website and number of days from today.

    Args:
        url: Website to check for changes
            Example: "https://sema4.ai"
        days: Number of days to go back looking for changes
            Example: "7"

    Returns:
        A comma-seperated list of urls for each Wayback Machine website snaphost available within the number of days from today.
    """
    # Get the current date and the date one week ago
    end_date = datetime.now()
    start_date = end_date - timedelta(days)

    # Format dates in the required format for Wayback Machine (YYYYMMDDHHMMSS)
    start_date_str = start_date.strftime("%Y%m%d%H%M%S")
    end_date_str = end_date.strftime("%Y%m%d%H%M%S")

    # Initialize the Wayback Machine CDX Server API
    cdx = WaybackMachineCDXServerAPI(url, start_date_str, end_date_str)

    # Get the list of snapshots within the date range
    snapshots = cdx.snapshots()

    for snapshot in snapshots:
        print(snapshot.archive_url)
    return ",".join(list(snapshots))
