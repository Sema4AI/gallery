# YouTube Actions for Sema4.ai Action Server

import re

from sema4ai.actions import Response, action
from youtube_search import YoutubeSearch
from youtube_transcript_api import YouTubeTranscriptApi


def _extract_youtube_id(url):
    # Regular expression patterns to match various YouTube URL formats
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&amp;]+)",  # Matches https://www.youtube.com/watch?v=VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtu\.be/([^?]+)",  # Matches https://youtu.be/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([^?]+)",  # Matches https://www.youtube.com/embed/VIDEO_ID
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([^?]+)",  # Matches https://www.youtube.com/v/VIDEO_ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@action(is_consequential=False)
def search(search_term: str, max_results: int = 3) -> Response[str]:
    """Searches for the YouTube videos with a search keyword.

    Args:
        search_term: A search term for the Youtube video search, example: "Agentic Automation"
        max_results: How many results to return, default 3.

    Returns:
        Youtube video links that match the search criteria. The return value is a json string.
    """
    results = YoutubeSearch(search_term, max_results=max_results).to_json()
    return Response(result=results)


@action(is_consequential=False)
def get_transcript(video_url: str) -> Response[str]:
    """Extracts the transcription of a Youtube video. Only works if subtitles or captions are available for the video.

    Args:
        video_url: Youtube video URL as a complete URL, example: "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

    Returns:
        Complete transcription of the youtube video
    """

    # Extract video ID from the URL
    video_id = _extract_youtube_id(video_url)

    if video_id is None:
        return "Could not extract YouTube video ID from the given URL."

    # Fetching the transcript
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    # Concatenate all text parts to create a full transcript
    transcript = " ".join([entry["text"] for entry in transcript_list])

    return Response(result=transcript)
