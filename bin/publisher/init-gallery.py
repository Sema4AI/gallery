from robocorp.tasks import task
import os
from utils import clear_folders, download_action_server, download_rcc
from manifest import generate_manifest
from extractor import extract_and_rename
from builder import build_action_packages

# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"


@task
def main_task():
    input_folder = os.path.abspath(os.path.join(script_dir, '../../actions'))
    rcc_path = download_rcc()
    action_server_path = download_action_server()
    clear_folders(zips_folder)
    build_action_packages(input_folder, zips_folder, action_server_path)
    clear_folders(gallery_actions_folder)
    extract_and_rename(zips_folder, gallery_actions_folder, rcc_path)
    generate_manifest(gallery_actions_folder, base_url)
    print(f"\n\n-> Gallery generated in: {gallery_actions_folder}")