import os
import subprocess
from utils import log_error, read_yaml_file, get_version_strings_from_package_info
from models import PackageInfo, Manifest


def build_single_package(sub_folder_path: str, zips_folder: str, action_server_path: str) -> None:
    """
    Builds a single action package from a specified folder using the provided action server path.

    Parameters:
        sub_folder_path (str): The path to the folder containing the package.yaml.
        zips_folder (str): The path to the folder where the zip files will be stored.
        action_server_path (str): The path to the action server executable.
    """
    package_yaml_path = os.path.join(sub_folder_path, 'package.yaml')
    if os.path.isfile(package_yaml_path):
        command = f"\"{action_server_path}\" package build --output-dir {zips_folder} --override"
        try:
            print(f">>> Running: {sub_folder_path}")

            subprocess.run(command, shell=True, check=True, cwd=sub_folder_path)
        except subprocess.CalledProcessError as e:
            log_error(sub_folder_path, str(e))
            print(f"{sub_folder_path} package errored, will not be available to publish")


def build_action_packages(input_folder: str, zips_folder: str, action_server_path: str, manifest: Manifest = None) -> None:
    """
    Iterates over all sub-folders in the input folder and builds action packages where package.yaml is found.

    Parameters:
        input_folder (str): The path to the main input folder containing multiple action package folders.
        zips_folder (str): The path where the resulting zip files should be stored.
        action_server_path (str): The path to the action server executable.
        manifest (Manifest): The package manifest. If provided, versions already existing in the manifest
            will be skipped.
    """

    # Ensure the output directory exists
    if not os.path.exists(zips_folder):
        os.makedirs(zips_folder)

    # Process each sub-folder in the main input folder
    for sub_folder_name in os.listdir(input_folder):
        sub_folder_path = os.path.join(input_folder, sub_folder_name)

        if os.path.isdir(sub_folder_path):
            try:
                package_data = read_yaml_file(os.path.join(sub_folder_path, "package.yaml"))
            except Exception as e:
                log_error(f"Reading package.yaml from {sub_folder_path} failed with error {e}, skipping")
                continue

            published_versions: list[str] = []

            package_name = package_data.get('name')
            package_version = package_data.get('version')

            # If manifest was provided, we want to use it to get already published packages, and exclude package
            # from being built if current version is already in the manifest.
            if manifest is not None:
                package_info = manifest['packages'].get(package_name)

                if package_info is not None:
                    published_versions = get_version_strings_from_package_info(package_info)

            # If there is no published versions (either because the package is new, or the manifest
            # was not provided at all), or if the current version does not exist in the manifest,
            # only then we build a package.
            if len(published_versions) == 0 or package_version not in published_versions:
                build_single_package(sub_folder_path, zips_folder, action_server_path)