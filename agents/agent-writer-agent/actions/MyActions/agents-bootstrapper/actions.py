import base64
import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urljoin

import black
import requests
from refresh_agent_spec_helper import update_agent_spec
from sema4ai.actions import action

AGENTS_DIR_PATH = Path.home() / "agents_bootstrapper"
ACTIONS_GITHUB_URL = "https://api.github.com/repos/Sema4AI/gallery/contents/actions"
SEMA4AI_ACTIONS = "Sema4.ai"
MY_ACTIONS = "MyActions"


@action
def bootstrap_agent_package(agent_name: str) -> str:
    """
    This action sets up an agent package in the home directory of the user under the "agents_bootstrapper" folder.

    Args:
        agent_name: Name of the agent package

    Returns:
        The full path of the bootstrapped agent package.
    """
    AGENTS_DIR_PATH.mkdir(parents=True, exist_ok=True)

    command = f"agent-cli project new --path '{agent_name}'"
    subprocess.run(command, shell=True, check=True, cwd=str(AGENTS_DIR_PATH))

    return f"Agent successfully bootstrapped! Code available at {str(AGENTS_DIR_PATH / agent_name)}"


@action
def open_agent_code(agent_name: str) -> str:
    """
    This action opens the code of the agent package with VSCode.

    Args:
        agent_name: Name of the agent package

    Returns:
        A message indicating success or detailed error information.
    """

    full_agent_path = AGENTS_DIR_PATH / agent_name

    if not os.path.exists(full_agent_path):
        return f"Error: agent package '{agent_name}' does not exist at path {full_agent_path}."

    command = ["code", str(full_agent_path)]

    try:
        subprocess.run(command, check=True)
    except Exception as e:
        return f"Unexpected error: {str(e)}. " "Please check your setup and try again."

    return f"{agent_name} code opened with VSCode."


@action
def refresh_agent_package_spec(agent_name: str) -> None:
    """
    Refreshes the agent-spec.yaml file in the agent package with the latest changes.

    Args:
        agent_name: Name of the agent package
    """
    return update_agent_spec(AGENTS_DIR_PATH / agent_name / "agent-spec.yaml")


@action
def list_available_prebuilt_actions() -> list[str]:
    """
    List all folders (actions) inside the 'actions' directory of the repository.

    Returns:
        A list of folder names representing actions.
    """
    response = requests.get(ACTIONS_GITHUB_URL)
    if response.status_code == 200:
        data = response.json()
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return folders
    else:
        return []


@action
def read_prebuild_action_capabilities(action_name: str) -> str:
    """
    Read the capabilities of a prebuild action package that is available in Github.

    Args:
        action_name: Name of the action package

    Returns:
        A message indicating the capabilities of the action package.
    """
    readme_url = f"{ACTIONS_GITHUB_URL}/{action_name}/README.md"
    response = requests.get(readme_url)
    if response.status_code == 200:
        data = response.json()
        if "content" in data:
            import base64

            readme_content = base64.b64decode(data["content"]).decode("utf-8")
            return readme_content
        else:
            return "README.md file is empty or not available in the expected format."
    else:
        return f"Unable to fetch README.md. Status Code: {response.status_code}, error: {response.text}"


def download_file(url, save_path):
    """
    Downloads a file from the given URL and saves it to the specified path.

    Args:
        url: The URL of the file.
        save_path: The local path to save the file.
    """
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
    else:
        print(f"Failed to download file: {url}. Status Code: {response.status_code}")


def download_folder(url: str, local_path: Path) -> str:
    """
    Downloads all files and subdirectories in a GitHub folder recursively to the right agent location.

    Args:
        action_name: The action directory name that you want to download from Github.
        agent_name: The agent name where the action will be downloaded.
    """
    response = requests.get(url)

    if response.status_code == 200:
        contents = response.json()
        local_path.mkdir(parents=True, exist_ok=True)

        for item in contents:
            if item["type"] == "file":
                download_file(item["download_url"], local_path / item["name"])
            elif item["type"] == "dir":
                download_folder(item["url"], local_path / item["name"])
    else:
        return f"Failed to download action: {url}. Status Code: {response.status_code}, message: {response.text}"

    return "Action downloaded successfully."


@action
def download_prebuilt_action(action_name: str, agent_name: str) -> str:
    """
    Downloads a prebuilt action package from Github to the specified agent package.
    This method requires an agent to be bootstrapped first.

    Args:
        action_name: Name of the action package
        agent_name: Name of the agent package

    Returns:
        A message indicating success or detailed error information.
    """
    agent_path = AGENTS_DIR_PATH / agent_name
    if not agent_path.exists():
        return (
            f"Error: agent package '{agent_name}' does not exist at path {agent_path}."
        )

    url = f"{ACTIONS_GITHUB_URL}/{action_name}"
    sema4_actions_path = agent_path / "actions" / SEMA4AI_ACTIONS / action_name

    return download_folder(url, sema4_actions_path)


def get_sema4_ai_studio_url_for_agent_zip_path(path: str) -> str:
    dl_app_protocol_uri = "sema4.ai.studio"
    dl_app_protocol_uri_full = f"{dl_app_protocol_uri}://"

    dl_app_controller_vscode = "vscode.sema4.ai"
    dl_app_base_uri_controller_vscode = (
        f"{dl_app_protocol_uri_full}{dl_app_controller_vscode}/"
    )

    dl_api_id_import_agent_package_from_zip = "import-agent/zip-path/"

    encoded_path = base64.b64encode(path.encode("utf-8")).decode("utf-8")
    return urljoin(
        dl_app_base_uri_controller_vscode,
        f"{dl_api_id_import_agent_package_from_zip}{encoded_path}",
    )


@action
def publish_to_sema4_ai_studio(agent_name: str) -> None:
    """
    Publishes the agent package to Sema4 AI Studio.

    Args:
        agent_name: Name of the agent package
    """
    agent_dir = str(AGENTS_DIR_PATH / agent_name)
    command = f"agent-cli package build --overwrite --input-dir {agent_dir} --output-dir {agent_dir}"
    subprocess.run(command, shell=True, check=True, cwd=str(AGENTS_DIR_PATH))

    zip_path = AGENTS_DIR_PATH / agent_name / "agent-package.zip"
    if not zip_path.is_file() or zip_path.suffix != ".zip":
        raise ValueError("The provided path is not a zip file.")

    base64_zip_path = base64.urlsafe_b64encode(str(zip_path).encode("utf-8")).decode(
        "utf-8"
    )
    url = f"sema4.ai.studio://vscode.sema4.ai/import-agent/zip-path/{base64_zip_path}"

    webbrowser.open(url)

    return


@action
def bootstrap_action_package(agent_name: str, action_package_name: str) -> str:
    """
    This action sets up an action package in the home directory of the user under the "actions_bootstrapper" folder.

    Args:
        agent_name: Name of the agent package
        action_package_name: Name of the action package

    Returns:
        The full path of the bootstrapped action package.
    """

    new_action_package_path = (
        AGENTS_DIR_PATH / agent_name / "actions" / MY_ACTIONS / action_package_name
    )
    new_action_package_path.mkdir(parents=True, exist_ok=True)

    command = f"action-server new --name '{action_package_name}' --template minimal"
    subprocess.run(command, shell=True, cwd=str(new_action_package_path.parent))

    return f"Action successfully bootstrapped! Code available at {str(new_action_package_path)}"


@action
def update_action_package_dependencies(
    agent_name: str, action_package_name: str, action_package_dependencies_code: str
) -> str:
    """
    Update the action package dependencies (package.yaml) for
    a specified action package.

    Args:
        agent_name: Name of the agent package.
        action_package_name: The name of the action package.
        action_package_dependencies_code: The YAML content to
            write into the package.yaml file.

    Returns:
        A success message.
    """

    package_yaml_path = (
        AGENTS_DIR_PATH
        / agent_name
        / "actions"
        / MY_ACTIONS
        / action_package_name
        / "package.yaml"
    )

    package_yaml = open(package_yaml_path, "w")
    try:
        package_yaml.write(action_package_dependencies_code)
    finally:
        package_yaml.close()

    return f"Successfully updated the package dependencies at: {package_yaml_path}"


@action
def update_action_code(
    agent_name: str, action_package_name: str, action_code: str
) -> str:
    """
    Replaces actions.py content with the provided input.

    Args:
        agent_name: The name of the agent package
        action_package_name: The directory for the action to update
        action_code: The source code to place into the actions.py

    Returns:
        A success message.
    """

    # Format the code using black
    formatted_code = black.format_str(action_code, mode=black.FileMode())

    actions_py_path = (
        AGENTS_DIR_PATH
        / agent_name
        / "actions"
        / MY_ACTIONS
        / action_package_name
        / "actions.py"
    )

    actions_py = open(actions_py_path, "w")
    try:
        actions_py.write(formatted_code)
    finally:
        actions_py.close()

    return f"Successfully updated the actions at {actions_py_path}"
