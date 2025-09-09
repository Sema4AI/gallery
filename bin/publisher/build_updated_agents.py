import os

from agents_manifest import (
    generate_agents_manifest,
    generate_consolidated_manifest,
    save_manifest,
)
from bin.publisher.models import AgentsWhitelistEntry
from models import AgentsManifest, AgentsWhitelist
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

agents_whitelist_file = os.path.join(script_dir, "agents_whitelist.json")

manifest_file = os.path.join(dest_agents_folder, "manifest.json")
spcs_manifest_file = os.path.join(dest_agents_folder, "manifest_spcs.json")
manifest_v2_file = os.path.join(dest_agents_folder, "manifest_v2.json")
spcs_manifest_v2_file = os.path.join(dest_agents_folder, "manifest_spcs_v2.json")


@task
def build_updated_agents():
    published_manifest_path = os.path.join(
        get_working_dir(), "published_agents_manifest.json"
    )

    published_manifest_spcs_path = os.path.join(
        get_working_dir(), "published_agents_manifest_spcs.json"
    )

    published_manifest_v2_path = os.path.join(
        get_working_dir(), "published_agents_manifest_v2.json"
    )

    published_manifest_spcs_v2_path = os.path.join(
        get_working_dir(), "published_agents_manifest_spcs_v2.json"
    )

    try:
        agents_whitelist: AgentsWhitelist = read_json_file(agents_whitelist_file)
    except Exception:
        log_error("Reading agents whitelist failed, exiting...")
        return

    download_file(
        "https://cdn.sema4.ai/gallery/agents/manifest.json", published_manifest_path
    )

    download_file(
        "https://cdn.sema4.ai/gallery/agents/manifest_spcs.json", published_manifest_spcs_path
    )

    download_file(
        "https://cdn.sema4.ai/gallery/agents/manifest_v2.json", published_manifest_v2_path
    )

    download_file(
        "https://cdn.sema4.ai/gallery/agents/manifest_spcs_v2.json", published_manifest_spcs_v2_path
    )

    try:
        published_manifest: AgentsManifest = read_json_file(published_manifest_path)
        published_manifest_spcs: AgentsManifest = read_json_file(published_manifest_spcs_path)
        published_manifest_v2: AgentsManifest = read_json_file(published_manifest_v2_path)
        published_manifest_spcs_v2: AgentsManifest = read_json_file(published_manifest_spcs_v2_path)
    except Exception:
        log_error("Reading published agents manifests failed, exiting...")
        return

    get_action_server()
    agent_cli_path = get_agent_cli()

    clear_folders(dest_agents_folder)

    input_folder = os.path.abspath(os.path.join(script_dir, "../../agents"))

    def build_and_save_manifest(
        output_manifest_file: str,
        existing_manifest: AgentsManifest,
        whitelist: list[AgentsWhitelistEntry]
    ):
        if os.path.exists(output_manifest_file):
            os.remove(output_manifest_file)

        # Generate manifest for Agents. Note that if an Agent already exists in the manifest currently published in S3,
        # it will be skipped, resulting in a "partial" manifest that will be merged into the current one.
        update_manifest = generate_agents_manifest(
            input_folder,
            dest_agents_folder,
            existing_manifest,
            whitelist,
            agent_cli_path,
        )

        # Consolidate the existing manifest with the updates.
        new_manifest: AgentsManifest = generate_consolidated_manifest(existing_manifest, update_manifest)

        # Save the manifest to file.
        save_manifest(new_manifest, output_manifest_file)

    # Manifest v1 does not support Studio version requirements, so we simply filter out those Agents
    # from the whitelists.
    v1_whitelist_standard = [entry for entry in agents_whitelist["standard"] if "required_studio_version" not in entry]
    v1_whitelist_spcs = [entry for entry in agents_whitelist["spcs"] if "required_studio_version" not in entry]

    build_and_save_manifest(manifest_file, published_manifest, v1_whitelist_standard)
    build_and_save_manifest(spcs_manifest_file, published_manifest_spcs, v1_whitelist_spcs)
    build_and_save_manifest(manifest_v2_file, published_manifest_v2, agents_whitelist["standard"])
    build_and_save_manifest(spcs_manifest_v2_file, published_manifest_spcs_v2, agents_whitelist["spcs"])

if __name__ == "__main__":
    build_updated_agents()
