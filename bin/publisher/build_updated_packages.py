from robocorp.tasks import task
import os
from utils import get_working_dir, clear_folders, download_file, read_json_file, is_manifest_empty, log_error
from tools import get_action_server, get_rcc
from manifest import generate_manifest, save_manifest, generate_consolidated_manifest
from extractor import extract_all
from models import Manifest
from package_builder import build_action_packages


# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"

@task
def build_updated_packages():
    working_dir = get_working_dir()
    published_manifest_path = os.path.join(working_dir, "published_manifest.json")

    download_file("https://cdn.sema4.ai/gallery/actions/manifest.json", published_manifest_path)
    published_manifest: Manifest = read_json_file(published_manifest_path)

    # When updating the gallery, we assume that some packages has already been published - otherwise, we want to
    # skip the operation. This ensures that if manifest download fails for any reason, we don't end up replacing
    # our entire gallery with only packages currently in the repository.
    if is_manifest_empty(published_manifest):
        log_error("No published manifest available, exiting...")
        return

    rcc_path = get_rcc()
    action_server_path = get_action_server()

    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)

    input_folder = os.path.abspath(os.path.join(script_dir, '../../actions'))

    # We use manifest to build all the packages that have a version that is not yet published.
    # We want to skip not updated packages at this point already, as building a package can also take
    # a non-trivial amount of time.
    build_action_packages(input_folder, zips_folder, action_server_path, published_manifest)

    # Then, we extract all information needed to update the manifest from the package eligible for update.
    extract_all(zips_folder, gallery_actions_folder, rcc_path)
    
    # Generate manifest for generated packages. Note that if a package already exists in the manifest currently
    # published in S3, it will be skipped, resulting in a "partial" manifest, that will be merged into current
    # one later on in the pipeline.
    update_manifest = generate_manifest(gallery_actions_folder, base_url)

    # We consolidate existing manifest with the updates, getting a manifest including updated packages.
    new_manifest: Manifest = generate_consolidated_manifest(published_manifest, update_manifest)

    # Write manifests to file.
    save_manifest(new_manifest, os.path.join(gallery_actions_folder, "manifest.json"))


if __name__ == '__main__':
    build_updated_packages()