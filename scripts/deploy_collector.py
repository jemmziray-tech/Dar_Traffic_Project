"""Deploy the collector to Google Cloud without uploading local credentials."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

PROJECT = "dar-traffic"
NUMBER = "693791183501"
REGION = "africa-south1"
SCHEDULER_REGION = "europe-west1"
JOB = "dar-traffic-collector"
REPOSITORY = "dar-traffic"
SECRET = "dar-traffic-maps-api-key"
BUCKET = f"dar-traffic-build-source-{NUMBER}"
RUNTIME = f"dar-traffic-collector@{PROJECT}.iam.gserviceaccount.com"
BUILDER = f"dar-traffic-build@{PROJECT}.iam.gserviceaccount.com"
INVOKER = f"dar-traffic-scheduler@{PROJECT}.iam.gserviceaccount.com"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = [
    "Dockerfile.collector",
    "cloudbuild.collector.yaml",
    "scraper_requirements.txt",
    "config.py",
    "scrape_traffic.py",
]


def gcloud(*arguments, input_text=None, missing_ok=False):
    print(f"Google Cloud: {' '.join(arguments[:3])}", flush=True)
    command = [
        os.environ.get("GCLOUD_BIN", "gcloud"),
        *arguments,
        f"--project={PROJECT}",
        "--quiet",
    ]
    result = subprocess.run(command, input=input_text, text=True, capture_output=True)
    if result.returncode:
        if missing_ok and any(
            marker in result.stderr for marker in ("NOT_FOUND", "not found", "does not exist")
        ):
            return None
        raise RuntimeError(f"gcloud {' '.join(arguments[:3])} failed: {result.stderr}")
    return result.stdout.strip()


def prepare():
    project = json.loads(gcloud("projects", "describe", PROJECT, "--format=json(projectNumber)"))
    if str(project["projectNumber"]) != NUMBER:
        raise RuntimeError("Unexpected Google Cloud project number")
    gcloud(
        "services",
        "enable",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com",
        "cloudscheduler.googleapis.com",
        "secretmanager.googleapis.com",
        "apikeys.googleapis.com",
    )
    for name in ("dar-traffic-build", "dar-traffic-scheduler"):
        email = f"{name}@{PROJECT}.iam.gserviceaccount.com"
        if gcloud("iam", "service-accounts", "describe", email, missing_ok=True) is None:
            gcloud("iam", "service-accounts", "create", name, f"--display-name={name}")
    if (
        gcloud(
            "artifacts",
            "repositories",
            "describe",
            REPOSITORY,
            f"--location={REGION}",
            missing_ok=True,
        )
        is None
    ):
        gcloud(
            "artifacts",
            "repositories",
            "create",
            REPOSITORY,
            f"--location={REGION}",
            "--repository-format=docker",
        )
    gcloud(
        "artifacts",
        "repositories",
        "add-iam-policy-binding",
        REPOSITORY,
        f"--location={REGION}",
        f"--member=serviceAccount:{BUILDER}",
        "--role=roles/artifactregistry.writer",
    )
    if gcloud("storage", "buckets", "describe", f"gs://{BUCKET}", missing_ok=True) is None:
        gcloud(
            "storage",
            "buckets",
            "create",
            f"gs://{BUCKET}",
            f"--location={REGION}",
            "--uniform-bucket-level-access",
        )
    gcloud(
        "storage",
        "buckets",
        "add-iam-policy-binding",
        f"gs://{BUCKET}",
        f"--member=serviceAccount:{BUILDER}",
        "--role=roles/storage.objectViewer",
    )
    for role in ("roles/logging.logWriter", "roles/serviceusage.serviceUsageConsumer"):
        gcloud(
            "projects",
            "add-iam-policy-binding",
            PROJECT,
            f"--member=serviceAccount:{BUILDER}",
            f"--role={role}",
            "--condition=None",
        )
    if gcloud("secrets", "describe", SECRET, missing_ok=True) is None:
        gcloud("secrets", "create", SECRET, "--replication-policy=automatic")
    versions = json.loads(
        gcloud(
            "secrets", "versions", "list", SECRET, "--filter=state=ENABLED", "--format=json(name)"
        )
    )
    if not versions:
        keys = json.loads(
            gcloud(
                "services",
                "api-keys",
                "list",
                "--filter=displayName=dar-traffic-cloud-collector",
                "--format=json(name)",
            )
        )
        if not keys:
            gcloud(
                "services",
                "api-keys",
                "create",
                "--display-name=dar-traffic-cloud-collector",
                "--api-target=service=distance-matrix-backend.googleapis.com",
                "--format=value(name)",
            )
            for _ in range(10):
                keys = json.loads(
                    gcloud(
                        "services",
                        "api-keys",
                        "list",
                        "--filter=displayName=dar-traffic-cloud-collector",
                        "--format=json(name)",
                    )
                )
                if keys:
                    break
                time.sleep(2)
        if not keys:
            raise RuntimeError(
                "Maps key creation is still pending; rerun prepare after it completes"
            )
        key_name = keys[0]["name"]
        key = gcloud(
            "services", "api-keys", "get-key-string", key_name, "--format=value(keyString)"
        )
        if not key:
            raise RuntimeError("Maps key provisioning returned no credential")
        gcloud("secrets", "versions", "add", SECRET, "--data-file=-", input_text=key)
    gcloud(
        "secrets",
        "add-iam-policy-binding",
        SECRET,
        f"--member=serviceAccount:{RUNTIME}",
        "--role=roles/secretmanager.secretAccessor",
    )
    print("Collector resources and scoped permissions prepared. No secret values displayed.")


def image_name():
    digest = hashlib.sha256()
    for name in SOURCE_FILES:
        digest.update((ROOT / name).read_bytes())
    return f"{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/collector:{digest.hexdigest()[:16]}"


def build():
    with tempfile.TemporaryDirectory(prefix="traffic-build-") as folder:
        for name in SOURCE_FILES:
            shutil.copy2(ROOT / name, Path(folder) / name)
        identifier = gcloud(
            "builds",
            "submit",
            folder,
            f"--region={REGION}",
            f"--gcs-source-staging-dir=gs://{BUCKET}/source",
            f"--service-account=projects/{PROJECT}/serviceAccounts/{BUILDER}",
            f"--config={Path(folder) / 'cloudbuild.collector.yaml'}",
            f"--substitutions=_IMAGE={image_name()}",
            "--async",
            "--format=value(id)",
        )
    print(json.dumps({"build_id": identifier, "image": image_name(), "region": REGION}))


def deploy():
    gcloud(
        "run",
        "jobs",
        "deploy",
        JOB,
        f"--region={REGION}",
        f"--image={image_name()}",
        f"--service-account={RUNTIME}",
        "--tasks=1",
        "--parallelism=1",
        "--cpu=1",
        "--memory=512Mi",
        "--max-retries=0",
        "--task-timeout=480s",
        f"--set-secrets=MAPS_API_KEY={SECRET}:latest",
    )
    gcloud(
        "run",
        "jobs",
        "add-iam-policy-binding",
        JOB,
        f"--region={REGION}",
        f"--member=serviceAccount:{INVOKER}",
        "--role=roles/run.invoker",
    )
    print("Cloud Run job deployed. Scheduler is not enabled by this phase.")


def schedule():
    exists = (
        gcloud(
            "scheduler", "jobs", "describe", JOB, f"--location={SCHEDULER_REGION}", missing_ok=True
        )
        is not None
    )
    gcloud(
        "scheduler",
        "jobs",
        "update" if exists else "create",
        "http",
        JOB,
        f"--location={SCHEDULER_REGION}",
        "--schedule=0,30 6-22 * * *",
        "--time-zone=Africa/Dar_es_Salaam",
        f"--uri=https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/jobs/{JOB}:run",
        "--http-method=POST",
        f"--oauth-service-account-email={INVOKER}",
        "--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform",
        "--headers=Content-Type=application/json",
        "--message-body={}",
        "--max-retry-attempts=0",
        "--attempt-deadline=30s",
    )
    print("Cloud Scheduler enabled: every 30 minutes, 06:00-22:30 EAT.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "build", "deploy", "schedule"])
    args = parser.parse_args()
    {"prepare": prepare, "build": build, "deploy": deploy, "schedule": schedule}[args.phase]()
