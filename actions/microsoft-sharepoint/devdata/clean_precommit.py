import json
from pathlib import Path
import os


devdata_directory = Path(__file__).absolute().parent


def clean_precommit() -> str:
    # Update the "access_token" in all the json files in devdata directory
    for file in os.listdir(devdata_directory):
        if file.endswith(".json"):
            file_path = devdata_directory / file
            with open(file_path, "r+") as json_file:
                data = json.load(json_file)
                if "token" in data and "access_token" in data["token"]:
                    data["token"]["access_token"] = "<ACCESS_TOKEN>"
                    json_file.seek(0)
                    json.dump(data, json_file, indent=4)
                    json_file.truncate()


if __name__ == "__main__":
    clean_precommit()
