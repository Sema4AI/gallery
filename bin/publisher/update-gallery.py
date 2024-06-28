from robocorp.tasks import task
import os
from utils import download_action_server, download_rcc
from manifest import generate_manifest
from extractor import extract_single_zip
from builder import build_single_package

# Define the input, output, and extracted folders
zips_folder = os.path.abspath(r".\zips")
results_folder = os.path.abspath(r".\result")
base_url = "https://cdn.sema4.ai/gallery/actions/"
script_dir = os.path.dirname(os.path.abspath(__file__))

@task
def add_single_package_task():
    # TODO: Figure out how to get this in.. env. variable in GHA..?
    package_name = 'browsing'

    input_folder = os.path.abspath(os.path.join(script_dir, f'../../actions/{package_name}'))
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
    # TODO: The manifest.json needs to be done over everything in S3
    #       so we probably need to download all, or have this running in AWS as Lambda or something that reacts to changes
    generate_manifest(results_folder, base_url)

