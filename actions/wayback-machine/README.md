# Wayback Machine

Action Package to detect changes to websites using the Wayback Machine.

This action package is used by the Wayback Machine Agent, which helps users analyze changes on a website over time. Whether you want to see how a competitor's website has evolved, what new messaging they have adopted, or how their website structure has changed, this agent can provide those insights. It utilizes the Wayback Machine to access historical versions of websites and Google to fetch current content for comparison. Note that the Wayback Machine can take some time to process, so patience is required. For detailed documentation, refer to the provided link: [Wayback Machine Agent](https://github.com/Sema4AI/cookbook/tree/main/agents/wayback-machine-agent).

The Wayback Machine action package provides endpoints for retrieving archived URLs and snapshots of a website from the Wayback Machine. These endpoints allow users to specify a website and a number of days to look back, returning a list of archived URLs or snapshots available within that timeframe.

## Prompts

`How has competitor.com changed over the last 60 days?`

> _... summarizes the changes and shows the results based on archived data from the Wayback Machine_

`List all the snapshots of example.com from the last 30 days.`

> _... returns a list of all available snapshots of the specified website from the last 30 days_

## Authorization

Uses publicly available data - no need for API keys.