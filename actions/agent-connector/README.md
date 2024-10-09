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
use wayback machine to find how robocorp.com has changed over past 2yrs
```

> **Changes to Robocorp.com Over the Past 2 Years**
> Snapshot from September 1, 2022
>
> ... Content shortened ...
>
> Snapshot from August 13, 2024
>
> ... Content shortened ...
>

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
