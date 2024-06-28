import os
import subprocess
from utils import log_error

def build_single_package(sub_folder_path, zips_folder, action_server_path):
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
            print(f"\n>>>>>>>> Running: {sub_folder_path}")
            subprocess.run(command, shell=True, check=True, cwd=sub_folder_path)
        except subprocess.CalledProcessError as e:
            log_error(sub_folder_path, str(e))

def build_action_packages(input_folder, zips_folder, action_server_path):
    """
    Iterates over all sub-folders in the input folder and builds action packages where package.yaml is found.

    Parameters:
        input_folder (str): The path to the main input folder containing multiple action package folders.
        zips_folder (str): The path where the resulting zip files should be stored.
        action_server_path (str): The path to the action server executable.
    """
    # Ensure the output directory exists
    if not os.path.exists(zips_folder):
        os.makedirs(zips_folder)

    # Process each sub-folder in the main input folder
    for sub_folder_name in os.listdir(input_folder):
        sub_folder_path = os.path.join(input_folder, sub_folder_name)
        if os.path.isdir(sub_folder_path):
            build_single_package(sub_folder_path, zips_folder, action_server_path)
