# YouTube Actions

Action Package to interact with Youtube.

## Authentication

Uses only publicly available API's no need for API keys.

## Actions

The following actions are contained with this package:

### get_transcript
Extracts the transcription of a Youtube video. Works for videos with subtitles or captions.

## Examples

Create an agent that has a runbook to generate summaries and extract highlights of videos, like this:

You help user to extract relevant points from the youtube videos. Follow this runbook everytime you get a youtube video link:

1. Fetch the transcription of the video using tools you have
2. Summarize the video content in max 4 bullet points - focus on the key talking points and highlights
3. Based on your knowledge of our business and products (description below), provide 1-3 highlights of what the product and sales team can learn from the video, and use in the discussions with customers
4. Provide one tweet sample how company's marketing team could share the video so that it connects the content with Sema4.ai business. Make it very specific, and link to a product or feature described below. Include a link to the video

Structure your response like this:

*Summary of the video*
_- bullet 1
_- bullet 2
_- bullet 3
_- bullet 4

*Highlights for the company*
- bullet 1
- bullet 2 (optional)
- bullet 3 (optional)

*Tweet*
(text here)

*Description of company's business and products:*
Add your own data here