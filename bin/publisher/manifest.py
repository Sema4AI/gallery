import os
import hashlib
import json
import yaml
from utils import read_file_contents

def read_package_yaml(package_yaml_path):
    if os.path.exists(package_yaml_path):
        with open(package_yaml_path, 'r') as file:
            return yaml.safe_load(file)
    return {}

def read_metadata_json(metadata_path):
    actions = []
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as file:
            metadata = json.load(file)
            openapi_section = metadata.get('openapi.json', {})
            paths = openapi_section.get('paths', {})
            for path, operations in paths.items():
                for method, details in operations.items():
                    if 'summary' in details:
                        actions.append(details['summary'])
    return actions

def generate_manifest(gallery_actions_folder, base_url):
    manifest = {'action_packages': []}
    all_package_hashes = []

    for action_name in os.listdir(gallery_actions_folder):
        action_path = os.path.join(gallery_actions_folder, action_name)
        if os.path.isdir(action_path):
            versions_info = []
            for version_dir in os.listdir(action_path):
                version_path = os.path.join(action_path, version_dir)
                if os.path.isdir(version_path):
                    metadata_path = os.path.join(version_path, "metadata.json")
                    package_yaml_path = os.path.join(version_path, "package.yaml")
                    env_hash_path = os.path.join(version_path, "env.hash")
                    package_hash_path = os.path.join(version_path, "package.hash")

                    package_data = read_package_yaml(package_yaml_path)
                    actions = read_metadata_json(metadata_path)
                    python_env_hash = read_file_contents(env_hash_path)
                    zip_hash = read_file_contents(package_hash_path)

                    version_info = {
                        'version': package_data.get('version', version_dir),
                        'description': package_data.get('description', 'No description provided.'),
                        'zip': f"{base_url}{action_name}/{version_dir}/{action_name}.zip",
                        'icon': f"{base_url}{action_name}/{version_dir}/package.png",
                        'metadata': f"{base_url}{action_name}/{version_dir}/metadata.json",
                        'actions': actions,
                        'python_env_hash': python_env_hash,
                        'zip_hash': zip_hash
                    }
                    versions_info.append(version_info)
                    if zip_hash:
                        all_package_hashes.append(zip_hash)

            if versions_info:
                action_package = {
                    'name': package_data.get('name', action_name),
                    'versions': versions_info
                }
                manifest['action_packages'].append(action_package)

    # Compute a single hash over all the package.hash values
    total_hash = hashlib.sha256()
    for package_hash in sorted(all_package_hashes):
        total_hash.update(package_hash.encode('utf-8'))
    manifest['total_hash'] = total_hash.hexdigest()

    # Write manifest to file
    with open(os.path.join(gallery_actions_folder, "manifest.json"), 'w') as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
