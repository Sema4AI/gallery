import os
import subprocess

from robocorp.tasks import task
from tools import get_agent_cli
from utils import (
    clear_folders
)

script_dir = os.path.dirname(os.path.abspath(__file__))
dest_folder = os.path.join(script_dir, "demos")


def package_agents(
    input_folder: str,
    dest_folder: str,
    agent_cli_path: str,
) -> str | None:
    """
    Generates the agent zip using agent-cli package build command

    Parameters:
        input_folder (str): The path to the folder containing an agent.
        dest_agents_folder (str): Path where to store agent zip files that will later be pushed to S3.
        agent_cli_path (str): The path to the agent cli executable.

    Returns:
        str | None: Path to the generated agent.zip file if successful, None if failed
    """
    command = f'"{agent_cli_path}" package build --input-dir {input_folder} --output-dir {dest_folder} --name {os.path.basename(input_folder)} --overwrite'
    print(f"Building agent package: {command}")

    try:
        result = subprocess.run(
            command, shell=True, cwd=input_folder, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(
                f"{input_folder} -- Agent package build failed. Error: {result.stderr}"
            )
            return None

        zip_path = os.path.join(dest_folder, f"{os.path.basename(input_folder)}.zip")
        return zip_path
    except Exception as e:
        print(f"{input_folder} -- Agent package build failed to run. Error: {str(e)}")
        return None


@task
def update_demos():
    agent_cli_path = get_agent_cli()

    clear_folders(dest_folder)
    input_folder = os.path.abspath(os.path.join(script_dir, "../../demos"))

    # Package the demo agent to zip package
    zip_path = package_agents(
        input_folder,
        dest_folder,
        agent_cli_path,
    )
    print(f"Built agent package to: {zip_path}")


if __name__ == "__main__":
    update_demos()
