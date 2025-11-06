# Serper Action Package

The Serper Action Package provides an interface to interact with the Serper API, allowing you to perform Google searches programmatically. This package includes a single action, `search_google`, which returns a structured summary of search results.

## Features

- Perform Google searches using the Serper API.
- Retrieve structured search results, including knowledge graph, organic results, places, people also ask, and related searches.
- Securely manage API keys using Sema4.ai's Secret management.
- Built-in retry logic with exponential backoff for handling connection failures.

## Installation

- To use this action package, ensure you have the Sema4.ai VSCode extension installed. You can find it [here](https://marketplace.visualstudio.com/items?itemName=sema4ai.sema4ai).
- Create your Serper API key [here](https://serper.dev/).

## Action: `search_google`

### Description

The `search_google` action performs a search using the Serper API and returns a structured summary of the results.

### Parameters

- `q` (str): The search query.
- `num` (int): The number of results to return.
- `api_key` (Secret): The API key for authentication.

### Returns

- `str`: A JSON string containing a structured summary of the search results.

### Example Usage

```python
from sema4ai.actions import action, Secret

@action
def search_google(q: str, num: int, api_key: Secret) -> str:
    # Implementation here
    pass
```

### Pydantic Models

The response from the API is parsed and validated using Pydantic models, ensuring a consistent and structured format.

- `KnowledgeGraph`: Represents the knowledge graph section.
- `OrganicResult`: Represents each organic search result.
- `Place`: Represents each place in the response.
- `PeopleAlsoAsk`: Represents each "people also ask" entry.
- `RelatedSearch`: Represents each related search query.
- `SearchResult`: The main model that includes all sections of the response.

## Setup

1. **API Key**: Store your Serper API key securely using Sema4.ai's Secret management when used in Studio and Control Room.
2. **Test Data**: Use the provided `input_search_google.json` file in the `devdata` folder to test the action.
   - Add your Serper API key to the `api_key` field in the `input_search_google.json` file to run this in VS Code / Cursor.