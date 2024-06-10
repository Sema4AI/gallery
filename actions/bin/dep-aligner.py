#! /usr/bin/env python

"""
Dependency alignment tool to be run over action packages and inline their package.yaml
files content.
"""


import itertools
import math
import re
import sys
from pathlib import Path


RE_DIRECTIVE = re.compile(r"^\s*\w+:")

EXPECTED_DEPS = {
    # Conda-forge deps:
    "python": ("3.10.14", 1),
    "python-dotenv": ("1.0.1", 2),
    "uv": ("0.2.10", 3),
    # PyPI deps:
    "sema4ai-actions": ("0.9.1", 1),
    "pydantic": ("2.7.3", 2),
}


def inline_dep(dep: str) -> tuple[str, int]:
    # Checks for known common deps that should be inlined in version and position.
    if not dep.strip():
        return dep, math.inf

    assert dep.strip().startswith("-"), f"invalid dependency entry {dep!r}"
    indent, dep = dep.split("-", 1)
    name, _ = dep.strip().split("=")

    found = EXPECTED_DEPS.get(name)
    if not found:
        # No worries, the dep will preserve its original order if not prioritized.
        return f"{indent}-{dep}", math.inf

    ver, priority = found
    return f"{indent}- {name}={ver}", priority


def inline_deps(data: str) -> str:
    # Inlines Conda and PyPI dependencies based on a common configuration.
    header, deps, footer = [], [], []
    cursor = header
    for line in data.strip().splitlines():
        line = line.rstrip()
        if line == "dependencies:":
            cursor = deps
        elif (
            RE_DIRECTIVE.match(line)
            and line.strip() not in ("conda-forge:", "pypi:")
            and cursor == deps
        ):
            cursor = footer
        cursor.append(line)

    conda_directive, pypi_directive = None, None
    conda_deps, pypi_deps = [], []
    for dep in deps[1:]:
        if "conda-forge:" in dep:
            conda_directive = dep
            cursor = conda_deps
        elif "pypi:" in dep:
            pypi_directive = dep
            cursor = pypi_deps
        else:
            cursor.append(dep)

    deps = [deps[0]]  # keep the "dependencies:" directive indentation.
    deps_map = {conda_directive: conda_deps, pypi_directive: pypi_deps}
    for dep_directive, deps_set in deps_map.items():
        deps_dict = dict([inline_dep(dep) for dep in deps_set])
        inlined_deps = sorted(deps_dict, key=lambda key: deps_dict[key])
        deps.append(dep_directive)
        deps.extend(inlined_deps)

    return "\n".join(itertools.chain(header, deps, footer)) + "\n"


def main(args):
    if len(args) != 2:
        print(f"Usage: {args[0]} ACTIONS_DIR")
        return

    for conf_file in Path(args[1]).rglob("package.yaml"):
        print(f"Processing file: {conf_file}")
        conf_data = conf_file.read_text()
        conf_data = inline_deps(conf_data)
        conf_file.write_text(conf_data)


if __name__ == "__main__":
    main(sys.argv)
