# Microsoft Teams

Action package for interaction with Microsoft Teams resources.

Currently capable of:  

- **Listing the details of Teams that the user has joined.**
- **Searching for Teams by name.**
- **Listing members and channels of a Team.**
- **Searching for users.**
- **Posting messages in channels.**
- **Creating new Teams.**
- **Adding members to Teams.**
- **Creating one-on-one and group chats and sending messages to them.**
- **Getting messages from a specific channel.**
- **Getting replies to a specific message in a channel.**
- **Replying to a specific message in a channel.**


## Prompt Examples

```
Create a new chat with Tommi, and send a message "Yo, greetings from my Teams Agent!"
```

>A new chat has been created with Tommi, and the message "Yo, greetings from my Teams Agent!" has been sent.

```
Create a Team "Agent Testing"
```

>The team "Agent Testing" has been created successfully. If you need any further assistance, feel free to ask!

```
Post "Hello" to that team's general channel
```

>The message "Hello" has been posted to the General channel of the "Agent Testing" team. If you need any further assistance, feel free to ask! 

## Authorization

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/actions/auth/microsoft).

Currently the Actions in this package use the following scopes.

    - Channel.ReadBasic.All
    - ChannelMessage.Send
    - ChannelMessage.Read.All
    - Chat.Create
    - ChatMessage.Send
    - Group.Read.All
    - GroupMember.ReadWrite.All
    - Team.Create
    - Team.ReadBasic.All
    - TeamMember.Read.All
    - User.Read.All
