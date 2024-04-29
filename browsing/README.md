# Browsing

## Required secrets

This action package utilizes Google Custom Search API. The API usage requires the [API key](https://developers.google.com/custom-search/v1/overview#api_key) and
[search engine ID](https://programmablesearchengine.google.com/).

## Actions

The following actions are contained with this package:

### download_file

Download file via URL to local filesystem.

### fill_elements

Fill elements and submit the form.

### get_website_content

Use 'playwright' browser to get information about the web page.

### google_search

Use Google Custom Search API to perform searches.

### web_search_news

Use DuckDuckGO API to search for news.

### web_search_places

Use DuckDuckGO API to use maps search for places.

## Instruction for the Agent

You are a helpful assistant. Forward any text user has placed within quotes directly to the `google_search` action if that action is required.

Pass to `fill_elements` actions output from `get_website_content` embedded with the values to fill in correct elements.
