import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from models import AgentsWhitelistEntry, AgentInfo
from models import AgentActionPackage, AgentsManifest, AgentVersionInfo
from utils import read_yaml_file, calculate_file_hash


def build_agent_package(
    agent_folder: str, agent_name: str, agent_version: str, agent_cli_path: str
) -> tuple[str, str] | None:
    """
    Build an agent package zip file using agent-cli package build command.
    
    Parameters:
        agent_folder (str): The path to the agent folder.
        agent_name (str): The name of the agent.
        agent_version (str): The version of the agent.
        agent_cli_path (str): The path to the agent cli executable.
    
    Returns:
        tuple[str, str] | None: A tuple of (zip_file_path, zip_hash) if successful, None if failed.
    """
    # Create a zips directory in the project root for building packages
    script_dir = os.path.dirname(os.path.abspath(__file__))
    zips_dir = os.path.join(script_dir, "zips")
    os.makedirs(zips_dir, exist_ok=True)
    
    kebab_case_agent_name = to_kebab_case(agent_name)
    zip_filename = f"{kebab_case_agent_name}.zip"
    zip_file_path = os.path.join(zips_dir, zip_filename)
    
    # Build the agent package using agent-cli
    command = [
        agent_cli_path,
        "package",
        "build",
        "--input-dir", agent_folder,
        "--name", zip_filename,
        "--output-dir", zips_dir,
        "--overwrite"
    ]
    
    print(f"Building agent package: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=agent_folder
        )
        
        if result.returncode != 0:
            print(f"Agent package build failed for {agent_name} {agent_version}: {result.stderr}")
            return None
        
        # Check if the zip file was created
        if not os.path.exists(zip_file_path):
            print(f"Agent package zip file not found after build: {zip_file_path}")
            return None
        
        # Calculate the hash of the zip file
        zip_hash = calculate_file_hash(zip_file_path)
        
        print(f"Successfully built agent package for {agent_name} {agent_version}")
        return (zip_file_path, zip_hash)
        
    except Exception as e:
        print(f"Error building agent package for {agent_name} {agent_version}: {str(e)}")
        return None


def generate_agents_manifest(
    input_folder: str,
    dest_agents_folder: str,
    published_manifest: AgentsManifest,
    whitelist: list[AgentsWhitelistEntry],
    agent_cli_path: str,
) -> AgentsManifest:
    """
    Generates the manifest file for the agents.
    It only generates Agent entries if their respective versions are not already published, i.e., not present
    in the published manifest.

    Parameters:
        input_folder (str): The path to the folder containing prepared gallery agents folders.
        dest_agents_folder (str): Path where to store agent information that is then copied over to S3.
        published_manifest (AgentsManifest): A dictionary containing the manifest data for the already published agents.
        whitelist: (list[AgentsWhitelistEntry]): A list of agents that are whitelisted in a given context.
        agent_cli_path (str): The path to the agent cli file.
    """
    manifest: AgentsManifest = {"agents": {}, "organization": "Sema4.ai"}

    print("Input folder: ", input_folder)
    for agent_folder_name in os.listdir(input_folder):
        agent_folder = os.path.join(input_folder, agent_folder_name)

        print("Processing agent: ", agent_folder)
        if not os.path.isdir(agent_folder):
            continue

        # TODO (Kari 2025-09-29): Validation logic is moving to agent-server, away from agent-cli
        #                         Re-enable agent validation after the logic is provided in some new way
        #is_agent_valid = validate_agent(agent_folder, agent_cli_path)
        #if not is_agent_valid:
        #    continue

        agent_spec_data = read_yaml_file(os.path.join(agent_folder, "agent-spec.yaml"))[
            "agent-package"
        ]["agents"][0]
        agent_name = agent_spec_data["name"]
        agent_version = agent_spec_data["version"]

        kebab_case_agent_name = to_kebab_case(agent_name)

        whitelist_entry = get_whitelist_entry(kebab_case_agent_name, whitelist)

        # If a given Agent is not whitelisted for a given manifest, or it's current version is already published, skip it.
        if not whitelist_entry or is_agent_published(published_manifest, agent_name, agent_version):
            continue

        with open(os.path.join(agent_folder, "runbook.md"), encoding='utf-8') as file:
            runbook_content = file.read()

        # Build the agent package
        package_result = build_agent_package(agent_folder, agent_name, agent_version, agent_cli_path)
        if not package_result:
            print(f"Skipping agent {agent_name} {agent_version} due to package build failure")
            continue
        
        zip_file_path, zip_hash = package_result

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
            "agent_package_zip_url": f"{base_url}{kebab_case_agent_name}/{agent_version}/{kebab_case_agent_name}.zip",
            "agent_package_zip_hash": zip_hash,
        }

        # Copy the interesting files to be uploaded in S3
        dest = Path(dest_agents_folder) / kebab_case_agent_name / agent_version

        # Only copy the agent files into agents output directory if it doesn't exist yet.
        # If it does, it means that the agent was already copied while generating other manifests.
        if not os.path.exists(dest):
            os.makedirs(dest)

            shutil.copyfile(
                Path(agent_folder) / "agent-spec.yaml", dest / "agent-spec.yaml"
            )
            shutil.copyfile(Path(agent_folder) / "CHANGELOG.md", dest / "CHANGELOG.md")
        
        # Always copy the zip file if it doesn't exist (zip files are version-specific)
        zip_dest_path = dest / f"{kebab_case_agent_name}.zip"
        if not os.path.exists(zip_dest_path):
            shutil.copyfile(zip_file_path, zip_dest_path)
        
        # Extract and copy the agent package metadata from the zip file
        metadata_dest_path = dest / "__agent_package_metadata__.json"
        if not os.path.exists(metadata_dest_path):
            import zipfile
            try:
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    if "__agent_package_metadata__.json" in zip_ref.namelist():
                        zip_ref.extract("__agent_package_metadata__.json", dest)
                        print(f"Extracted agent package metadata for {agent_name} {agent_version}")
                    else:
                        print(f"Warning: __agent_package_metadata__.json not found in zip for {agent_name} {agent_version}")
            except Exception as e:
                print(f"Error extracting metadata from zip for {agent_name} {agent_version}: {str(e)}")

        agent_info: AgentInfo = {
            "name": agent_name,
            "versions": [agent_info],
        }

        # If the whitelist entry defines a required Studio version, add it to the manifest.
        if "required_studio_version" in whitelist_entry:
            agent_info["requiredStudioVersion"] = whitelist_entry["required_studio_version"]
            agent_info["required_studio_version"] = whitelist_entry["required_studio_version"]

        manifest["agents"][agent_name] = agent_info

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
    new_manifest: AgentsManifest = published_manifest.copy()

    for updated_agent_name, updated_agent_info in update_manifest["agents"].items():
        if updated_agent_name not in new_manifest["agents"]:
            new_manifest["agents"][updated_agent_name] = updated_agent_info
            continue

        agent_info = new_manifest["agents"][updated_agent_name]
        versions_info = agent_info.get("versions", [])

        # we can only have one compiled version at manifest generation
        updated_agent_version = updated_agent_info["versions"][0]["version"]

        # If agent is not published then add the new version and sort the versions
        if not is_agent_published(
            new_manifest, updated_agent_name, updated_agent_version
        ):
            # Check if this version already exists in the manifest
            existing_version_index = None
            for i, existing_version in enumerate(versions_info):
                if existing_version.get("version") == updated_agent_version:
                    existing_version_index = i
                    break
            
            if existing_version_index is not None:
                # Update existing version with new fields
                versions_info[existing_version_index] = updated_agent_info["versions"][0]
            else:
                # Add new version
                versions_info.append(updated_agent_info["versions"][0])
            
            agent_info["versions"] = sorted(versions_info, key=lambda x: x["version"])

    return new_manifest


def get_actions_info(action_packages: list[dict]) -> list[AgentActionPackage]:
    import requests

    actions = []
    for action in action_packages:
        version = action["version"]

        folder_name = action["path"].split("/")[-1]
        metadata_url = f"https://cdn.sema4.ai/gallery/actions/{folder_name}/{version}/metadata.json"
        response = requests.get(metadata_url)

        if response.status_code != 200:
            raise Exception(
                f"Invalid action package, could not find it at: {metadata_url}"
            )

        action_metadata = response.json()

        actions.append(
            {
                "name": action["name"],
                "version": version,
                "whitelist": action.get("whitelist", []),
                "organization": "Sema4.ai",
                "metadata": action_metadata.get("metadata", {}),
            }
        )

    return actions


def get_whitelist_entry(kebab_case_agent_name: str, whitelist: list[AgentsWhitelistEntry]) -> AgentsWhitelistEntry | None:
    return next((entry for entry in whitelist if entry["name"] == kebab_case_agent_name), None)

def save_manifest(manifest: AgentsManifest, file_path: str) -> None:
    with open(file_path, "w", encoding='utf-8', newline='\n') as file:
        json.dump(manifest, file)


def is_agent_published(published_manifest: AgentsManifest, agent_name: str, version: str) -> bool:
    manifest_agent_versions = (
        published_manifest.get("agents").get(agent_name, {}).get("versions", [])
    )
    versions = [x.get("version") for x in manifest_agent_versions]

    if version not in versions:
        return False

    # Check if the agent version has the required zip file fields
    agent_versions = published_manifest.get("agents", {}).get(agent_name, {}).get("versions", [])
    for agent_version in agent_versions:
        if agent_version.get("version") == version:
            # Check if both zip URL and hash are present
            if "agent_package_zip_url" not in agent_version or "agent_package_zip_hash" not in agent_version:
                return False
            break

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
