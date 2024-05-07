# Slack

In order for the integration to work it requires the following:
* a Slack App with the following OAuth scopes:
  * channels:history 
  * channels:read 
  * chat:write
  * users:read
* The bot needs to be added to the channel before it can access the message history or post a message

Note: the bot can read from public and private groups or dms with appropriate OAuth scopes.  