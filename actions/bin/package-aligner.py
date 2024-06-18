#! /usr/bin/env python

"""AI Actions package alignment tool to be run over action packages.

It inlines their package.yaml files content, the git-ignored files and more.
"""


import itertools
import re
import sys
from pathlib import Path


# package.yaml
RE_DIRECTIVE = re.compile(r"^\s*\w+:")
EXPECTED_DEPS = {
    # Conda-forge deps:
    "python": ("3.10.14", 1),
    "python-dotenv": ("1.0.1", 2),
    "uv": ("0.2.6", 3),
    # PyPI deps:
    "sema4ai-actions": ("0.9.2", 1),
    "pydantic": ("2.7.4", 2),
}
LOWEST_PRIO = sys.maxsize

# .gitignore
IGNORE = {
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
}
NO_IGNORE = set({})


def inline_dep(dep: str) -> tuple[str, int]:
    # Checks for known common deps that should be inlined in version and position.
    if not dep.strip():
        return dep, LOWEST_PRIO

    assert dep.strip().startswith("-"), f"invalid dependency entry {dep!r}"
    indent, dep = dep.split("-", 1)
    name, _ = dep.strip().split("=")

    found = EXPECTED_DEPS.get(name)
    if not found:
        # No worries, the dep will preserve its original order if not prioritized.
        return f"{indent}-{dep}", LOWEST_PRIO

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


def inline_ignore(data: str) -> str:
    ignore = set(data.strip().splitlines())
    if not_ignore := (ignore & NO_IGNORE):
        print(f"Warning! Detected inappropriate ignore(s): {not_ignore} (removing)")
        ignore -= not_ignore
    ignore |= IGNORE
    return "\n".join(sorted(ignore)) + "\n"


def main(args):
    if len(args) != 2:
        print(f"Usage: {args[0]} ACTIONS_DIR")
        return

    alignments = {
        "package.yaml": inline_deps,
        ".gitignore": inline_ignore,
    }
    for conf_file in Path(args[1]).rglob("package.yaml"):
        for source_file, inliner in alignments.items():
            source_path = conf_file.parent / source_file
            print(f"Processing file: {source_path}")
            misaligned_data = source_path.read_text()
            inlined_data = inliner(misaligned_data)
            source_path.write_text(inlined_data)


if __name__ == "__main__":
    main(sys.argv)
