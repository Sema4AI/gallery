In Sema4.ai Studio, let your agents talk to each other seamlessly.

## Overview

The Agent Connector allows agents within the Sema4.ai platform to communicate with each other through a simple and
intuitive interface. This connector provides actions to create communication threads and send messages between agents,
facilitating smooth and efficient inter-agent communication.

Currently supported features:

- Get agents
- Get agent by name
- Get threads
- Get a thread
- Create a thread
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
> You have the following threads available with the "Data Agent Example":
> 1. Welcome
> 2. Chat 2

```
Let's say "Hello" to "Welcome"
```

> The "Data Agent Example" responded with: "Hello! How can I assist you today?"
> If you have any specific questions or tasks for this agent, feel free to let me know!

## How It Works

1. **Creating a Communication Thread**:
    - The `create_thread` action allows you to create a new thread for communication with an agent by specifying the
      agent's name and a user-defined thread name. This action internally fetches the list of available agents and
      validates the agent name before creating the thread.

2. **Sending Messages**:
    - The `send_message` action enables you to send messages within a specified thread and retrieve the assistant's
      response. This action ensures smooth communication by providing only the relevant content of the response or an
      error message if the operation fails.

By using these actions, agents within the Sema4.ai platform can effectively communicate, enabling seamless collaboration
and information exchange.In Sema4.ai Desktop let your agents talk to each other.

## Caveats

- Agent API is not GA, and is likely to change before release. This action package is experimental and only for demos.
