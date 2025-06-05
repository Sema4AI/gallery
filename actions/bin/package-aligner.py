import os
import sys
from datetime import datetime

from ruamel.yaml import YAML

EXPECTED_DEPS = {
    "python": "3.11.11",
    "python-dotenv": "1.1.0",
    "uv": "0.6.11",
    "sema4ai-actions": "1.3.8",
    "requests": "2.32.3",
    "pydantic": "2.11.2",
}

IGNORE = [
    "output/",
    "venv/",
    ".venv/",
    "temp/",
    ".use",
    ".vscode",
    ".DS_Store",
    "*.pyc",
    "*.zip",
    ".env",
    ".project",
    ".pydevproject",
    ".env",
    "metadata.json",
    "./**/.env",
]


def update_dependencies(deps):
    """Update dependencies in the package.yaml file"""
    updated_deps = {}
    for section, deps_list in deps.items():
        updated_deps[section] = []
        for dep in deps_list:
            dep_name = dep.split("=")[0].strip()
            if dep_name in EXPECTED_DEPS:
                updated_deps[section].append(f"{dep_name}={EXPECTED_DEPS[dep_name]}")
            else:
                updated_deps[section].append(dep)
    return updated_deps


def update_changelog(file_path, new_version):
    """Update the CHANGELOG.md file by adding the new version entry at the top"""
    changelog_path = os.path.join(os.path.dirname(file_path), "CHANGELOG.md")
    date_today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(changelog_path):
        return

    with open(changelog_path, "r") as file:
        changelog = file.read()

    # Prepare the new changelog entry
    new_entry = f"## [{new_version}] - {date_today}\n\n### Changed\n\n- Dependency versions updated\n\n"

    # Check if the first version block exists
    first_version_index = changelog.find("## [")
    if first_version_index != -1:
        # Insert the new changelog entry before the first version block
        changelog = (
            changelog[:first_version_index]
            + new_entry
            + changelog[first_version_index:]
        )

    # If no version block is found, simply prepend the new entry
    else:
        changelog = new_entry + changelog

    with open(changelog_path, "w") as file:
        file.write(changelog)


def update_version(version_str, bump_type):
    """Update the version based on the bump type: 'patch', 'minor', or 'major'."""
    # Split the version into major, minor, and patch components
    major, minor, patch = map(int, version_str.split("."))

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0  # Reset patch to 0
    elif bump_type == "major":
        major += 1
        minor = 0  # Reset minor and patch to 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

    # Rebuild the version string
    new_version = f"{major}.{minor}.{patch}"
    return new_version


def process_package_yaml(file_path, bump_type=None):
    """Reads and updates package.yaml with correct indentation, dependencies, and optional version bump"""
    print(f"Processing {file_path}...")
    yaml = YAML()
    yaml.preserve_quotes = True  # Keep formatting
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 500

    with open(file_path, "r") as file:
        content = yaml.load(file)  # Fixed: Changed safe_load to load

    # Update dependencies
    if "dependencies" in content:
        content["dependencies"] = update_dependencies(content["dependencies"])

    # Ensure a blank line after dependencies if it's not already there
    if "external-endpoints" in content:
        content.yaml_set_comment_before_after_key("external-endpoints", before="\n")
    else:
        # Add a newline after the dependencies section if no external-endpoints
        content.yaml_set_comment_before_after_key("packaging", before="\n")

    # Bump version if a bump type is provided
    if bump_type and "version" in content:
        current_version = content["version"]
        new_version = update_version(current_version, bump_type)
        content["version"] = new_version

        update_changelog(file_path, new_version)

    # Write back the correctly formatted file
    with open(file_path, "w") as file:
        yaml.dump(content, file)


def update_gitignore(file_path):
    """Updates .gitignore files by appending missing IGNORE patterns, without overwriting existing content."""
    print(f"Processing {file_path}...")

    # Read the existing content from the .gitignore file
    with open(file_path, "r") as file:
        existing_lines = file.readlines()

    # Open the file in append mode, but add new patterns if they aren't already present
    with open(file_path, "a") as file:
        for line in IGNORE:
            # Only write the line if it's not already in the file
            if line.strip() and line.strip() not in [l.strip() for l in existing_lines]:
                file.write(f"{line}\n")


def main():
    """Process all package.yaml and .gitignore files and optionally bump version"""
    bump_type = None
    if len(sys.argv) > 2:
        bump_type = sys.argv[2]

    for root, dirs, files in os.walk("."):
        for file in files:
            if file == "package.yaml":
                file_path = os.path.join(root, file)
                process_package_yaml(file_path, bump_type)
                update_gitignore(os.path.join(root, ".gitignore"))


if __name__ == "__main__":
    main()
