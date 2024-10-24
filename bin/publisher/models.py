from typing import TypedDict


class ActionInfo(TypedDict):
    name: str
    description: str


class ActionVersionInfo(TypedDict):
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
    versions: list[ActionVersionInfo]


class ActionsManifest(TypedDict):
    packages: dict[str, PackageInfo]
    total_hash: str
    organization: str


class LLMModel(TypedDict):
    provider: str
    name: str


class AgentActionPackage(TypedDict):
    name: str
    version: str
    whitelist: list[str]
    organization: str


class AgentVersionInfo(TypedDict):
    version: str
    description: str
    agent_spec: str
    changelog: str
    runbook: str
    architecture: str
    reasoning: str
    model: LLMModel
    knowledge: list[str]
    metadata: dict
    action_packages: list[AgentActionPackage]


class AgentInfo(TypedDict):
    name: str
    versions: list[AgentVersionInfo]


class AgentsManifest(TypedDict):
    agents: dict[str, AgentInfo]
    organization: str
