from typing import TypedDict


class ActionInfo(TypedDict):
    name: str
    description: str


class VersionInfo(TypedDict):
    version: str
    description: str
    zip: str
    icon: str
    metadata: str
    readme: str
    changelog: str
    actions: list[ActionInfo]
    python_env_hash: str
    zip_hash: str


class PackageInfo(TypedDict):
    name: str
    versions: list[VersionInfo]


PackagesDict = dict[str, PackageInfo]


class Manifest(TypedDict):
    packages: PackagesDict
    total_hash: str