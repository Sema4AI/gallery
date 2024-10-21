import os

from agents_manifest import generate_agents_manifest, save_manifest
from robocorp.tasks import task
from tools import get_action_server, get_agent_cli
from utils import clear_folders

script_dir = os.path.dirname(os.path.abspath(__file__))
dest_agents_folder = os.path.join(script_dir, "agents")
manifest_file = os.path.join(script_dir, "manifest.json")


@task
def build_all_agents():
    input_folder = os.path.abspath(os.path.join(script_dir, "../../agents"))

    get_action_server()
    agent_cli_path = get_agent_cli()

    clear_folders(dest_agents_folder)
    if os.path.exists(manifest_file):
        os.remove(manifest_file)

    input_folder = os.path.abspath(os.path.join(script_dir, "../../agents"))
    starting_manifest = {"agents": {}, "organization": "Sema4.ai"}

    manifest = generate_agents_manifest(
        input_folder,
        dest_agents_folder,
        starting_manifest,
        agent_cli_path,
    )

    # Write manifests to file.
    save_manifest(manifest, manifest_file)


if __name__ == "__main__":
    build_all_agents()
