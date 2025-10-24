import json
import os
import shutil

from actions_manifest import (
    generate_actions_manifest,
    generate_actions_manifest_for_spcs,
    save_manifest,
)
from extractor import extract_all
from robocorp.tasks import task
from tools import get_rcc
from utils import clear_folders


def _parse_package_version(extracted_dir: str) -> tuple[str, str] | None:
    """Parse package name and version from directory name like 'package-name-version'."""
    parts = extracted_dir.split("-")
    if len(parts) < 2:
        return None
    
    # Find the last part that looks like a version (contains dots)
    for i, part in enumerate(parts):
        if "." in part and part.replace(".", "").isdigit():
            package_name = "-".join(parts[:i])
            version = part
            return package_name, version
    
    return None


def _reorganize_extracted_files(temp_gallery_folder: str, reorganized_folder: str) -> dict:
    """Reorganize extracted files into package/version structure."""
    package_versions = {}
    
    for extracted_dir in os.listdir(temp_gallery_folder):
        extracted_path = os.path.join(temp_gallery_folder, extracted_dir)
        if not os.path.isdir(extracted_path):
            continue
            
        parsed = _parse_package_version(extracted_dir)
        if not parsed:
            continue
            
        package_name, version = parsed
        if package_name not in package_versions:
            package_versions[package_name] = []
        package_versions[package_name].append((version, extracted_path))
    
    # Create the reorganized structure
    for package_name, versions in package_versions.items():
        package_folder = os.path.join(reorganized_folder, package_name)
        os.makedirs(package_folder, exist_ok=True)
        
        for version, source_path in versions:
            version_folder = os.path.join(package_folder, version)
            os.makedirs(version_folder, exist_ok=True)
            
            # Copy contents, handling nested directory structure
            for item in os.listdir(source_path):
                item_path = os.path.join(source_path, item)
                if os.path.isdir(item_path):
                    # Check if this directory contains the actual package files
                    if any(f.endswith(".yaml") or f.endswith(".json") for f in os.listdir(item_path)):
                        # Copy contents of nested directory
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
    
    return package_versions


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
        print(
            "Please follow the instructions in s3/README.md to download the S3 content first."
        )
        return

    # Clear existing folders (but keep temp-gallery if it exists and has content)
    clear_folders(zips_folder)
    clear_folders(gallery_actions_folder)

    # Only clear temp folder if it's empty or doesn't exist
    if (
        not os.path.exists(temp_gallery_folder)
        or len(os.listdir(temp_gallery_folder)) == 0
    ):
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
            if item.endswith(".json"):
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
                            if file_name.endswith(".zip"):
                                zip_src = os.path.join(version_path, file_name)
                                zip_dst = os.path.join(
                                    zips_folder, f"{item}-{version_dir}.zip"
                                )

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
    
    package_versions = _reorganize_extracted_files(temp_gallery_folder, reorganized_folder)
    print(f"Reorganized {len(package_versions)} packages with versions")

    # Generate manifests from reorganized folder
    print("Generating standard manifest...")
    manifest = generate_actions_manifest(reorganized_folder, base_url)

    print("Generating SPCS manifest...")
    spcs_manifest = generate_actions_manifest_for_spcs(reorganized_folder)

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
