import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from models import AgentActionPackage, AgentsManifest, AgentVersionInfo
from utils import read_yaml_file


def generate_agents_manifest(
    input_folder: str,
    dest_agents_folder: str,
    published_manifest: dict,
    agent_cli_path: str,
) -> AgentsManifest:
    """
    Generates the manifest file for the agents.

    Parameters:
        input_folder (str): The path to the folder containing prepared gallery agents folders.
        dest_agents_folder (str): Path where to store agent information that is then copied over to S3.
        published_manifest (dict): A dictionary containing the manifest data for the agents.
        agent_cli_path (str): The path to the agent cli file.
    """
    manifest: AgentsManifest = {"agents": {}, "organization": "Sema4.ai"}

    # Load whitelist
    with open('whitelist.json', 'r') as f:
        whitelist = json.load(f)

    print("Input folder: ", input_folder)
    for agent_folder_name in os.listdir(input_folder):
        agent_folder = os.path.join(input_folder, agent_folder_name)

        print("Processing agent: ", agent_folder)
        if not os.path.isdir(agent_folder):
            continue

        is_agent_valid = validate_agent(agent_folder, agent_cli_path)
        if not is_agent_valid:
            continue

        agent_spec_data = read_yaml_file(os.path.join(agent_folder, "agent-spec.yaml"))[
            "agent-package"
        ]["agents"][0]
        agent_name = agent_spec_data["name"]
        agent_version = agent_spec_data["version"]

        if is_agent_published(published_manifest, agent_name, agent_version):
            continue

        with open(os.path.join(agent_folder, "runbook.md")) as file:
            runbook_content = file.read()

        # Determine filters based on whitelist inclusion
        kebab_case_agent_name = to_kebab_case(agent_name)
        filters = []
        for filter_name, filter_data in whitelist.items():
            if kebab_case_agent_name in filter_data.get("agents", []):
                filters.append(filter_name)

        actions = get_actions_info(agent_spec_data["action-packages"])
        base_url = "https://cdn.sema4.ai/gallery/agents/"

        agent_info: AgentVersionInfo = {
            "version": agent_spec_data["version"],
            "description": agent_spec_data["description"],
            "agent_spec": f"{base_url}{kebab_case_agent_name}/{agent_version}/agent-spec.yaml",
            "changelog": f"{base_url}{kebab_case_agent_name}/{agent_version}/CHANGELOG.md",
            "runbook": runbook_content,
            "architecture": agent_spec_data["architecture"],
            "reasoning": agent_spec_data["reasoning"],
            "model": agent_spec_data["model"],
            "knowledge": agent_spec_data["knowledge"],
            "metadata": agent_spec_data["metadata"],
            "action_packages": actions,
        }

        # Copy the interested files to be uploaded in S3
        dest = Path(dest_agents_folder) / kebab_case_agent_name / agent_version
        os.makedirs(dest)

        shutil.copyfile(
            Path(agent_folder) / "agent-spec.yaml", dest / "agent-spec.yaml"
        )
        shutil.copyfile(Path(agent_folder) / "CHANGELOG.md", dest / "CHANGELOG.md")

        manifest["agents"][agent_name] = {
            "name": agent_name,
            "versions": [agent_info],
            "filters": filters
        }

    return manifest


def generate_consolidated_manifest(
    published_manifest: AgentsManifest, update_manifest: AgentsManifest
) -> AgentsManifest:
    """
    Generates a new manifest, by getting the current manifest and updating it with updated agents.

    Args:
        published_manifest: The manifest currently stored in S3.
        update_manifest: The manifest generated as a result of building updated packages.
    """
    # Load whitelist
    with open('whitelist.json', 'r') as f:
        whitelist = json.load(f)

    new_manifest: AgentsManifest = published_manifest.copy()

    for updated_agent_name, updated_agent_info in update_manifest["agents"].items():
        if updated_agent_name not in new_manifest["agents"]:
            new_manifest["agents"][updated_agent_name] = updated_agent_info
            continue

        agent_info = new_manifest["agents"][updated_agent_name]
        versions_info = agent_info.get("versions", [])

        # Always update filters based on current whitelist status
        
        kebab_case_agent_name = to_kebab_case(updated_agent_name)
        filters = []
        for filter_name, filter_data in whitelist.items():
            if kebab_case_agent_name in filter_data.get("agents", []):
                filters.append(filter_name)
        agent_info["filters"] = filters

        # we can only have one compiled version at manifest generation
        updated_agent_version = updated_agent_info["versions"][0]["version"]

        # If agent is not published then add the new version and sort the versions
        if not is_agent_published(
            new_manifest, updated_agent_name, updated_agent_version
        ):
            versions_info.append(updated_agent_info["versions"][0])
            agent_info["versions"] = sorted(versions_info, key=lambda x: x["version"])

    # Update filters for all agents based on current whitelist
    for agent_name, agent_info in new_manifest["agents"].items():
        kebab_case_agent_name = to_kebab_case(agent_name)
        filters = []
        for filter_name, filter_data in whitelist.items():
            if kebab_case_agent_name in filter_data.get("agents", []):
                filters.append(filter_name)
        agent_info["filters"] = filters

    return new_manifest


def get_actions_info(action_packages: list[dict]) -> list[AgentActionPackage]:
    actions = []
    for action in action_packages:
        actions.append(
            {
                "name": action["name"],
                "version": action["version"],
                "whitelist": action.get("whitelist", []),
                "organization": "Sema4.ai",
            }
        )

    return actions


def save_manifest(manifest: AgentsManifest, file_path: str) -> None:
    with open(file_path, "w") as file:
        json.dump(manifest, file, indent=2)


def is_agent_published(published_manifest: dict, agent_name: str, version: str) -> bool:
    manifest_agent_versions = (
        published_manifest.get("agents").get(agent_name, {}).get("versions", [])
    )
    versions = [x.get("version") for x in manifest_agent_versions]

    if version not in versions:
        return False

    return True


def to_kebab_case(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1-\2", text)
    kebab_case = re.sub(r"[\s_]+", "-", text).lower()

    return kebab_case


def validate_agent(agent_folder: str, agent_cli_path: str) -> bool:
    """
    Validate the agent content.

    Parameters:
        agent_folder (str): The path to the agent folder.
        agent_cli_path (str): The path to the agent cli executable.
    """
    command = f'"{agent_cli_path}" validate -j {agent_folder}'
    print(f"Validating agent: {command}")

    try:
        result = subprocess.run(
            command, shell=True, cwd=agent_folder, capture_output=True, text=True
        )

        validation_output = json.loads(result.stdout)
        errors = [error for error in validation_output if error.get("severity") == 1]

        if errors:
            print(f"{agent_folder} -- Agent validation failed. Errors: {errors}")
            return False
    except Exception as e:
        print(f"{agent_folder} -- Agent validation to run. Error: {str(e)}")
        return False

    return True
