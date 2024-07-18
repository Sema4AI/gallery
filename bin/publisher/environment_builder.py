import os
import platform
from utils import read_file_contents, url_exists
from tools import ensure_holotree_shared, run_rcc_command


def get_environment_file_name(env_hash: str) -> str:
    system = platform.system().lower()

    return f"{env_hash}_{system}_amd64.zip"


def get_environment_url(env_hash: str) -> str:
    base_environments_url = 'https://cdn.sema4.ai/holotree/sema4ai/'
    file_name = get_environment_file_name(env_hash)

    return f"{base_environments_url}{file_name}"


def build_package_environment(version_path: str, environments_folder: str) -> None:
    """
    Builds a single environment for given action package.
    Args:
        version_path (str): The path to the exact action package.
        environments_folder (str): The path where the resulting environment files will be stored.
    """
    env_hash_path = os.path.join(version_path, "env.hash")
    env_hash = read_file_contents(env_hash_path)

    environment_url = get_environment_url(env_hash)

    if url_exists(environment_url):
        print(f"Environment with hash {env_hash} for package {version_path} already exists, skipping")
        return

    package_yaml_path = os.path.join(version_path, "package.yaml")
    result_zip_path = os.path.join(environments_folder, get_environment_file_name(env_hash))

    print(f"Building: {version_path}")

    run_rcc_command(['ht', 'prebuild', package_yaml_path, '--export', result_zip_path])

    print(f"Environment built: {result_zip_path}")


def build_package_environments(gallery_actions_folder: str, environments_folder: str) -> None:
    """
    Iterates over all sub-folders in the gallery folder, and builds RCC environments for related package.yaml files.
    Args:
        gallery_actions_folder (str): The path to the gallery folder containing built action packages.
        environments_folder (str): The path where the resulting environment files will be stored.
    """
    ensure_holotree_shared()

    for action_package_name in os.listdir(gallery_actions_folder):
        action_package_path = os.path.join(gallery_actions_folder, action_package_name)

        if os.path.isdir(action_package_path):
            for version_dir in os.listdir(action_package_path):
                version_path = os.path.join(action_package_path, version_dir)

                env_hash_path = os.path.join(version_path, "env.hash")
                python_env_hash = read_file_contents(env_hash_path)

                build_package_environment(version_path, environments_folder)



