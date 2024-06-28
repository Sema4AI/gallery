from robocorp.tasks import task
import os
from utils import download_action_server, download_rcc, get_folder_from_repo
from manifest import generate_manifest
from extractor import extract_single_zip
from builder import build_single_package

# Define the input, output, and extracted folders
zips_folder = os.path.abspath(r".\zips")
results_folder = os.path.abspath(r".\result")
base_url = "https://cdn.sema4.ai/gallery/actions/"

@task
def add_single_package_task():
    url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
    extract_to = os.path.abspath('./temp')
    package_name = 'browsing'
    input_folder = get_folder_from_repo(url, extract_to, f'gallery-main/actions/{package_name}')
    rcc_path = download_rcc()
    action_server_path = download_action_server()
    
    # Build only the specified package
    build_single_package(input_folder, zips_folder, action_server_path)
    
    # Extract and rename only for the specified package zip file
    specific_zip_path = os.path.join(zips_folder, f"{package_name}.zip")
    if os.path.exists(specific_zip_path):
        extract_single_zip(specific_zip_path, results_folder, rcc_path)
    else:
        print(f"No zip file found for package '{specific_zip_path}'. Check the build process or package name.")
    
    # Generate manifest for only the newly added package
    generate_manifest(results_folder, base_url)

