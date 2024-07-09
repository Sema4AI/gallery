from robocorp.tasks import task
import os
from utils import clear_folders, download_action_server, download_rcc
from manifest import generate_manifest, save_manifest
from extractor import extract_all
from builder import build_action_packages

working_dir = os.path.abspath(".")

# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"


@task
def build_all_packages():
    input_folder = os.path.abspath(os.path.join(script_dir, '../../actions'))

    rcc_path = download_rcc(working_dir)
    action_server_path = download_action_server(working_dir)

    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)

    build_action_packages(input_folder, zips_folder, action_server_path)

    extract_all(zips_folder, gallery_actions_folder, rcc_path)

    manifest = generate_manifest(gallery_actions_folder, base_url)

    # Write manifest to file
    save_manifest(manifest, os.path.join(gallery_actions_folder, "manifest.json"))

    print(f"\n\n-> Gallery generated in: {gallery_actions_folder}")


if __name__ == '__main__':
    build_all_packages()