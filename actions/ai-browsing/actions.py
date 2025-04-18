"""Set of actions for AI-powered web browsing automation.

Currently supporting:
- Automated web browsing with AI agent
- Scraping web page content and elements
- Form filling and interaction
- File downloads
- Integration with OpenAI and Anthropic LLMs
- Structured output generation
"""

from sema4ai.actions import action, Response, ActionError, Secret
import asyncio
import json
import re
from dotenv import load_dotenv
import os
import random
from browser_use import Agent, Controller, Browser, BrowserConfig, BrowserContextConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import TypeVar, Optional, Union

from pathlib import Path

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env", override=True)

T = TypeVar('T', bound=BaseModel)

def extract_json_from_text(text: str) -> dict:
    """
    Extract JSON from text that might contain additional content.

    Args:
        text: Text that might contain JSON

    Returns:
        Extracted JSON as a dictionary
    """
    # Try to find JSON objects in the text
    json_pattern = r'\{[^{}]*\}'
    matches = re.finditer(json_pattern, text)

    # Try each potential JSON match
    for match in matches:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            continue

    # If no valid JSON found, try parsing the entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ActionError(f"Could not find valid JSON in the response: {str(e)}")


@action
def perform_browser_task(
    task_description: str,
    url: str,
    openai_api_key: Secret,
    source_data: Optional[str],
    output_model: Optional[str] = None,
    headless: bool = True,
    timeout: int = 300,
    cookies_file: Optional[str] = None
) -> Response[Union[str, T]]:
    """
    Perform a browser task with the given task description, URL, and optional source data.

    Use `input_data` if possible to prevent multiple calls to pass the same data to the same task (url).

    Args:
        task_description: the description of the task to perform
        url: the URL of the website to browse
        openai_api_key: the OpenAI API key
        source_data: Optional source data to be used during the task execution. Given as JSON string.
                   When a list is provided, the task will be executed separately for each item in the list.
                   Examples:
                   - List of strings: ["item1", "item2", "item3"]
                   - Single dictionary: {"username": "john", "password": "secret"}
                   - List of dictionaries: [{"name": "John", "email": "john@example.com"},
                                          {"name": "Jane", "email": "jane@example.com"}]
        output_model: Optional string description to structure the output.
                     Example: "list of name(str) and title(str) combinations"
        headless: whether to run the browser in headless mode (default: True)
        timeout: maximum time in seconds to wait for task completion (default: 300)
        cookies_file: Optional path to a file containing cookies to be used during the task execution.
    Returns:
        The result of the task, either as a string or structured according to the output_model.
    """
    controller = Controller()

    llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key.value if openai_api_key.value else os.getenv("OPENAI_API_KEY"))

    context_config = {
        "user_agent": _get_random_user_agent()
    }
    if cookies_file:
        context_config["cookies_file"] = cookies_file
    browser_configuration = {
        "headless": headless,
		"new_context_config": BrowserContextConfig(**context_config)
    }
    config = BrowserConfig(**browser_configuration)
    browser = Browser(config=config)
    if url == "":
        final_task_description = task_description
    else:
        final_task_description = f"{task_description}. Start by going to this URL (do not deviate from this domain unless otherwise specified): {url}"

    # Add input data to the task description if provided
    if source_data is not None:
        try:
            data_str = json.dumps(source_data, indent=2)
            final_task_description += f"\n\nUse the following input data in the task:\n{data_str}"
        except (TypeError, ValueError) as e:
            raise ActionError(f"Input data must be JSON-serializable: {str(e)}")

    # If output_model is provided, instruct the LLM to return JSON
    if output_model:
        final_task_description += f"\n\nReturn the result as a JSON object that matches this structure: {output_model}"
        final_task_description += "\nReturn ONLY the JSON object, without any additional text or explanation."

    agent = Agent(controller=controller, task=final_task_description, llm=llm, browser=browser)

    def task_executor():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_result = ""
        try:
            print(">>> Starting task executor...")
            # Add timeout for the entire operation
            history = loop.run_until_complete(asyncio.wait_for(agent.run(), timeout=timeout))
            final_result = history.final_result()
        except asyncio.TimeoutError:
            raise ActionError("Task execution timed out")
        except Exception as e:
            raise ActionError(str(e))
        finally:
            print(">>> Exiting task executor.")
            try:
                loop.run_until_complete(browser.close())
            except Exception as e:
                print(f"Warning: Error closing browser: {str(e)}")
            loop.close()
        return final_result
    task_response = task_executor()
    return Response(result=task_response)


def _get_random_user_agent():
    user_agents = [
        # Google Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Mobile Safari/537.36",
        # Mozilla Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Android 13; Mobile; rv:118.0) Gecko/118.0 Firefox/118.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        # Microsoft Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 Edg/117.0.2045.43",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 Edg/117.0.2045.43",
        # Opera
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 OPR/102.0.4880.78",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 OPR/102.0.4880.78",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Mobile Safari/537.36 OPR/102.0.4880.78",
    ]

    return random.choice(user_agents)