In Sema4.ai Studio, let your agents talk to each other seamlessly.

## Overview

The Agent Connector allows agents within the Sema4.ai platform to communicate with each other through a simple and
intuitive interface. This connector provides actions to create communication conversations and send messages between agents,
facilitating smooth and efficient inter-agent communication.

## Quick Start

The easiest way to interact with agents is using the `ask_agent` function:

> Ask the Marketing Agent for a 10-word description of Studio

## Available Actions

**Primary Interface:**
- `ask_agent()` - The simplest way to ask an agent a question by name

**Agent Management:**
- Get all agents
- Get agent by name (with intelligent suggestions if not found)

**Conversation Management:**
- Get conversations for an agent
- Get a specific conversation
- Create a conversation
- Send a message to existing conversation

**Work Items:**
- Create a Work Item for an agent by name
- Create multiple Work Items in a single batch call
- Get the current conversation ID (for passing back to a parent agent)

## Example Usage

### Simple Agent Interaction

```
Ask "Data Agent Example" to help me analyze my dataset
```

> The "Data Agent Example" responded: "I'd be happy to help you analyze your dataset! Could you please provide more details about the data you're working with?"
> 
> Conversation ID: `abc123-def456-ghi789` (use this to continue the conversation)

### Continue a Conversation

```
Ask "Data Agent Example" to explain the previous analysis further
```

> The "Data Agent Example" responded: "Based on our previous analysis, here's a more detailed explanation..."

### Get Available Agents

```
What agents do I have available?
```

> Here are the agents you currently have running:
> 1. Data Agent Example
> 2. The Ultimate Data Sources Test

### Create a Work Item

```
Create a work item for "Invoice Agent" with payload {"invoice_id": "ABC123", "priority": "high"}
```

### Create a Work Item With Attachments

```
Create a work item for "Invoice Agent" with payload {"invoice_id": "ABC123"} and attachments ["/path/to/invoice.pdf", "/path/to/notes.txt"]
```

### Attachments From Chat Files

If an attachment path is not found locally, the action will try to fetch it from the chat files API using the filename (basename). This supports agent inputs that pass relative file names.

```
Create a work item for "Invoice Worker" with payload {"invoice_id": "IN-100017"} and attachments ["ad03f9489278c8e19d01ea5e05ee0aeb.pdf"]
```

### Create Multiple Work Items in One Call

Use `create_work_items_for_agent` to dispatch several items at once. Each entry can have its own message, payload, and attachments:

```
Create work items for "Invoice Agent":
[
  {"message": "Process invoice IN-001", "payload": {"invoice_id": "IN-001"}},
  {"message": "Process invoice IN-002", "payload": {"invoice_id": "IN-002"}, "attachments": ["IN-002.pdf"]}
]
```

The `message` field is automatically merged into the payload so the worker receives it as `payload["message"]`.

### Pass the Current Conversation ID to Worker Agents

When orchestrating workers, use `get_current_conversation_id` to retrieve the calling conversation's ID and include it in the work item payload so workers can send replies back:

```
Get the current conversation ID and create a work item for "Summarizer Agent" with payload {"conversation_id": "<id>", "document": "report.pdf"}
```

### Intelligent Suggestions

If you mistype an agent name, the system will suggest the closest match:

```
Ask "Data Agnet" to help me
```

> Agent 'Data Agnet' not found. Did you mean 'Data Agent Example'?
> Available agents: Data Agent Example, The Ultimate Data Sources Test

## How It Works

### Simple Agent Communication

The `ask_agent` function provides the easiest way to interact with agents:

1. **Automatic Agent Resolution**: Just provide the agent name - the system will find the agent and handle any typos with intelligent suggestions
2. **Conversation Management**: Automatically creates new conversations when needed, or uses existing ones for follow-up messages
3. **Structured Responses**: Returns both the agent's response and conversation ID for easy continuation

### Advanced Usage

For more control, you can also use the individual actions:

1. **Agent Discovery**: Use `get_all_agents` to see available agents or `get_agent_by_name` for specific lookups with suggestions
2. **Conversation Management**: Create conversations manually or retrieve existing ones
3. **Message Sending**: Send messages to specific conversations with full control over the process

### Authentication & API URL

All actions require two Secret parameters:

| Parameter | Description |
|---|---|
| `sema4_api_key` | API key for the Sema4 API. Use `LOCAL` when running in Studio or SDK. |
| `sema4_api_url` | Base URL for the Sema4 API. Use `LOCAL` when running in Studio or SDK. |

- **Cloud Environment**: Provide your API key and the deployment base URL (e.g. `https://your-tenant.sema4.ai`).
- **Snowflake Environment**: Provide the Snowflake endpoint URL — the connector automatically uses `Snowflake Token` authentication and normalises the URL to end with `/api/v1`.
- **Local Development**: Use `LOCAL` for both values — the connector discovers the agent server automatically via environment variable or PID file.

### Intelligent Features

- **Name Suggestions**: If you mistype an agent name, the system suggests the closest match
- **Error Handling**: Clear error messages with available agent names when agents aren't found
- **Conversation Continuity**: Easy follow-up messages using returned conversation IDs

Let your agents talk to each other seamlessly!