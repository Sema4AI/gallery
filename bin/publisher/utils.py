import hashlib
import json
import logging
import os
import shutil
import zipfile
from typing import Any, Union

import requests
import yaml
from models import ActionsManifest, PackageInfo

logging.basicConfig(level=logging.INFO)


def get_working_dir() -> str:
    """Return the directory current task was run in."""
    return os.path.abspath(".")


def sha256(filepath: str, hash_type: str = "sha256") -> str:
    """Calculate the hash of a file using the specified hash algorithm (default is SHA256) and return the hex digest."""
    hash_obj = hashlib.new(hash_type)
    with open(filepath, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def log_error(error_message: str, sub_folder_path: str = None) -> None:
    with open("log.txt", "a") as log_file:
        message = f"Error in folder {sub_folder_path}: " if sub_folder_path else ""
        message += f"{error_message}\n"

        log_file.write(message)


def read_file_contents(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read().strip()


def read_json_file(file_path: str) -> dict[str, Any]:
    with open(file_path, "r") as file:
        return json.load(file)


def read_yaml_file(file_path: str) -> dict[str, Any]:
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def clear_folders(target_folder: str) -> None:
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)
    os.makedirs(target_folder)


def ensure_folders(target_folder: str) -> None:
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)


def download_file(url: str, file_path: str = "") -> str:
    response = requests.get(url, stream=True)

    file_path = file_path if file_path is not None else url.split("/")[-1]

    with open(file_path, "wb") as file:
        shutil.copyfileobj(response.raw, file)

    return file_path


def url_exists(url: str) -> bool:
    try:
        result = requests.head(url)

        return result.status_code == 200
    except requests.RequestException:
        return False


def package_yaml_from_zip(
    zip_ref: zipfile.ZipFile, extract_path: str
) -> dict[str, Any]:
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

        package_data = read_yaml_file(yaml_path)
        os.remove(yaml_path)  # Clean up the temporary file

        return package_data
    return {}


def download_and_parse_json(url: str) -> Union[dict[str, Any], None]:
    """
    Downloads and parses a JSON file from a specified URL.

    Parameters:
        url (str): The URL from which to download the JSON data.

    Returns:
        dict: A dictionary containing the parsed JSON data.
        None: If an error occurs during download or parsing.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        json_data = response.json()  # Parses the JSON response into a dictionary
        return json_data
    except requests.RequestException as e:
        print(f"Error downloading data: {e}")
    except json.JSONDecodeError:
        print("Failed to parse JSON.")
    return None


def get_version_strings_from_package_info(package_info: PackageInfo) -> list[str]:
    versions = package_info.get("versions", [])

    return [version_info.get("version") for version_info in versions]


def is_manifest_empty(manifest: ActionsManifest) -> bool:
    return "packages" not in manifest
