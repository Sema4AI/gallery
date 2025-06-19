import os
import sys
import json
import subprocess
from pathlib import Path


def start_action_server(action_package_path, port, secrets):
    full_action_path = Path(action_package_path)

    log_path = full_action_path / "action_server.log"

    env = os.environ.copy()
    env["RC_ADD_SHUTDOWN_API"] = "1"

    if secrets:
        parsed_secrets = json.loads(secrets)
        env.update(parsed_secrets)

    start_command = f"action-server start -p {port} > {log_path} 2>&1"
    print(f"Starting server with command: {start_command}")

    subprocess.Popen(
        start_command,
        shell=True,
        env=env,
        cwd=full_action_path,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    print("Subprocess Popen executed.")


if __name__ == "__main__":
    action_package_path = sys.argv[1]
    port = int(sys.argv[2])
    secrets = sys.argv[3] if len(sys.argv) > 3 else ""
    print(f"Running start_server.py with path: {action_package_path}, port: {port}, secrets: {secrets}")
    start_action_server(action_package_path, port, secrets)
