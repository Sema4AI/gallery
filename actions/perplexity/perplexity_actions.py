import sema4ai_http
from pydantic import BaseModel
from sema4ai.actions import Response, Secret, action


class SearchResult(BaseModel):
    answer: str
    citations: list[str]


@action
def search(api_key: Secret, query: str) -> Response[SearchResult]:
    """
    Search the web for the given query and return the results in the specified format.

    Args:
        api_key: The Perplexity API key.
        query: The query to search for.

    Returns:
        The search results containing an answer and citations with source details.

    """
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise.",
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key.value}",
        "Content-Type": "application/json",
    }

    response = sema4ai_http.post(
        "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
    )

    response.raise_for_status()

    response_json = response.json()

    return Response(
        result=SearchResult(
            answer=response_json["choices"][0]["message"]["content"],
            citations=response_json["citations"],
        )
    )
