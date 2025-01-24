from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import TypedDict

logger = getLogger(__name__)

SEMA4AI = "sema4ai"
MYACTIONS = "myactions"


@dataclass
class ActionPackageInFilesystem:
    relative_path: str
    organization: str

    package_yaml_path: Path | None = None
    zip_path: Path | None = None
    package_yaml_contents: str | None = None

    _loaded_yaml: dict | None = None
    _loaded_yaml_error: str | None = None

    referenced_from_agent_spec: bool = False

    def __post_init__(self) -> None:
        if self.zip_path is None:
            assert (
                self.package_yaml_path is not None
            ), "When the zip path is not provided, package_yaml_path is expected to be provided."
        else:
            assert (
                self.package_yaml_path is None
            ), "When zip path is provided, package_yaml_path is not expected."

    def is_zip(self) -> bool:
        return self.zip_path is not None

    def get_as_dict(self) -> dict:
        if self._loaded_yaml is not None:
            return self._loaded_yaml

        if self._loaded_yaml_error is not None:
            raise RuntimeError(self._loaded_yaml_error)

        import yaml

        try:
            if self.is_zip() and self.package_yaml_contents is None:
                raise RuntimeError(
                    "It was not possible to load the agent-spec.yaml from the referenced .zip file."
                )
            if self.package_yaml_contents is not None:
                contents = yaml.safe_load(self.package_yaml_contents)
            else:
                if self.package_yaml_path is None:
                    raise RuntimeError(
                        "Internal error. Either package_yaml_path or package_yaml_contents must be provided"
                    )
                with self.package_yaml_path.open("r") as stream:
                    contents = yaml.safe_load(stream)

            if not isinstance(contents, dict):
                raise RuntimeError("Unable to get contents as dict.")

            self._loaded_yaml = contents
            return self._loaded_yaml
        except Exception as e:
            if self.is_zip():
                logger.error(
                    f"Error getting agent-spec.yaml from {self.zip_path} as yaml."
                )
            else:
                logger.error(f"Error getting {self.package_yaml_path} as yaml.")

            self._loaded_yaml_error = str(e)
            raise

    def get_version(self) -> str | None:
        try:
            contents = self.get_as_dict()
        except Exception:
            return None

        version = contents.get("version")
        return str(version) if version is not None else None

    def get_name(self) -> str | None:
        try:
            contents = self.get_as_dict()
        except Exception:
            return None

        name = contents.get("name")
        return str(name) if name is not None else None


class ActionPackage(TypedDict, total=False):
    name: str | None
    organization: str
    type: str
    version: str | None
    whitelist: str
    path: str
    seen: bool


def _list_actions_from_agent(
    agent_root_dir: Path,
) -> dict[Path, ActionPackageInFilesystem]:
    """
    Helper function to list the action packages from a given agent.

    Args:
        agent_root_dir: This is the agent root directory (i.e.: the directory containing the `agent-spec.yaml`).

    Returns:
        A dictionary where the key is the Path to the action package.yaml or the .zip (if zipped) and the value
        is an object with information about the action package.
    """
    found: dict[Path, ActionPackageInFilesystem] = {}
    actions_dir: Path = (agent_root_dir / "actions").absolute()
    if actions_dir.exists():
        for package_yaml in actions_dir.rglob("package.yaml"):
            package_yaml = package_yaml.absolute()
            relative_path: str = package_yaml.parent.relative_to(actions_dir).as_posix()
            organization = package_yaml.relative_to(actions_dir).parts[0]
            found[package_yaml] = ActionPackageInFilesystem(
                package_yaml_path=package_yaml,
                relative_path=relative_path,
                organization=organization,
            )

        for zip_path in actions_dir.rglob("*.zip"):
            # Skip zips if there is a package.yaml in the same directory.
            if (zip_path.parent / "package.yaml").exists():
                continue

            zip_path = zip_path.absolute()
            package_yaml_contents = _get_package_yaml_from_zip(zip_path)
            relative_path = zip_path.relative_to(actions_dir).as_posix()
            organization = zip_path.relative_to(actions_dir).parts[0]
            found[zip_path] = ActionPackageInFilesystem(
                package_yaml_path=None,
                zip_path=zip_path,
                package_yaml_contents=package_yaml_contents,
                relative_path=relative_path,
                organization=organization,
            )

    return found


def _get_package_yaml_from_zip(zip_path: Path) -> str | None:
    """
    Provides the contents of the package.yaml in the zip or None if it
    couldn't be found.

    Args:
        zip_path: The path to the zip.

    Returns:
        string with the package.yaml contents from the zip or None if
        it couldn't be gotten.
    """
    import zipfile

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            with zip_ref.open("package.yaml") as file:
                content = file.read()
                decoded = content.decode("utf-8")
                return decoded
    except Exception:
        return None


def _update_whitelist(
    action_package: ActionPackage,
    whitelist_map: dict[str, ActionPackage],
    match_key: str,
) -> bool:
    found_package = whitelist_map.get(match_key)

    if found_package and not found_package.get("seen"):
        action_package["whitelist"] = found_package["whitelist"]
        found_package["seen"] = True
        return True

    return False


def _update_agent_spec_with_actions(
    agent_spec: dict,
    action_packages_in_filesystem: list["ActionPackageInFilesystem"],
    whitelist_map: dict[str, ActionPackage],
) -> None:
    new_action_packages: list[ActionPackage] = [
        {
            "name": action_package.get_name(),
            "organization": action_package.organization,
            "version": action_package.get_version(),
            "path": action_package.relative_path,
            "type": "zip" if action_package.zip_path else "folder",
            "whitelist": "",
        }
        for action_package in action_packages_in_filesystem
        if action_package.organization.replace(".", "").lower() in [SEMA4AI, MYACTIONS]
    ]

    missing = []

    # First try to match by path.
    for action_package in new_action_packages:
        if not _update_whitelist(
            action_package,
            whitelist_map,
            match_key=action_package["path"],
        ):
            missing.append(action_package)

    # Couldn't find a path match, try to match by name.
    for action_package in missing:
        if action_package["name"]:
            _update_whitelist(
                action_package, whitelist_map, match_key=action_package["name"]
            )

    # If there was a whitelisted action and it wasn't matched, keep the old config
    # around so that the user can fix it.
    for whitelisted_action in whitelist_map.values():
        if not whitelisted_action.get("seen"):
            new_action_packages.append(whitelisted_action)
            whitelisted_action["seen"] = True

    for action in new_action_packages:
        action.pop("seen", None)

    agent_spec["agent-package"]["agents"][0]["action-packages"] = new_action_packages


def _get_whitelist_mapping(agent_spec: dict) -> dict[str, ActionPackage]:
    whitelist_mapping = {}

    for action_package in agent_spec["agent-package"]["agents"][0].get(
        "action-packages", []
    ):
        if action_package.get("whitelist"):
            if action_package.get("name"):
                whitelist_mapping[action_package["name"]] = action_package

            if action_package.get("path"):
                whitelist_mapping[action_package["path"]] = action_package

    return whitelist_mapping


def _fix_agent_spec(agent_spec: dict) -> None:
    """Updates the provided agent-spec configuration with default values
    where missing, ensuring the structure conforms to the expected format.

    The function compares the `agent_spec` dictionary against a predefined
    `default_spec` structure. For each key in `default_spec`, if the key is
    missing in `agent_spec`, it is added. If the key exists but contains a
    nested dictionary, the function recursively ensures that all default keys
    and values are present within the nested structure.
    """
    default_spec = {
        "agent-package": {
            "spec-version": "v2",
            "agents": [
                {
                    "name": "My Agent",
                    "description": "My Agent description",
                    "model": {"provider": "OpenAI", "name": "gpt-4o"},
                    "version": "0.0.1",
                    "architecture": "agent",
                    "reasoning": "disabled",
                    "runbook": "runbook.md",
                    "action-packages": [],
                    "knowledge": [],
                    "metadata": {"mode": "conversational"},
                }
            ],
        }
    }

    def recursive_update(original: dict, defaults: dict) -> dict:
        for key, value in defaults.items():
            if key not in original:
                original[key] = value
            elif isinstance(value, dict) and isinstance(original.get(key), dict):
                recursive_update(original[key], value)
            elif key == "agents":
                if not isinstance(original[key], list) or len(original[key]) == 0:
                    original[key] = [{}]
                recursive_update(original[key][0], value[0])

        return original

    recursive_update(agent_spec, default_spec)


def update_agent_spec(agent_spec_path: Path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True

    with agent_spec_path.open("r") as file:
        agent_spec = yaml.load(file)

    _fix_agent_spec(agent_spec)

    agent_spec["agent-package"]["agents"][0]["name"] = agent_spec_path.parent.name

    action_packages_in_filesystem = list(
        _list_actions_from_agent(agent_spec_path.parent).values()
    )
    current_whitelist_map = _get_whitelist_mapping(agent_spec)

    _update_agent_spec_with_actions(
        agent_spec,
        action_packages_in_filesystem,
        current_whitelist_map,
    )

    with agent_spec_path.open("w") as file:
        yaml.dump(agent_spec, file)
