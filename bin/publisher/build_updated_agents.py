import json
import os

from agents_manifest import (
    generate_agents_manifest,
    generate_consolidated_manifest,
    save_manifest,
)
from models import AgentsManifest
from robocorp.tasks import task
from tools import get_action_server, get_agent_cli
from utils import (
    clear_folders,
    download_file,
    get_working_dir,
    log_error,
    read_json_file,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
dest_agents_folder = os.path.join(script_dir, "agents")
manifest_file = os.path.join(dest_agents_folder, "manifest.json")
spcs_manifest_file = os.path.join(dest_agents_folder, "manifest_spcs.json")


@task
def build_updated_agents():
    published_manifest_path = os.path.join(
        get_working_dir(), "published_agents_manifest.json"
    )

    download_file(
        "https://cdn.sema4.ai/gallery/agents/manifest.json", published_manifest_path
    )

    try:
        published_manifest: AgentsManifest = read_json_file(published_manifest_path)
    except Exception:
        log_error("Reading published agents manifest failed, exiting...")
        return

    get_action_server()
    agent_cli_path = get_agent_cli()

    clear_folders(dest_agents_folder)
    if os.path.exists(manifest_file):
        os.remove(manifest_file)

    input_folder = os.path.abspath(os.path.join(script_dir, "../../agents"))

    # Generate manifest for generated packages. Note that if a package already exists in the manifest currently
    # published in S3, it will be skipped, resulting in a "partial" manifest, that will be merged into current
    # one later on in the pipeline.
    update_manifest = generate_agents_manifest(
        input_folder,
        dest_agents_folder,
        published_manifest,
        agent_cli_path,
    )

    # We consolidate existing manifest with the updates
    new_manifest: AgentsManifest = generate_consolidated_manifest(
        published_manifest, update_manifest
    )

    with open("whitelist.json", "r") as f:
        whitelist = json.load(f)

    save_manifest(new_manifest, manifest_file, whitelist["standard"]["agents"])
    save_manifest(new_manifest, spcs_manifest_file, whitelist["spcs"]["agents"])


if __name__ == "__main__":
    build_updated_agents()
