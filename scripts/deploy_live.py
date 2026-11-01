"""Release the on-demand service without uploading local credentials or data."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT = "dar-traffic"
NUMBER = "693791183501"
REGION = "africa-south1"
SERVICE = "dar-traffic-live"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "Dockerfile.live",
    "cloudbuild.live.yaml",
    "scraper_requirements.txt",
    "config.py",
    "scrape_traffic.py",
    "live_api.py",
)


def gcloud(*args):
    result = subprocess.run(
        [os.getenv("GCLOUD_BIN", "gcloud"), *args, f"--project={PROJECT}", "--quiet"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def image_name():
    digest = hashlib.sha256()
    for name in SOURCE_FILES:
        digest.update((ROOT / name).read_bytes())
    return f"{REGION}-docker.pkg.dev/{PROJECT}/dar-traffic/live:{digest.hexdigest()[:16]}"


def build():
    with tempfile.TemporaryDirectory(prefix="traffic-live-build-") as folder:
        for name in SOURCE_FILES:
            shutil.copy2(ROOT / name, Path(folder) / name)
        identifier = gcloud(
            "builds",
            "submit",
            folder,
            f"--region={REGION}",
            f"--gcs-source-staging-dir=gs://dar-traffic-build-source-{NUMBER}/source",
            f"--service-account=projects/{PROJECT}/serviceAccounts/dar-traffic-build@{PROJECT}.iam.gserviceaccount.com",
            f"--config={Path(folder) / 'cloudbuild.live.yaml'}",
            f"--substitutions=_IMAGE={image_name()}",
            "--async",
            "--format=value(id)",
        )
    print(json.dumps({"build_id": identifier, "image": image_name()}))


def deploy():
    print(
        gcloud(
            "run",
            "deploy",
            SERVICE,
            f"--region={REGION}",
            f"--image={image_name()}",
            f"--service-account=dar-traffic-collector@{PROJECT}.iam.gserviceaccount.com",
            "--cpu=1",
            "--memory=512Mi",
            "--min-instances=0",
            "--max-instances=1",
            "--concurrency=4",
            "--timeout=90s",
            "--allow-unauthenticated",
            "--set-secrets=MAPS_API_KEY=dar-traffic-maps-api-key:latest",
            "--format=value(status.url)",
        )
    )


def retention():
    # This command changes expiry configuration only; it does not provision keys or IAM.
    for collection in ("permitted_observations", "permitted_daily_history", "_live_usage"):
        print(
            gcloud(
                "firestore",
                "fields",
                "ttls",
                "update",
                "expire_at",
                f"--collection-group={collection}",
                "--enable-ttl",
                "--async",
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["build", "deploy", "retention"])
    args = parser.parse_args()
    {"build": build, "deploy": deploy, "retention": retention}[args.phase]()
