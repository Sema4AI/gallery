from robocorp.tasks import task
import os
from utils import clear_folders, download_action_server, download_rcc
from manifest import generate_manifest
from extractor import extract_and_rename
from builder import build_action_packages

# Define the input, output, and extracted folders
zips_folder = os.path.abspath("/zips")
results_folder = os.path.abspath("/result")
base_url = "https://cdn.sema4.ai/gallery/actions/"
script_dir = os.path.dirname(os.path.abspath(__file__))

@task
def main_task():
    input_folder = os.path.abspath(os.path.join(script_dir, '../../actions'))
    rcc_path = download_rcc()
    action_server_path = download_action_server()
    clear_folders(zips_folder)
    build_action_packages(input_folder, zips_folder, action_server_path)
    clear_folders(results_folder)
    extract_and_rename(zips_folder, results_folder, rcc_path)
    generate_manifest(results_folder, base_url)