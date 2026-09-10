# Cloud Migration & CI/CD Roadmap

> **Note to Future AI Agents:** The user wants to learn by doing. You must act as a **Mentor and Teacher**. DO NOT write the code for them or execute the steps automatically unless explicitly asked. Explain the concepts, provide code snippets or commands, and wait for the user to execute them and confirm completion before moving to the next step.

This document serves as the master roadmap to migrate the Local Dynamic Ticket Pricing Engine to a fully automated, cloud-hosted architecture on AWS.

## Architecture Overview
- **Frontend:** Streamlit (Deployed on AWS EC2 via Docker)
- **Backend:** FastAPI (Deployed on AWS EC2 via Docker)
- **Database:** PostgreSQL (Managed by AWS RDS)
- **Model Tracking:** DagsHub / MLflow (Already configured)
- **CI/CD:** GitHub Actions (Automates training, testing, building, and deployment)

---

## Phase 1: Local Dockerization 🐳
*Goal: Package the API and Frontend into portable Docker containers on your local machine.*

- [ ] **Step 1:** Generate a clean `requirements.txt` using `uv`.
- [ ] **Step 2:** Write `Dockerfile.api` for the FastAPI backend.
- [ ] **Step 3:** Write `Dockerfile.ui` for the Streamlit dashboard.
- [ ] **Step 4:** Write `docker-compose.yml` to run both services together locally.
- [ ] **Step 5:** Test the Docker containers locally to ensure they talk to each other.

---

## Phase 2: Database Migration (AWS RDS) 🗄️
*Goal: Move from local SQLite to a robust, cloud-hosted PostgreSQL database.*

- [ ] **Step 1:** Create an AWS Account (if not already done).
- [ ] **Step 2:** Provision an Amazon RDS PostgreSQL database instance.
- [ ] **Step 3:** Configure AWS Security Groups to allow your local IP to connect to the database.
- [ ] **Step 4:** Update `api/services.py` and `scheduler/jobs.py` to use `psycopg2` and connect to the Postgres connection string instead of SQLite.
- [ ] **Step 5:** Write a temporary python script to migrate the existing data from your local `flight.db` to the new AWS RDS database.

---

## Phase 3: Cloud Server Setup (AWS EC2) ☁️
*Goal: Set up the always-on cloud server that will host your code.*

- [ ] **Step 1:** Launch an Amazon EC2 instance (Ubuntu Server, t2.micro or t3.small).
- [ ] **Step 2:** Configure Security Groups to open Port 8000 (API), Port 8501 (Streamlit), and Port 22 (SSH).
- [ ] **Step 3:** SSH into the EC2 instance from your local terminal.
- [ ] **Step 4:** Install Docker and Docker Compose on the EC2 instance.
- [ ] **Step 5:** Test a manual deployment by pulling your code via Git and running `docker-compose up`.

---

## Phase 4: Automated CI/CD (GitHub Actions) 🤖
*Goal: Automate model retraining and code deployment whenever you push to GitHub.*

- [ ] **Step 1:** Set up an Amazon ECR (Elastic Container Registry) to store your Docker images securely.
- [ ] **Step 2:** Configure **GitHub Secrets** (Add AWS Access Keys, DagsHub credentials, and EC2 SSH keys). *Note: These are 100% private and encrypted.*
- [ ] **Step 3:** Write `.github/workflows/deploy.yml`. The pipeline will:
    1. Checkout the code.
    2. Run `train_demand_model.py` (which evaluates and registers the model to MLflow).
    3. Build the Docker images for API and UI.
    4. Push the images to AWS ECR.
    5. SSH into the EC2 instance, pull the new images, and restart the Docker containers.
- [ ] **Step 4:** Push a code change to `main` and watch the pipeline run from start to finish!

---

## Phase 5: Cloud Scheduler ⏱️
*Goal: Automate the ETL scrapers and Repricer to run without human intervention.*

- [ ] **Step 1:** Update the `docker-compose.yml` to include a third container dedicated to running cron jobs, OR set up a Linux `cron` job directly on the EC2 instance.
- [ ] **Step 2:** Configure the scheduler to run `run_all_jobs()` every few hours.
- [ ] **Step 3:** Verify that the database updates automatically and the Streamlit dashboard reflects the new prices.

---
**Status:** Ready to begin Phase 1.
