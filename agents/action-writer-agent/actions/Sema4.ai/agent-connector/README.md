In Sema4.ai Studio, let your agents talk to each other seamlessly.

## Overview

The Agent Connector allows agents within the Sema4.ai platform to communicate with each other through a simple and
intuitive interface. This connector provides actions to create communication conversations and send messages between agents,
facilitating smooth and efficient inter-agent communication.

Currently supported features:

- Get agents
- Get agent by name
- Get conversations
- Get a conversation
- Create a conversation
- Send a message

## Prompts

```
What agents do i have running?
```

> Here are the agents you currently have running:
> 1. Data Agent Example
> 2. The Ultimate Data Sources Test 


```
Let's talk to "Data Agent Example"
```
> You have the following conversations available with the "Data Agent Example":
> 1. Welcome
> 2. Chat 2

```
Let's say "Hello" to "Welcome"
```

> The "Data Agent Example" responded with: "Hello! How can I assist you today?"
> If you have any specific questions or tasks for this agent, feel free to let me know!

## How It Works

1. **Creating a Communication Conversation**:
    - The `create_conversation` action allows you to create a new conversation for communication with an agent by specifying the
      agent's ID and a user-defined conversation name. This action requires an agent ID and returns a conversation ID
      that can be used for further communication.

2. **Sending Messages**:
    - The `send_message` action enables you to send messages to an agent in a specific conversation. You need to provide 
      the conversation ID, agent ID, and the message content. The action returns the agent's response or an error message
      if the operation fails.

3. **Authentication**:
    - When running in cloud environments (HTTPS), the connector uses Bearer token authentication with the provided API key.
    - For local development (HTTP), no authentication is required. Use "LOCAL" as the API key value.

By using these actions, agents within the Sema4.ai platform can effectively communicate, enabling seamless collaboration
and information exchange.

Let your agents talk to each other!