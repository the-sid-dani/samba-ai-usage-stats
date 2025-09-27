# AI Usage Analytics Infrastructure
# Terraform configuration for production deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (staging/production)"
  type        = string
  default     = "production"
}

variable "dataset_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "sheets.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ])

  service = each.value
  project = var.project_id

  disable_on_destroy = false
}

# BigQuery dataset
resource "google_bigquery_dataset" "analytics_dataset" {
  dataset_id                  = "ai_usage_analytics"
  friendly_name              = "AI Usage Analytics"
  description                = "Multi-platform AI usage and cost analytics data"
  location                   = var.dataset_location
  default_table_expiration_ms = null # No expiration

  labels = {
    environment = var.environment
    team        = "data-engineering"
    purpose     = "analytics"
  }

  depends_on = [google_project_service.apis]
}

# Service accounts
resource "google_service_account" "pipeline_service_account" {
  account_id   = "ai-usage-pipeline"
  display_name = "AI Usage Analytics Pipeline Service Account"
  description  = "Service account for the daily data pipeline Cloud Run service"
}

resource "google_service_account" "scheduler_service_account" {
  account_id   = "ai-usage-scheduler"
  display_name = "AI Usage Analytics Scheduler Service Account"
  description  = "Service account for Cloud Scheduler to trigger pipeline"
}

# IAM bindings for pipeline service account
resource "google_project_iam_member" "pipeline_bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

resource "google_project_iam_member" "pipeline_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

resource "google_project_iam_member" "pipeline_sheets_readonly" {
  project = var.project_id
  role    = "roles/sheets.readonly"
  member  = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

resource "google_project_iam_member" "pipeline_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

# IAM bindings for scheduler service account
resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler_service_account.email}"
}

# Secret Manager secrets (placeholders - populate with actual values)
resource "google_secret_manager_secret" "cursor_api_key" {
  secret_id = "cursor-api-key"

  labels = {
    environment = var.environment
    purpose     = "api-authentication"
  }

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "anthropic-api-key"

  labels = {
    environment = var.environment
    purpose     = "api-authentication"
  }

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "sheets_service_account" {
  secret_id = "sheets-service-account-key"

  labels = {
    environment = var.environment
    purpose     = "api-authentication"
  }

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# IAM for secret access
resource "google_secret_manager_secret_iam_member" "cursor_api_key_access" {
  secret_id = google_secret_manager_secret.cursor_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "anthropic_api_key_access" {
  secret_id = google_secret_manager_secret.anthropic_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "sheets_key_access" {
  secret_id = google_secret_manager_secret.sheets_service_account.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_service_account.email}"
}

# Cloud Run service
resource "google_cloud_run_service" "pipeline_service" {
  name     = "ai-usage-analytics-pipeline"
  location = var.region

  template {
    spec {
      container_concurrency = 10
      timeout_seconds      = 3600 # 1 hour timeout for data processing
      service_account_name = google_service_account.pipeline_service_account.email

      containers {
        image = "gcr.io/${var.project_id}/ai-usage-analytics-pipeline:latest"

        resources {
          limits = {
            cpu    = "1000m"
            memory = "1Gi"
          }
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "BIGQUERY_DATASET"
          value = google_bigquery_dataset.analytics_dataset.dataset_id
        }

        # API Keys from Secret Manager
        env {
          name = "CURSOR_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.cursor_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "ANTHROPIC_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.anthropic_api_key.secret_id
              key  = "latest"
            }
          }
        }

        ports {
          container_port = 8080
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "10"
        "autoscaling.knative.dev/minScale" = "0"
        "run.googleapis.com/execution-environment" = "gen2"
      }

      labels = {
        environment = var.environment
        team        = "data-engineering"
        component   = "data-pipeline"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

# Cloud Scheduler job for daily execution
resource "google_cloud_scheduler_job" "daily_pipeline" {
  name        = "daily-usage-analytics"
  description = "Daily AI usage analytics data pipeline execution"
  schedule    = "0 6 * * *" # 6 AM PST daily
  time_zone   = "America/Los_Angeles"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.pipeline_service.status[0].url}/run-daily-job"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      mode = "production"
      days = 1
    }))

    oidc_token {
      service_account_email = google_service_account.scheduler_service_account.email
      audience             = google_cloud_run_service.pipeline_service.status[0].url
    }
  }

  retry_config {
    retry_count          = 3
    max_retry_duration   = "600s"
    max_backoff_duration = "300s"
    max_doublings        = 2
  }

  depends_on = [google_project_service.apis]
}

# Outputs
output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.pipeline_service.status[0].url
}

output "bigquery_dataset" {
  description = "BigQuery dataset name"
  value       = google_bigquery_dataset.analytics_dataset.dataset_id
}

output "pipeline_service_account" {
  description = "Pipeline service account email"
  value       = google_service_account.pipeline_service_account.email
}

output "scheduler_job_name" {
  description = "Cloud Scheduler job name"
  value       = google_cloud_scheduler_job.daily_pipeline.name
}