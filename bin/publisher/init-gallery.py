from robocorp.tasks import task
import os
from utils import clear_folders, download_action_server, download_rcc, get_repo
from manifest import generate_manifest
from extractor import extract_and_rename
from builder import build_action_packages

# Define the input, output, and extracted folders
zips_folder = os.path.abspath(r".\zips")
results_folder = os.path.abspath(r".\result")


base_url = "https://cdn.sema4.ai/gallery/actions/"

@task
def main_task():
    url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
    extract_to = os.path.abspath('./temp')
    exclude_dirs = ['gallery-main/agents', 'gallery-main/actions/bin', 'gallery-main/.github']
    input_folder = os.path.join(get_repo(url, extract_to, exclude_dirs), 'gallery-main/actions')

    rcc_path = download_rcc()
    action_server_path = download_action_server()
    clear_folders(zips_folder)
    build_action_packages(input_folder, zips_folder, action_server_path)
    clear_folders(results_folder)
    extract_and_rename(zips_folder, results_folder, rcc_path)
    generate_manifest(results_folder, base_url)