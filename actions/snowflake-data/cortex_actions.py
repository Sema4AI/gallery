import os

import requests
import snowflake.core.cortex.inference_service._generated.models as inference_models
from sema4ai.actions import Response, Secret, action
from snowflake.core import Root
from snowflake.core.cortex.lite_agent_service._generated.models import (
    AgentRunRequest,
    Message,
    Tool,
    ToolToolSpec,
)
from utils import execute_query, get_snowflake_connection, is_running_in_spcs

@action
def cortex_llm_complete(model: str, prompt: str) -> Response[list]:
    """
    Completes the inference for the provided message.

    Args:
        model: The model to use
        prompt: The prompt to use

    Returns:
        List of events.
    """

    with get_snowflake_connection() as conn:
        cortex_inference = Root(conn).cortex_inference_service
        req = inference_models.CompleteRequest(
            model=model, messages=[{"role": "user", "content": prompt}]
        )

        # TODO: Add tools once they are supported
        inference_result = cortex_inference.complete(req)

        events_dict = [
            {"event": event.event, "data": event.data}
            for event in inference_result.events()
        ]

        return Response(result=events_dict)


@action
def cortex_agent_chat(
    query: str, service: Secret, semantic_model_file: Secret
) -> Response[list]:
    """
    Chat with the cortex agent.

    Args:
        query: The query to use
        service: The search service to use
        semantic_model_file: The path to a Snowflake Stage containing the semantic model file

    Returns:
        The chat result.
    """
    with get_snowflake_connection() as conn:
        cortex_agent = Root(conn).cortex_agent_service
        req = AgentRunRequest(
            model="mistral-large2",
            messages=[Message(role="user", content=[{"type": "text", "text": query}])],
            tools=[
                Tool(tool_spec=ToolToolSpec(type="cortex_search", name="search1")),
                Tool(
                    tool_spec=ToolToolSpec(
                        type="cortex_analyst_text_to_sql", name="analyst1"
                    )
                ),
            ],
            tool_resources={
                "analyst1": {"semantic_model_file": semantic_model_file.value},
                "search1": {"name": service.value},
            },
        )
        inference_result = cortex_agent.Run(req)

        events_dict = [
            {"event": event.event, "data": event.data}
            for event in inference_result.events()
        ]

        return Response(result=events_dict)
