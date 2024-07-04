from robocorp.tasks import task
import os
from utils import download_action_server, download_rcc, download_and_parse_json
from manifest import generate_manifest
from extractor import extract_single_zip
from builder import build_single_package

# Define the input, output, and extracted folders
script_dir = os.path.dirname(os.path.abspath(__file__))
zips_folder = os.path.join(script_dir, "zips")
gallery_actions_folder = os.path.join(script_dir, "gallery")
base_url = "https://cdn.sema4.ai/gallery/actions/"

@task
def add_single_package_task():
    package_name = 'browsing'

    manifest = download_and_parse_json("https://cdn.sema4.ai/gallery/actions/manifest.json")
    input_folder = os.path.abspath(os.path.join(script_dir, f'../../actions/{package_name}'))
    # TODO: Determine based on the manifest and the content of input_folder the packages that need an update.

    rcc_path = download_rcc()
    action_server_path = download_action_server()
    
    # Build only the specified package
    build_single_package(input_folder, zips_folder, action_server_path)
    
    # Extract and rename only for the specified package zip file
    specific_zip_path = os.path.join(zips_folder, f"{package_name}.zip")
    if os.path.exists(specific_zip_path):
        extract_single_zip(specific_zip_path, gallery_actions_folder, rcc_path)
    else:
        print(f"No zip file found for package '{specific_zip_path}'. Check the build process or package name.")
    
    # Generate manifest for only the newly added package
    # TODO: The manifest.json needs to be done over everything in S3
    # so we probably need to download all, or have this running in AWS as Lambda or something that reacts to changes
    generate_manifest(gallery_actions_folder, base_url)
 

