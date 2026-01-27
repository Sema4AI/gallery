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

### Authentication

- **Cloud Environment**: Uses Bearer token authentication with your API key
- **Local Development**: Use "LOCAL" as the API key value (no authentication required)

### Intelligent Features

- **Name Suggestions**: If you mistype an agent name, the system suggests the closest match
- **Error Handling**: Clear error messages with available agent names when agents aren't found
- **Conversation Continuity**: Easy follow-up messages using returned conversation IDs

Let your agents talk to each other seamlessly!