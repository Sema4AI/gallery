import os

from actions_manifest import (
    generate_actions_manifest,
    generate_actions_manifest_for_sai,
    save_manifest,
)
from extractor import extract_all
from package_builder import build_action_packages
from robocorp.tasks import task
from tools import get_action_server, get_rcc
from utils import clear_folders

# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"


@task
def build_all_packages():
    input_folder = os.path.abspath(os.path.join(script_dir, "../../actions"))

    rcc_path = get_rcc()
    action_server_path = get_action_server()

    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)

    build_action_packages(input_folder, zips_folder, action_server_path)

    extract_all(zips_folder, gallery_actions_folder, rcc_path)

    manifest = generate_actions_manifest(gallery_actions_folder, base_url)
    sai_manifest = generate_actions_manifest_for_sai(gallery_actions_folder)

    with open("action_packages_whitelist.json", "r") as f:
        import json
        whitelist = json.load(f)

    # Write manifest to file
    save_manifest(manifest, os.path.join(gallery_actions_folder, "manifest.json"), whitelist["standard"])
    save_manifest(
        sai_manifest, os.path.join(gallery_actions_folder, "manifest_sai.json"), whitelist["standard"]
    )
    save_manifest(
        sai_manifest, os.path.join(gallery_actions_folder, "manifest_sai_spcs.json"), whitelist["spcs"]
    )

    print(f"\n\n-> Gallery generated in: {gallery_actions_folder}")


if __name__ == "__main__":
    build_all_packages()
