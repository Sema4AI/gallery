import os
from robocorp.tasks import task
from utils import clear_folders
from environment_builder import build_package_environments

script_dir = os.path.dirname(os.path.abspath(__file__))
gallery_actions_folder = os.path.join(script_dir, "gallery")
environments_folder = os.path.join(script_dir, "environments")

@task
def build_environments():
    clear_folders(environments_folder)

    build_package_environments(gallery_actions_folder, environments_folder)


if __name__ == "__main__":
    build_environments()