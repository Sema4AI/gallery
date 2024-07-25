import sys
import time
from pathlib import Path

from sema4ai.actions import action
import os
import urllib.parse
import subprocess
import socket
import requests
import black


@action
def bootstrap_action_package(action_package_name: str) -> str:
    """
    This action sets up an action package in the home directory of the user under the "actions_bootstrapper" folder.

    Args:
        action_package_name: Name of the action package

    Returns:
        The full path of the bootstrapped action package.
    """
    home_directory = os.path.expanduser("~")

    new_action_package_path = os.path.join(home_directory, "actions_bootstrapper")

    os.makedirs(new_action_package_path, exist_ok=True)

    command = f"action-server new --name '{action_package_name}' --template minimal"
    subprocess.run(command, shell=True, cwd=new_action_package_path)

    full_action_path = get_action_package_path(action_package_name)

    return f"Action successfully bootstrapped! Code available at {full_action_path}"


def find_available_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except socket.error:
                port += 1


def get_action_package_path(action_package_name: str) -> str:
    home_directory = os.path.expanduser("~")

    new_action_package_path = os.path.join(home_directory, "actions_bootstrapper")

    full_action_path = os.path.join(new_action_package_path, action_package_name)

    return full_action_path


@action
def update_action_package_dependencies(
    action_package_name: str, action_package_dependencies_code: str
) -> str:
    """
    Update the action package dependencies (package.yaml) for
    a specified action package.

    Args:
        action_package_name: The name of the action package.
        action_package_dependencies_code: The YAML content to
            write into the package.yaml file.

    Returns:
        A success message.
    """

    package_yaml_path = os.path.join(
        os.path.expanduser("~"),
        "actions_bootstrapper",
        action_package_name,
        "package.yaml",
    )

    package_yaml = open(package_yaml_path, "w")
    try:
        package_yaml.write(action_package_dependencies_code)
    finally:
        package_yaml.close()

    return f"Successfully updated the package dependencies at: {package_yaml_path}"


@action
def update_action_package_action_dev_data(
    action_package_name: str,
    action_package_action_name: str,
    action_package_dev_data: str,
) -> str:
    """
    Update the action package dev data for a specified action package.

    Args:
        action_package_name: The name of the action package.
        action_package_action_name: The name of the action for which the devdata is intended
        action_package_dev_data: The JSON content to write into the dev data for this specific action

    Returns:
        Whether the dev data was successfully updated or not.

    """

    full_action_path = get_action_package_path(action_package_name)

    dev_data_path = os.path.join(full_action_path, "devdata")

    os.makedirs(dev_data_path, exist_ok=True)

    file_name = f"input_{action_package_action_name}.json"
    file_path = os.path.join(dev_data_path, file_name)

    with open(file_path, "w") as file:
        try:
            file.write(action_package_dev_data)
        finally:
            file.close()

    return f"dev data for {action_package_action_name} in the action package {action_package_name} successfully created!"


@action
def start_action_server(action_package_name: str, secrets: str) -> str:
    """
    This action starts the bootstrapped action package.

    Args:
        action_package_name: Name of the action package
        secrets: A JSON dictionary where each key is the secret name and the value is the secret value

    Returns:
        The address of the running action package.
    """

    print(f"Starting action server for package: {action_package_name}")

    full_action_path = get_action_package_path(action_package_name)
    print(f"Full action package path: {full_action_path}")

    if not os.path.exists(full_action_path):
        print(f"Action package '{full_action_path}' does not exist.")
        return f"Action package '{full_action_path}' does not exist."

    start_port = 8080
    available_port = find_available_port(start_port)
    print(f"Found available port: {available_port}")

    # Command to start the server using the script
    script_path = Path(__file__).parent / "start_action_server.py"
    start_command = [
        sys.executable, str(script_path),
        str(full_action_path), str(available_port), secrets
    ]
    print(f"Start command: {start_command}")

    process = subprocess.Popen(
        start_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    print("Subprocess started.")

    timeout = 60
    start_time = time.time()
    url = f"http://localhost:{available_port}"

    time.sleep(1.0)
    log_path = Path(full_action_path) / "action_server.log"
    print(f"Log path: {log_path}")

    while True:
        if time.time() - start_time > timeout:
            stop_action_server(url)
            stdout_content = process.stdout.read().decode() if process.stdout else ""
            stderr_content = process.stderr.read().decode() if process.stderr else ""
            print("Process timed out.")
            print("Stdout:")
            print(stdout_content)
            print("Stderr:")
            print(stderr_content)
            return f"Process timed out.\n\nStdout:\n{stdout_content}\n\nStderr:\n{stderr_content}"
        if log_path.exists():
            with open(log_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if url in line:
                        print(f"Action Server started at {url}")
                        return f"Action Server started at {url}"
                    if "Error executing action-server" in line:
                        stdout_content = process.stdout.read().decode() if process.stdout else ""
                        stderr_content = process.stderr.read().decode() if process.stderr else ""
                        print("Failed to start.")
                        print("Stdout:")
                        print(stdout_content)
                        print("Stderr:")
                        print(stderr_content)
                        return f"Failed to start.\n\nStdout:\n{stdout_content}\n\nStderr:\n{stderr_content}"
        time.sleep(1.0)
        print("Process exit status: {process.poll()}")
        print("Checking log file...")


@action
def stop_action_server(action_server_url: str) -> str:
    """
    This action shutdowns the running action package.

    Args:
        action_server_url: URL of the running action package

    Returns:
        Whether the shutdown was successful or not
    """

    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(f"{action_server_url}/api/shutdown", headers=headers)
    except requests.exceptions.ConnectionError:
        return "Could not connect to the server"

    if response.status_code == 200:
        return "Successfully shutdown the action server"
    else:
        print("POST request failed.")
        print("Status code:", response.status_code)
        print("Response content:", response.text)
        return "Failed to stop the action server"


@action
def update_action_code(action_package_name: str, action_code: str) -> str:
    """
    Replaces actions.py content with the provided input.

    Args:
        action_package_name: The directory for the action to update
        action_code: The source code to place into the actions.py

    Returns:
        A success message.
    """

    # Format the code using black
    formatted_code = black.format_str(action_code, mode=black.FileMode())

    actions_py_path = os.path.join(
        os.path.expanduser("~"),
        "actions_bootstrapper",
        action_package_name,
        "actions.py",
    )

    actions_py = open(actions_py_path, "w")
    try:
        actions_py.write(formatted_code)
    finally:
        actions_py.close()

    return f"Successfully updated the actions at {actions_py_path}"


@action
def open_action_code(action_package_name: str) -> str:
    """
    This action opens the code of the action package with VSCode.

    Args:
        action_package_name: Name of the action package

    Returns:
        A message indicating success or detailed error information.
    """

    full_action_path = get_action_package_path(action_package_name)

    if not os.path.exists(full_action_path):
        return f"Error: Action package '{action_package_name}' does not exist at path {full_action_path}."

    command = ["code", full_action_path]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        return (
            f"Error: Failed to open the action package '{action_package_name}' with VSCode. "
            f"Subprocess returned non-zero exit status {e.returncode}. "
            "Ensure VSCode is installed and the 'code' command is available in your PATH."
        )
    except FileNotFoundError:
        return (
            "Error: 'code' command not found. "
            "Ensure VSCode is installed and the 'code' command is available in your PATH."
        )
    except Exception as e:
        return (
            f"Unexpected error: {str(e)}. "
            "Please check your setup and try again."
        )

    return f"{action_package_name} code opened with VSCode."


@action
def get_action_run_logs(action_server_url: str, run_id: str) -> str:
    """
    Returns action run logs in plain text by requesting them from the
    provided action server URL.

    Args:
        action_server_url: The URL (base path) to the action server.
        run_id: The ID of the run to fetch logs for.

    Returns:
        The plain text from the output logs of the run.
    """

    artifact = "__action_server_output.txt"

    target_url = urllib.parse.urljoin(
        action_server_url,
        f"/api/runs/{run_id}/artifacts/text-content?artifact_names={artifact}",
    )

    response = requests.get(target_url)

    payload = response.json()
    output = payload[artifact]

    return output


@action
def get_action_run_logs_latest(action_server_url: str) -> str:
    """
    Returns action run logs in plain text by requesting them from the
    provided action server URL. Requests the latest run's logs.

    Args:
        action_server_url: The URL (base path) to the action server.

    Returns:
        The plain text from the output logs of the run.
    """

    runs_list_url = urllib.parse.urljoin(action_server_url, "/api/runs")

    runs_response = requests.get(runs_list_url)
    runs_payload = runs_response.json()

    last_run = runs_payload[-1]

    return get_action_run_logs(action_server_url, last_run["id"])
