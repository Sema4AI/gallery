#! /usr/bin/env python


import os
import re
import sys
from pathlib import Path

import toml
from requests_oauthlib import OAuth2Session


CONFIG_FILE = Path.home() / ".sema4ai" / "gallery-oauth.toml"
DEFAULT_CONFIG = {
    "hubspot": {
        # Usually stable configuration for the provider.
        "auth_url": "https://app-eu1.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "redirect_uri": "http://localhost:4567",
        # Configuration you may want to override or replace during the prompt.
        "client_id": "05ffd287-41db-4def-8e4d-8fa4ed23bb76",
        "client_secret": "",
    },
}

RE_OAUTH_TYPE = re.compile(r"OAuth2Secret\[.+?list\[([^:]+):", re.DOTALL)
RE_SCOPE = re.compile(r"""Literal\[("|')(?P<scope>[^"']+?)("|')\]""")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow localhost `http` redirects


def _save_config(config: dict):
    with open(CONFIG_FILE, "w") as stream:
        toml.dump(config, stream)


def _make_oauth(pack_conf: dict, *, scopes: list[str]):
    # Init the flow and wait for the `code` to exchange it for a token.
    oauth = OAuth2Session(
        pack_conf["client_id"], redirect_uri=pack_conf["redirect_uri"], scope=scopes
    )
    authorization_url, _ = oauth.authorization_url(pack_conf["auth_url"])

    # Exchange the response with a token.
    print(f"Start this in your browser to initialize the flow: {authorization_url}")
    redirect_response = input("Paste the full redirect URL here: ")
    oauth.fetch_token(
        pack_conf["token_url"],
        include_client_id=True,
        client_secret=pack_conf["client_secret"],
        authorization_response=redirect_response,
    )

    # Now save these tokens in the configuration.
    for token in ("access_token", "refresh_token"):
        pack_conf[token] = oauth.token.get(token)
    print(f"Retrieved access token: {pack_conf['access_token']}")


def make_oauth(pack_path: Path):
    if not CONFIG_FILE.exists():
        _save_config(DEFAULT_CONFIG)
    with open(CONFIG_FILE, "r") as stream:
        config = toml.load(stream)

    # Ask for auth/token URL and client credentials if not already configured.
    pack_conf = config[pack_path.name]
    for entry, value in pack_conf.items():
        value = input(f"{entry} (press enter for {value!r} default): ") or value
        pack_conf[entry] = value
    _save_config(config)

    # Gather all the scopes in order to build the auth URL.
    scopes = set()
    for module in pack_path.rglob("*.py"):
        oauth_types = RE_OAUTH_TYPE.findall(module.read_text())
        for oauth_type in oauth_types:
            for scope_match in RE_SCOPE.finditer(oauth_type):
                scopes.add(scope_match.group("scope"))
    print(f"Gathered the following scopes: {' '.join(scopes)}")

    # Do the flow with the configuration and scopes gathered so far.
    _make_oauth(pack_conf, scopes=scopes)
    _save_config(config)  # saves the just set tokens


def main(args):
    if len(args) != 2:
        print(f"Usage: {args[0]} ACTIONS_DIR")
        return

    packages = {}
    idx = 1
    actions_dir = Path(args[1])
    for conf_file in actions_dir.rglob("package.yaml"):
        has_oauth = False
        for module in conf_file.parent.rglob("*.py"):
            if "OAuth2Secret" in module.read_text():
                has_oauth = True
                break

        if has_oauth:
            packages[idx] = conf_file.parent.name
            idx += 1

    for idx in sorted(packages):
        print(f"{idx}. {packages[idx]}")
    choice = input("Initialize the OAuth2 flow with (choose number): ")
    package = packages[int(choice)]

    make_oauth(actions_dir / package)


if __name__ == "__main__":
    main(sys.argv)
