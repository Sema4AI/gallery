import json
import os
import shutil
from typing import Dict, Any

from actions_manifest import (
    generate_actions_manifest,
    generate_actions_manifest_for_spcs,
    save_manifest,
)
from extractor import extract_all
from robocorp.tasks import task
from tools import get_rcc
from utils import clear_folders


@task
def regenerate_manifests():
    """
    Regenerate manifests from local S3 content.
    Reads the actual S3 folder structure and rebuilds manifests with full version history.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    s3_actions_folder = os.path.join(script_dir, "s3", "s3-actions")
    zips_folder = os.path.join(script_dir, "zips")
    temp_gallery_folder = os.path.join(script_dir, "s3", "temp-extracts")
    gallery_actions_folder = os.path.join(script_dir, "gallery")
    base_url = "https://cdn.sema4.ai/gallery/actions/"

    print("Starting manifest regeneration from local S3 content...")

    # Check if S3 content exists
    if not os.path.exists(s3_actions_folder):
        print(f"Error: S3 actions folder not found at {s3_actions_folder}")
        print("Please follow the instructions in s3/README.md to download the S3 content first.")
        return

    # Clear existing folders (but keep temp-gallery if it exists and has content)
    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)
    
    # Only clear temp folder if it's empty or doesn't exist
    if not os.path.exists(temp_gallery_folder) or len(os.listdir(temp_gallery_folder)) == 0:
        clear_folders(temp_gallery_folder)

    # Load whitelist first to know which packages to process
    with open("action_packages_whitelist.json", "r") as f:
        whitelist = json.load(f)
    
    # Combine both standard and spcs whitelists to get all packages we care about
    all_whitelisted_packages = set(whitelist["standard"] + whitelist["spcs"])
    print(f"Processing {len(all_whitelisted_packages)} whitelisted packages")

    # Check if temp folder already has extracted content
    if os.path.exists(temp_gallery_folder) and len(os.listdir(temp_gallery_folder)) > 0:
        print("Using existing extracted packages from temp folder...")
    else:
        # Copy individual zip files from S3 content to zips folder (only whitelisted packages)
        print("Copying zip files from S3 content (whitelisted packages only)...")
        copied_count = 0
        
        for item in os.listdir(s3_actions_folder):
            item_path = os.path.join(s3_actions_folder, item)
            
            # Skip manifest files
            if item.endswith('.json'):
                continue
                
            # Only process whitelisted packages
            if item not in all_whitelisted_packages:
                continue
                
            # Process package directories
            if os.path.isdir(item_path):
                print(f"  Processing package: {item}")
                
                # Look for version subdirectories
                for version_dir in os.listdir(item_path):
                    version_path = os.path.join(item_path, version_dir)
                    
                    if os.path.isdir(version_path):
                        # Look for zip file in this version directory
                        for file_name in os.listdir(version_path):
                            if file_name.endswith('.zip'):
                                zip_src = os.path.join(version_path, file_name)
                                zip_dst = os.path.join(zips_folder, f"{item}-{version_dir}.zip")
                                
                                shutil.copy2(zip_src, zip_dst)
                                copied_count += 1
                                print(f"    Copied: {item}-{version_dir}.zip")

        print(f"Copied {copied_count} zip files from S3 (whitelisted packages only)")

        if copied_count == 0:
            print("No whitelisted packages found in S3 content, exiting...")
            return

        # Extract all packages to temporary folder
        rcc_path = get_rcc()
        print("Extracting packages...")
        extract_all(zips_folder, temp_gallery_folder, rcc_path)

    # Reorganize extracted files into the structure expected by generate_actions_manifest
    print("Reorganizing extracted files for manifest generation...")
    reorganized_folder = os.path.join(script_dir, "s3", "reorganized-extracts")
    clear_folders(reorganized_folder)
    
    # Group extracted versions by package name
    package_versions = {}
    for extracted_dir in os.listdir(temp_gallery_folder):
        extracted_path = os.path.join(temp_gallery_folder, extracted_dir)
        if os.path.isdir(extracted_path):
            # Parse package name and version from directory name
            # Format: package-name-version
            parts = extracted_dir.split('-')
            if len(parts) >= 2:
                # Find the last part that looks like a version (contains dots)
                version_part = None
                package_parts = []
                
                for i, part in enumerate(parts):
                    if '.' in part and part.replace('.', '').isdigit():
                        version_part = part
                        package_parts = parts[:i]
                        break
                
                if version_part and package_parts:
                    package_name = '-'.join(package_parts)
                    if package_name not in package_versions:
                        package_versions[package_name] = []
                    package_versions[package_name].append((version_part, extracted_path))
    
    # Create the reorganized structure
    for package_name, versions in package_versions.items():
        package_folder = os.path.join(reorganized_folder, package_name)
        os.makedirs(package_folder, exist_ok=True)
        
        for version, source_path in versions:
            version_folder = os.path.join(package_folder, version)
            os.makedirs(version_folder, exist_ok=True)
            
            # Copy contents of source_path to version_folder
            # Handle the case where there might be an extra nested directory
            for item in os.listdir(source_path):
                item_path = os.path.join(source_path, item)
                if os.path.isdir(item_path):
                    # If it's a directory, check if it contains the files we need
                    if any(f.endswith('.yaml') or f.endswith('.json') for f in os.listdir(item_path)):
                        # This is likely the actual content directory, copy its contents
                        for nested_item in os.listdir(item_path):
                            nested_item_path = os.path.join(item_path, nested_item)
                            nested_dest = os.path.join(version_folder, nested_item)
                            if os.path.isdir(nested_item_path):
                                shutil.copytree(nested_item_path, nested_dest)
                            else:
                                shutil.copy2(nested_item_path, nested_dest)
                    else:
                        # Regular directory, copy as is
                        shutil.copytree(item_path, os.path.join(version_folder, item))
                else:
                    # Regular file, copy directly
                    shutil.copy2(item_path, os.path.join(version_folder, item))
            
            print(f"  Reorganized: {package_name}/{version}")
    
    print(f"Reorganized {len(package_versions)} packages with versions")

    # Generate manifests from reorganized folder
    print("Generating standard manifest...")
    manifest = generate_actions_manifest(reorganized_folder, base_url)

    print("Generating SPCS manifest...")
    spcs_manifest = generate_actions_manifest_for_spcs(reorganized_folder)

    # Use the whitelist we already loaded

    # Save manifests
    print("Saving manifests...")
    save_manifest(
        manifest,
        os.path.join(gallery_actions_folder, "manifest.json"),
        whitelist["standard"],
    )

    save_manifest(
        spcs_manifest,
        os.path.join(gallery_actions_folder, "manifest_spcs.json"),
        whitelist["spcs"],
    )

    print(f"Manifests regenerated successfully!")
    print(f"Standard manifest: {len(manifest['packages'])} packages")
    print(f"SPCS manifest: {len(spcs_manifest['packages'])} packages")

    # Print version counts for Snowflake packages
    snowflake_packages = [
        "Snowflake Cortex Analyst",
        "Snowflake Cortex Search", 
        "Snowflake Data",
    ]
    for package_name in snowflake_packages:
        if package_name in spcs_manifest["packages"]:
            version_count = len(
                spcs_manifest["packages"][package_name].get("versions", [])
            )
            print(f"{package_name}: {version_count} versions")
        else:
            print(f"{package_name}: NOT FOUND in SPCS manifest")
    
    # Keep temporary folder for future runs (since S3 packages are immutable)
    print("Keeping extracted packages for future runs...")


if __name__ == "__main__":
    regenerate_manifests()
