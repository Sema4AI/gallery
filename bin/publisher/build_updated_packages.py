import json
import os

from actions_manifest import (
    generate_actions_manifest,
    generate_consolidated_manifest,
    save_manifest,
)
from extractor import extract_all
from models import ActionsManifest
from package_builder import build_action_packages
from robocorp.tasks import task
from tools import get_action_server, get_rcc
from utils import (
    clear_folders,
    download_file,
    get_working_dir,
    is_manifest_empty,
    log_error,
    read_json_file,
)

# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"


@task
def build_updated_packages():
    working_dir = get_working_dir()
    published_manifest_path = os.path.join(working_dir, "published_manifest.json")
    published_manifest_spcs_path = os.path.join(working_dir, "published_manifest_spcs.json")

    download_file(
        "https://cdn.sema4.ai/gallery/actions/manifest.json", published_manifest_path
    )
    download_file(
        "https://cdn.sema4.ai/gallery/actions/manifest_spcs.json", published_manifest_spcs_path
    )

    published_manifest: ActionsManifest
    published_manifest_spcs: ActionsManifest

    try:
        published_manifest = read_json_file(published_manifest_path)
        published_manifest_spcs = read_json_file(published_manifest_spcs_path)
    except Exception:
        log_error("Reading published manifest(s) failed, exiting...")
        return

    # Check both manifests
    if is_manifest_empty(published_manifest) or is_manifest_empty(published_manifest_spcs):
        log_error("No published manifest available, exiting...")
        return

    rcc_path = get_rcc()
    action_server_path = get_action_server()

    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)

    input_folder = os.path.abspath(os.path.join(script_dir, "../../actions"))

    # We use manifest to build all the packages that have a version that is not yet published.
    # We want to skip not updated packages at this point already, as building a package can also take
    # a non-trivial amount of time.
    built_count = build_action_packages(
        input_folder, zips_folder, action_server_path, published_manifest
    )

    # If no packages were built, there is no point in continuing. Manifest won't be created, and the pipeline
    # will be able to leverage this to skip some of the jobs.
    if built_count == 0:
        print(
            f"\n No packages were built (no updates detected), manifest won't be created."
        )
        return

    # Then, we extract all information needed to update the manifest from the package eligible for update.
    extract_all(zips_folder, gallery_actions_folder, rcc_path)

    # Generate manifest for generated packages. Note that if a package already exists in the manifest currently
    # published in S3, it will be skipped, resulting in a "partial" manifest, that will be merged into current
    # one later on in the pipeline.
    update_manifest = generate_actions_manifest(gallery_actions_folder, base_url)

    # We consolidate existing manifest with the updates, getting a manifest including updated packages.
    new_manifest: ActionsManifest = generate_consolidated_manifest(
        published_manifest, update_manifest
    )

    new_manifest["organization"] = "Sema4.ai"

    # Create consolidated SPCS manifest using the published SPCS manifest as base
    new_manifest_spcs: ActionsManifest = generate_consolidated_manifest(
        published_manifest_spcs, update_manifest
    )
    new_manifest_spcs["organization"] = "Sema4.ai"
    
    with open("action_packages_whitelist.json", "r", encoding='utf-8') as f:
        whitelist = json.load(f)

    save_manifest(
        new_manifest,
        os.path.join(gallery_actions_folder, "manifest.json"),
        whitelist["standard"],
    )

    save_manifest(
        new_manifest_spcs,
        os.path.join(gallery_actions_folder, "manifest_spcs.json"),
        whitelist["spcs"],
    )


if __name__ == "__main__":
    build_updated_packages()
