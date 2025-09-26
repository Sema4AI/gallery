# Example Web Search

> **⚠️ DISCLAIMER: This is a demonstration and example action package only. It is not intended for production use and should only be used for learning, testing, and educational purposes.**

Action Package demonstrating web search integration using the Sema4.ai demo API, providing structured access to web search results without requiring API keys or complex setup.

This package showcases how to extract and structure various types of search data including organic results, knowledge graph information, places, people-also-ask questions, and related searches from web search engines.

## Features

- **Organic Search Results**: Get traditional search results with titles, links, snippets, and positions
- **Knowledge Graph**: Access structured information about entities, including titles, types, websites, and attributes
- **Places**: Retrieve location-based results with addresses and place identifiers
- **People Also Ask**: Get related questions and their answers that appear in search results
- **Related Searches**: Discover additional search queries related to your original query
- **Structured Data**: All results are returned as well-defined Pydantic models for easy integration

## Prompts

```
Search for "artificial intelligence trends 2024" and return 5 results.
```

> The search for "artificial intelligence trends 2024" has been completed successfully. Here are the structured results:
>
> **Organic Results:**
> 1. "AI Trends 2024: What to Expect" - https://example.com/ai-trends-2024
> 2. "Top 10 AI Developments This Year" - https://example.com/ai-developments
> ...
>
> **Knowledge Graph:**
> - Title: Artificial Intelligence
> - Type: Technology
> - Website: https://en.wikipedia.org/wiki/Artificial_intelligence
>
> **People Also Ask:**
> - "What are the biggest AI trends in 2024?"
> - "How will AI change in 2024?"

```
Find information about "Tesla stock price" and show me 3 results with knowledge graph data.
```

> The search for "Tesla stock price" has been completed. Here are the key results:
>
> **Knowledge Graph:**
> - Title: Tesla, Inc.
> - Type: Public Company
> - Website: https://tesla.com
> - Current Stock Price: $XXX.XX
>
> **Organic Results:**
> 1. "Tesla Stock (TSLA) - Real-time Quotes" - https://finance.yahoo.com/quote/TSLA
> 2. "Tesla Stock Analysis and Price Target" - https://example.com/tesla-analysis
> 3. "TSLA Stock News and Updates" - https://example.com/tesla-news

```
Search for "best restaurants in San Francisco" and get 5 results including places.
```

> The search for "best restaurants in San Francisco" has been completed with location-based results:
>
> **Places:**
> 1. "The French Laundry" - 6640 Washington St, Yountville, CA
> 2. "Gary Danko" - 800 N Point St, San Francisco, CA
> 3. "State Bird Provisions" - 1529 Fillmore St, San Francisco, CA
>
> **Organic Results:**
> 1. "Top 10 Restaurants in San Francisco" - https://example.com/sf-restaurants
> 2. "Michelin Guide San Francisco" - https://example.com/michelin-sf
> ...

## API Details

- **Endpoint**: Uses Sema4.ai demo API at `demo-services.sema4ai.dev`
- **Authentication**: No API key required (demo service)
- **Rate Limits**: Subject to demo service limitations
- **Data Format**: Returns structured JSON with Pydantic models

## Response Structure

The search action returns a `SearchResult` object containing:
- `searchParameters`: Original search parameters used
- `knowledgeGraph`: Entity information from the knowledge graph
- `organic`: List of traditional search results
- `places`: Location-based results with addresses
- `peopleAlsoAsk`: Related questions and answers
- `relatedSearches`: Additional search suggestions
- `credits`: Number of API credits consumed

## Caveats

- This is a demo package using Sema4.ai's demo API service
- Results may be limited or filtered compared to direct web search APIs
- No authentication required, but subject to demo service availability
- Structured for educational and demonstration purposes