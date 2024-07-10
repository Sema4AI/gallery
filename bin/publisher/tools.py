import os
import shutil
import requests
import platform
import subprocess
import json
from utils import get_working_dir

as_version = "0.15.2"
rcc_version = "v18.1.1"


def get_action_server_path() -> str:
    working_dir = get_working_dir()
    system = platform.system().lower()

    if system == 'windows':
        return os.path.join(working_dir, "action-server.exe")
    else:
        return os.path.join(working_dir, "action-server")


def get_rcc_path() -> str:
    working_dir = get_working_dir()
    system = platform.system().lower()

    if system == 'windows':
        return os.path.join(working_dir, "rcc.exe")
    else:
        return os.path.join(working_dir, "rcc")


def get_action_server() -> str:
    action_server_path = get_action_server_path()

    if not os.path.isfile(action_server_path):
        download_action_server()

    return action_server_path


def get_rcc() -> str:
    rcc_path = get_rcc_path()

    if not os.path.isfile(rcc_path):
        download_rcc()

    return rcc_path


def download_action_server() -> str:
    working_dir = get_working_dir()
    system = platform.system().lower()

    if system == "windows":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/windows64/action-server.exe"
        action_server_exe = os.path.join(working_dir, "action-server.exe")
    elif system == "darwin":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/macos64/action-server"
        action_server_exe = os.path.join(working_dir, "action-server")
    elif system == "linux":
        url = f"https://cdn.sema4.ai/action-server/releases/{as_version}/linux64/action-server"
        action_server_exe = os.path.join(working_dir, "action-server")
    else:
        raise Exception("Unsupported OS")

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we raise an error for bad status codes
    with open(action_server_exe, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    if system != "windows":
        os.chmod(action_server_exe, 0o755)

    return action_server_exe


def download_rcc() -> str:
    working_dir = get_working_dir()
    system = platform.system().lower()

    if system == "windows":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/windows64/rcc.exe"
        rcc_exe = os.path.join(working_dir, "rcc.exe")
    elif system == "darwin":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/macos64/rcc"
        rcc_exe = os.path.join(working_dir, "rcc")
    elif system == "linux":
        url = f"https://cdn.sema4.ai/rcc/releases/{rcc_version}/linux64/rcc"
        rcc_exe = os.path.join(working_dir, "rcc")
    else:
        raise Exception("Unsupported OS")

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we raise an error for bad status codes
    with open(rcc_exe, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    if system != "windows":
        os.chmod(rcc_exe, 0o755)

    return rcc_exe


def run_rcc_command(args: list[str], shell: bool = False) -> subprocess.CompletedProcess[str]:
    executable_path = get_rcc()

    if not os.path.isfile(executable_path):
        return subprocess.CompletedProcess(returncode=None, stdout=None, stderr=f"{executable_path} not found")

    return subprocess.run([executable_path, *args], capture_output=True, text=True, shell=shell, cwd=get_working_dir())


def ensure_holotree_shared():
    diagnostics_result = run_rcc_command(['conf', 'diag', '-j'])

    diagnostics = json.loads(diagnostics_result.stdout)

    holotree_shared = diagnostics['details']['holotree-shared']

    if holotree_shared == 'false':
        run_rcc_command(['ht', 'shared', '--enable', '--once'])
        run_rcc_command(['ht', 'init'])