import os
import hashlib
import json
from utils import read_file_contents, read_yaml_file, get_version_strings_from_package_info
from models import VersionInfo, PackageInfo, Manifest, ActionInfo


def generate_manifest(gallery_actions_folder: str, base_url: str) -> Manifest:
    """
    Generates the manifest file for the built action packages.

    Parameters:
        gallery_actions_folder (str): The path to the folder containing prepared gallery action packages.
        base_url (str): The base URL for the gallery actions in the S3.
    """
    manifest: Manifest = { 'packages': {} }
    all_package_hashes = []

    for action_package_name in os.listdir(gallery_actions_folder):
        action_package_path = os.path.join(gallery_actions_folder, action_package_name)

        if os.path.isdir(action_package_path):
            versions_info = []

            for version_dir in os.listdir(action_package_path):
                version_path = os.path.join(action_package_path, version_dir)
                if os.path.isdir(version_path):
                    metadata_path = os.path.join(version_path, "metadata.json")
                    package_yaml_path = os.path.join(version_path, "package.yaml")
                    env_hash_path = os.path.join(version_path, "env.hash")
                    package_hash_path = os.path.join(version_path, "package.hash")

                    # If reading of any file fails, we want to let it throw,
                    # so it can be dealt with higher up if needed.
                    package_data = read_yaml_file(package_yaml_path)
                    actions = get_actions_info(metadata_path)
                    python_env_hash = read_file_contents(env_hash_path)
                    zip_hash = read_file_contents(package_hash_path)

                    version_info: VersionInfo = {
                        'version': package_data.get('version', version_dir),
                        'description': package_data.get('description', 'No description provided.'),
                        'zip': f"{base_url}{action_package_name}/{version_dir}/{action_package_name}.zip",
                        'icon': f"{base_url}{action_package_name}/{version_dir}/package.png",
                        'metadata': f"{base_url}{action_package_name}/{version_dir}/metadata.json",
                        'readme': f"{base_url}{action_package_name}/{version_dir}/README.md",
                        'changelog': f"{base_url}{action_package_name}/{version_dir}/CHANGELOG.md",
                        'actions': actions,
                        'python_env_hash': python_env_hash,
                        'zip_hash': zip_hash
                    }

                    versions_info.append(version_info)

                    if zip_hash:
                        all_package_hashes.append(zip_hash)

            if versions_info:
                package_name = package_data.get('name', action_package_name)

                action_package: PackageInfo = {
                    'name': package_name,
                    'versions': versions_info
                }

                manifest['packages'][package_name] = action_package

        # We only want to calculate the total hash if there are any packages in the manifest.
        if len(manifest['packages'].keys()) > 0:
            manifest['total_hash'] = generate_total_hash(manifest)

    return manifest


def generate_consolidated_manifest(published_manifest: Manifest, update_manifest: Manifest) -> Manifest:
    """
    Generates a new manifest, by getting the current manifest and updating it with updated pakages.

    Args:
        published_manifest: The manifest currently stored in S3.
        update_manifest: The manifest generated as a result of building updated packages.
    """
    new_manifest: Manifest = published_manifest.copy()

    for updated_package_name, updated_package_info in update_manifest['packages'].items():
        if updated_package_name not in new_manifest['packages']:
            new_manifest['packages'][updated_package_name] = updated_package_info
        else:
            new_package_info = new_manifest['packages'][updated_package_name].copy()
            new_versions_info = new_package_info.get('versions', []).copy()

            published_versions: list[str] = get_version_strings_from_package_info(new_package_info)

            for updated_version_info in updated_package_info.get('versions', []):
                updated_version = updated_version_info.get('version', None)

                if updated_version is not None and updated_version not in published_versions:
                    new_versions_info.append(updated_version_info)

            new_package_info['versions'] = sorted(new_versions_info, key=lambda x: x['version'])

            new_manifest['packages'][updated_package_name] = new_package_info

    new_manifest['total_hash'] = generate_total_hash(new_manifest)

    return new_manifest


def get_actions_info(metadata_path: str) -> list[ActionInfo]:
    actions_info: list[ActionInfo] = []

    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as file:
            metadata = json.load(file)
            openapi_section = metadata.get('openapi.json', {})
            paths = openapi_section.get('paths', {})
            for path, operations in paths.items():
                for method, details in operations.items():
                    if 'summary' in details:
                        action_info: ActionInfo = {
                            'name': details['summary'],
                            'description': details['description'] if details['description'] else ''
                        }

                        actions_info.append(action_info)
    return actions_info


def generate_total_hash(manifest: Manifest) -> str:
    all_hashes: list[str] = []

    for _, package_info in manifest['packages'].items():
        versions: list[VersionInfo] = package_info.get('versions', [])

        if len(versions) > 0:
            for version_info in versions:
                zip_hash = version_info.get('zip_hash', None)

                if zip_hash is not None:
                    all_hashes.append(zip_hash)

    # Compute a single hash over all the package.hash values
    total_hash = hashlib.sha256()
    for package_hash in sorted(all_hashes):
        total_hash.update(package_hash.encode('utf-8'))

    return total_hash.hexdigest()


def save_manifest(manifest: Manifest, file_path: str) -> None:
    with open(file_path, 'w') as file:
        json.dump(manifest, file, indent=2)