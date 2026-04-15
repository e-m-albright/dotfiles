---
tags: [venture/infra, engineering/cloud]
related: ["[[System-Design/Infrastructure-and-Deployment]]"]
sources: ["Notion migration"]
---

# Infrastructure Planning

GCP-native stack recommendation for an early-stage startup. Optimized for speed of iteration, cost control, and not over-engineering day one.

## Philosophy

- Start simple, add complexity only when needed
- Local dev should feel identical to prod
- Preview environments for every PR — non-negotiable for design partner demos
- Terraform everything from day one so you never have to reverse-engineer infra

## Local Development — Docker Compose

Everything runs locally via Docker Compose. One command, full stack.

```yaml
# docker-compose.yml
version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - PUBSUB_EMULATOR_HOST=pubsub:8085
      - GCS_EMULATOR_HOST=http://gcs:4443
      - ENVIRONMENT=local
    volumes:
      - .:/app
      - /app/.venv  # don't mount venv
    depends_on:
      - db
      - pubsub
      - gcs

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  pubsub:
    image: gcr.io/google.com/cloudsdktool/cloud-sdk:latest
    command: gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
    ports:
      - "8085:8085"

  gcs:
    image: fsouza/fake-gcs-server
    command: ["-scheme", "http", "-port", "4443"]
    ports:
      - "4443:4443"
    volumes:
      - gcsdata:/data

volumes:
  pgdata:
  gcsdata:
```

Key points:
- Postgres 16, not some managed thing locally — just run it
- GCP Pub/Sub emulator for async messaging
- fake-gcs-server for object storage
- Mount source code for hot reload, exclude .venv

## Preview Environments — Cloud Run + GitHub Actions

Every PR gets a live preview URL. Design partners can click a link and see the latest.

### GitHub Actions Workflow

```yaml
# .github/workflows/preview.yml
name: Preview Environment

on:
  pull_request:
    types: [opened, synchronize, reopened]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  SERVICE_NAME: app-preview-pr-${{ github.event.pull_request.number }}

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit \
            --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:${{ github.sha }} \
            --timeout=600

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME:${{ github.sha }} \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --memory 512Mi \
            --cpu 1 \
            --max-instances 1 \
            --set-env-vars "ENVIRONMENT=preview,DATABASE_URL=${{ secrets.PREVIEW_DB_URL }}"

      - name: Get URL and comment on PR
        run: |
          URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
          gh pr comment ${{ github.event.pull_request.number }} --body "Preview deployed: $URL"
        env:
          GH_TOKEN: ${{ github.token }}
```

### Cleanup on PR close

```yaml
# .github/workflows/preview-cleanup.yml
name: Cleanup Preview

on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA }}

      - name: Delete Cloud Run service
        run: |
          gcloud run services delete app-preview-pr-${{ github.event.pull_request.number }} \
            --region us-central1 \
            --quiet
```

### Cloud Build config (alternative to GH Actions build step)

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/$_SERVICE_NAME:$COMMIT_SHA', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/$_SERVICE_NAME:$COMMIT_SHA']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '$_SERVICE_NAME'
      - '--image'
      - 'gcr.io/$PROJECT_ID/$_SERVICE_NAME:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'

substitutions:
  _SERVICE_NAME: app

timeout: '600s'
```

## Production Deployment

Cloud Run for the app, Cloud SQL for Postgres, Pub/Sub for async, GCS for storage. All managed, all auto-scaling.

### Terraform

```hcl
# main.tf
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "mycompany-terraform-state"
    prefix = "prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type    = string
  default = "prod"
}

# ---- Cloud SQL (Postgres) ----

resource "google_sql_database_instance" "main" {
  name             = "${var.environment}-postgres"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"  # start small, scale up
    availability_type = "ZONAL"        # HA later when it matters

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "app" {
  name     = "app"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# ---- VPC ----

resource "google_compute_network" "main" {
  name                    = "${var.environment}-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.environment}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.main.id
}

# ---- Cloud Run ----

resource "google_cloud_run_v2_service" "app" {
  name     = "${var.environment}-app"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/app:latest"

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    vpc_access {
      connector = google_vpc_access_connector.main.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}

# ---- VPC Connector (Cloud Run → Cloud SQL) ----

resource "google_vpc_access_connector" "main" {
  name          = "${var.environment}-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name
}

# ---- Pub/Sub ----

resource "google_pubsub_topic" "events" {
  name = "${var.environment}-events"

  message_retention_duration = "86400s"  # 24h
}

resource "google_pubsub_subscription" "events_push" {
  name  = "${var.environment}-events-push"
  topic = google_pubsub_topic.events.name

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.app.uri}/webhooks/pubsub"
  }

  ack_deadline_seconds = 60
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# ---- GCS ----

resource "google_storage_bucket" "data" {
  name     = "${var.project_id}-${var.environment}-data"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# ---- Secret Manager ----

resource "google_secret_manager_secret" "db_url" {
  secret_id = "${var.environment}-db-url"

  replication {
    auto {}
  }
}
```

## Python Abstraction Layer

Thin wrappers so application code doesn't directly import GCP SDKs. Makes testing easy and swapping providers possible (though you probably won't).

```python
# infra/storage.py
"""
Thin abstraction over GCS / local filesystem.
In local dev, uses fake-gcs-server via STORAGE_EMULATOR_HOST.
"""
import os
from google.cloud import storage


def get_client() -> storage.Client:
    emulator = os.environ.get("GCS_EMULATOR_HOST")
    if emulator:
        # fake-gcs-server
        from google.auth.credentials import AnonymousCredentials
        return storage.Client(
            credentials=AnonymousCredentials(),
            project="test",
        )
    return storage.Client()


def upload_blob(bucket_name: str, source: bytes, destination: str) -> str:
    client = get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination)
    blob.upload_from_string(source)
    return f"gs://{bucket_name}/{destination}"


def download_blob(bucket_name: str, source: str) -> bytes:
    client = get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source)
    return blob.download_as_bytes()


def list_blobs(bucket_name: str, prefix: str = "") -> list[str]:
    client = get_client()
    bucket = client.bucket(bucket_name)
    return [b.name for b in bucket.list_blobs(prefix=prefix)]
```

```python
# infra/messaging.py
"""
Thin abstraction over Pub/Sub.
Locally uses the Pub/Sub emulator via PUBSUB_EMULATOR_HOST.
"""
import json
import os
from google.cloud import pubsub_v1


def get_publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def publish(topic_path: str, data: dict, **attrs) -> str:
    publisher = get_publisher()
    message = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_path, message, **attrs)
    return future.result()


def get_subscriber() -> pubsub_v1.SubscriberClient:
    return pubsub_v1.SubscriberClient()
```

```python
# infra/database.py
"""
Database session management. Uses SQLAlchemy async.
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/app")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

## Cost Estimates (Startup Scale)

Starting out, this whole setup runs well under $100/month:
- Cloud Run: ~$0 at low traffic (scale to zero)
- Cloud SQL (db-f1-micro): ~$10/month
- Pub/Sub: free tier covers early usage
- GCS: pennies
- Secret Manager: free tier

Scale up Cloud SQL tier and Cloud Run min instances when you have real traffic.

## What I'd Add Later (Not Now)

- **Cloud Armor** — WAF, DDoS protection. When you have users.
- **Cloud CDN** — When you serve static assets at scale.
- **BigQuery** — When you need analytics beyond what Postgres can handle.
- **Redis (Memorystore)** — When you need caching. Postgres is fine for a while.
- **Monitoring** — Cloud Monitoring + alerting. Set up basic uptime checks early though.
