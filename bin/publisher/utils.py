import os
import hashlib
import shutil
import requests
import platform
import yaml
import zipfile
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO)

base_path = os.path.abspath(".")
as_version = "0.15.1"
rcc_version = "v18.1.1"

def sha256(filepath, hash_type='sha256'):
    """Calculate the hash of a file using the specified hash algorithm (default is SHA256) and return the hex digest."""
    hash_obj = hashlib.new(hash_type)
    with open(filepath, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def log_error(sub_folder_path, error_message):
    with open("log.txt", "a") as log_file:
        log_file.write(f"Error in folder {sub_folder_path}: {error_message}\n")

def read_file_contents(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read().strip()
    return None

def clear_folders(target_folder):
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)
    os.makedirs(target_folder)

def download_action_server():
    system = platform.system().lower()
    if system == "windows":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/windows64/action-server.exe"
        action_server_exe = os.path.join(base_path, "action-server.exe")
    elif system == "darwin":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/macos64/action-server"
        action_server_exe = os.path.join(base_path, "action-server")
    elif system == "linux":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/linux64/action-server"
        action_server_exe = os.path.join(base_path, "action-server")
    else:
        raise Exception("Unsupported OS")

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we raise an error for bad status codes
    with open(action_server_exe, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    if system != "windows":
        os.chmod(action_server_exe, 0o755)

    return action_server_exe

def download_rcc():
    system = platform.system().lower()
    if system == "windows":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/windows64/rcc.exe"
        rcc_exe = os.path.join(base_path, "rcc.exe")
    elif system == "darwin":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/macos64/rcc"
        rcc_exe = os.path.join(base_path, "rcc")
    elif system == "linux":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/linux64/rcc"
        rcc_exe = os.path.join(base_path, "rcc")
    else:
        raise Exception("Unsupported OS")

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we raise an error for bad status codes
    with open(rcc_exe, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    if system != "windows":
        os.chmod(rcc_exe, 0o755)

    return rcc_exe


def get_repo(url, extract_to, exclude_dirs=None):
    """
    Download a zip file from a GitHub repository URL, clear the target directory, extract it to the specified folder,
    excluding specified directories, and return the path to the extracted root.
    
    Parameters:
        url (str): URL to download the zip file.
        extract_to (str): Directory path where the zip file should be extracted.
        exclude_dirs (list, optional): List of directory names to exclude from extraction.

    Example:
        url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
        extract_to = os.path.abspath('./temp')
        exclude_dirs = ['gallery-main/agents', 'gallery-main/actions/bin', 'gallery-main/.github']
        input_folder = os.path.join(get_repo(url, extract_to, exclude_dirs), 'gallery-main/actions')
    """
    # Ensure the extraction path is cleared before extraction
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    os.makedirs(extract_to, exist_ok=True)

    try:
        response = requests.get(url)
        response.raise_for_status()
        with zipfile.ZipFile(BytesIO(response.content)) as the_zip:
            files_to_extract = [item for item in the_zip.namelist() if not any(item.startswith(f"{exclude_dir}/") for exclude_dir in exclude_dirs)] if exclude_dirs else the_zip.namelist()
            the_zip.extractall(extract_to, files_to_extract)
        logging.info(f"Repository extracted to {extract_to} excluding directories: {exclude_dirs if exclude_dirs else 'None'}")
        return extract_to
    except requests.RequestException as e:
        logging.error(f"Failed to download the repository: {str(e)}")
    except zipfile.BadZipFile:
        logging.error("Failed to unzip the repository.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

    
def get_folder_from_repo(url, extract_to, include_dir):
    """
    Download a zip file from a GitHub repository URL, clear the target directory, extract only the specified folder,
    and return the path to the extracted folder.

    Parameters:
        url (str): URL to download the zip file.
        extract_to (str): Directory path where the zip file should be extracted.
        include_dir (str): Specific directory to include in extraction.

    Example:
       url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
       extract_to = os.path.abspath('./temp')
       package_name = 'browsing'
       input_folder = get_folder_from_repo(url, extract_to, f'gallery-main/actions/{package_name}')
    """
    # Ensure the extraction path is cleared before extraction
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    os.makedirs(extract_to, exist_ok=True)

    try:
        response = requests.get(url)
        response.raise_for_status()
        with zipfile.ZipFile(BytesIO(response.content)) as the_zip:
            members = [m for m in the_zip.namelist() if m.startswith(include_dir)]
            the_zip.extractall(extract_to, members)
        logging.info(f"Specific folder '{include_dir}' extracted to {extract_to}")
        return os.path.join(extract_to, include_dir)
    except requests.RequestException as e:
        logging.error(f"Failed to download the repository: {str(e)}")
    except zipfile.BadZipFile:
        logging.error("Failed to unzip the repository.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")



def setup_full_repository():
    url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
    extract_to = os.path.abspath('./temp_repository')
    exclude_dirs = ['gallery-main/agents', 'gallery-main/actions/bin', 'gallery-main/.github']
    
    # Clear the extraction directory if it exists
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    os.makedirs(extract_to)

    # Download and extract the repository excluding specific directories
    get_repo(url, extract_to, exclude_dirs=exclude_dirs)

    return os.path.join(extract_to, 'gallery-main/actions')

def setup_specific_package(package_dir_name):
    url = "https://github.com/Sema4AI/gallery/archive/refs/heads/main.zip"
    extract_to = os.path.abspath('./temp_specific_package')
    include_dir = f'gallery-main/actions/{package_dir_name}'

    # Clear the extraction directory if it exists
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    os.makedirs(extract_to)

    # Download and extract only the specified package directory
    get_folder_from_repo(url, extract_to, include_dir=include_dir)

    return os.path.join(extract_to, include_dir)


def package_yaml_from_zip(zip_ref, extract_path):
    """
    Extracts 'package.yaml' from a zip file, parses it, and returns the package data.
    It temporarily extracts the file to the provided path, parses it, and deletes the temporary file.

    Parameters:
        zip_ref (zipfile.ZipFile): Reference to the opened zip file.
        extract_path (str): Path to extract the temporary file.

    Returns:
        dict: Parsed data from 'package.yaml', or an empty dictionary if not found.
    """
    yaml_file_name = "package.yaml"
    yaml_path = os.path.join(extract_path, yaml_file_name)
    if yaml_file_name in zip_ref.namelist():
        zip_ref.extract(yaml_file_name, extract_path)
        with open(yaml_path, 'r') as file:
            package_data = yaml.safe_load(file)
        os.remove(yaml_path)  # Clean up the temporary file
        return package_data
    return {}