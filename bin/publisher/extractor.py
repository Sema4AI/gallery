import os
import shutil
import subprocess
import zipfile
from utils import log_error, sha256, package_yaml_from_zip


def extract_single_zip(zip_path: str, gallery_actions_folder: str, rcc_path: str):
    """Extracts and processes a single zip file using version data from package.yaml."""
    base_extract_path = os.path.join(gallery_actions_folder, os.path.splitext(os.path.basename(zip_path))[0])
    os.makedirs(base_extract_path, exist_ok=True)

    # Open the zip file to check contents and extract package.yaml to get the version
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        package_data = package_yaml_from_zip(zip_ref, base_extract_path)
        version = package_data.get('version', 'unknown')  # Default to 'unknown' if not found
        versioned_extract_path = os.path.join(base_extract_path, version)
        os.makedirs(versioned_extract_path, exist_ok=True)

        # Filter and extract specific files
        files_to_extract = [
            "metadata.json",
            "package.png",
            "package.yaml",
            "__action_server_metadata__.json",
            "README.md",
            "CHANGELOG.md"
        ]

        for item in zip_ref.namelist():
            if any(item.endswith(x) for x in files_to_extract) or item.endswith('.yaml'):
                zip_ref.extract(item, versioned_extract_path)

        # Rename '__action_server_metadata__.json' to 'metadata.json'
        metadata_src = os.path.join(versioned_extract_path, "__action_server_metadata__.json")
        metadata_dst = os.path.join(versioned_extract_path, "metadata.json")
        if os.path.exists(metadata_src):
            # Remove existing metadata.json if it exists to avoid rename conflict
            if os.path.exists(metadata_dst):
                os.remove(metadata_dst)
            os.rename(metadata_src, metadata_dst)

        # Copy the zip file to the versioned target folder
        shutil.copy(zip_path, os.path.join(versioned_extract_path, os.path.basename(zip_path)))

        # Calculate the hash of the zip file and save it to package.hash
        zip_hash = sha256(zip_path)
        with open(os.path.join(versioned_extract_path, "package.hash"), 'w', encoding='utf-8', newline='\n') as hash_file:
            hash_file.write(zip_hash)

        # If package.yaml was extracted, run RCC command on it
        package_yaml_path = os.path.join(versioned_extract_path, "package.yaml")
        if os.path.exists(package_yaml_path):
            hash_command = f"\"{rcc_path}\" ht hash {package_yaml_path} --silent > {os.path.join(versioned_extract_path, 'env.hash')}"
            try:
                subprocess.run(hash_command, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                log_error(f"Failed to run RCC on {package_yaml_path}: {str(e)}", versioned_extract_path)


def extract_all(zips_folder: str, gallery_actions_folder: str, rcc_path: str):
    """Iterates over all zip files in the directory and processes each one."""
    if not os.path.exists(gallery_actions_folder):
        os.makedirs(gallery_actions_folder)

    for file_name in os.listdir(zips_folder):
        if file_name.endswith(".zip"):
            zip_path = os.path.join(zips_folder, file_name)
            extract_single_zip(zip_path, gallery_actions_folder, rcc_path)
