"""
Youtube Actions for Sema4.ai Action Server
"""

from sema4ai.actions import action
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_search import YoutubeSearch


@action(is_consequential=False)
def search(search_term: str, max_results: int = 3) -> str:
    """
    Searches for the YouTube videos with a search keyword.

    Args:
        search_term (str): A search term for the Youtube video search, example: "Agentic Automation"
        max_results (int): How many results to return, default 3.

    Returns:
        str: Youtube video links that match the search criteria. The return value is a json string.
    """
    try:
        results = YoutubeSearch(search_term, max_results=max_results).to_json()
        return results
    except Exception as e:
        return f"An error occurred: {str(e)}"

@action(is_consequential=False)
def get_transcript(video_url: str) -> str:
    """
    Extracts the transcription of a Youtube video. Only works if subtitles or captions are available for the video.

    Args:
        video_url (str): Youtube video URL as a complete URL, example: "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

    Returns:
        str: Complete transcription of the youtube video
    """

    # Extract video ID from the URL
    video_id = video_url.split('v=')[1]
    # Handle video URLs with additional parameters after the video ID
    ampersand_position = video_id.find('&')
    if ampersand_position != -1:
        video_id = video_id[:ampersand_position]
    
    try:
        # Fetching the transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Concatenate all text parts to create a full transcript
        transcript = ' '.join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        return f"An error occurred: {str(e)}"
