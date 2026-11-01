"""Publish the checked-in Firestore rules using an existing Cloud SDK login."""

import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT = "dar-traffic"
ROOT = Path(__file__).resolve().parents[1]


def main():
    token = subprocess.run(
        [os.getenv("GCLOUD_BIN", "gcloud"), "auth", "print-access-token", "--project=" + PROJECT],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    base = "https://firebaserules.googleapis.com/v1/projects/" + PROJECT

    def request(method, url, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        req = Request(
            url,
            data=payload,
            method=method,
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "x-goog-user-project": PROJECT,
            },
        )
        try:
            with urlopen(req, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(error.read().decode()) from None

    rules = request(
        "POST",
        base + "/rulesets",
        {
            "source": {
                "files": [
                    {
                        "name": "firestore.rules",
                        "content": (ROOT / "firestore.rules").read_text(),
                    }
                ]
            }
        },
    )
    release = {
        "name": "projects/" + PROJECT + "/releases/cloud.firestore",
        "rulesetName": rules["name"],
    }
    result = request(
        "PATCH",
        base + "/releases/cloud.firestore",
        {"release": release, "updateMask": "ruleset_name"},
    )
    print(json.dumps({"release": result["name"], "ruleset": result["rulesetName"]}))


if __name__ == "__main__":
    main()
