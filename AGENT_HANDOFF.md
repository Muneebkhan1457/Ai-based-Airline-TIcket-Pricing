# Project Hand-Off & Deployment State

> **Note for the Next AI Agent:**
> - The user wants to learn by doing. Act as a **Mentor and Teacher**.
> - **DO NOT** execute everything blindly or dump raw code without explanation.
> - Explain the concepts, provide exact commands/snippets, and guide the user step-by-step.
> - **Current Next Step:** Start at **Phase 1, Step 5 (Local Docker Container Testing)**, then proceed to **Phase 2 (AWS RDS PostgreSQL Migration)**.

---

## 1. Project Overview & Architecture
This project is an **AI-Driven Airline Dynamic Ticket Pricing System** built for PIA (Pakistan International Airlines) routes.

* **Backend:** FastAPI ([api/main.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/api/main.py), [api/services.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/api/services.py))
* **Frontend:** Streamlit ([ui/app.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/ui/app.py))
* **Pricing Engine:** Elasticity modeling, guardrails, and revenue optimizer ([pricing_engine/](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/pricing_engine/))
* **ML Model & Tracking:** LightGBM with monotonic constraints; tracked on **DagsHub MLflow**; large datasets tracked with **DVC**
* **Target Cloud Architecture:**
  * **Database:** AWS RDS PostgreSQL (currently running on local SQLite `Data_load/flight.db`)
  * **Compute / Host:** AWS EC2 (Ubuntu Linux with Docker & Docker Compose)
  * **Registry:** AWS ECR (Elastic Container Registry)
  * **CI/CD:** GitHub Actions (`.github/workflows/deploy.yml`)
  * **Scheduler:** Automated background cron / worker for scraping & repricing

---

## 2. Current Implementation Status

### ✅ What is 100% Completed
1. **Model Pipeline & MLflow Tracking:**
   * Tracking URI and credentials configured in `.env` pointing to DagsHub.
   * [models/train_demand_model.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/models/train_demand_model.py) logs model runs, metrics ($R^2$, RMSE), and sets the registered model alias `champion`.
2. **Local Pricing Engine & Guardrails:**
   * Complete pricing optimizer with price floors, ceilings, competitor multipliers, and capacity urgency logic.
3. **Automated Unit Tests:**
   * **11 of 11 tests passing** (`pytest` passing for API and ETL modules).
4. **Scraper Adaptations for Containers:**
   * [Data_load/scrapers/scrape_competitor_prices.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/Data_load/scrapers/scrape_competitor_prices.py) uses mock competitor data so Docker containers do not need heavy Playwright / Chromium headless browser binaries.
5. **Docker Infrastructure Files (Written & Configured):**
   * [requirements.txt](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/requirements.txt): Pruned to clean lightweight dependencies.
   * [Dockerfile.api](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/Dockerfile.api): Python 3.11-slim, installs `libgomp1`, exposes port `8000`.
   * [Dockerfile.ui](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/Dockerfile.ui): Python 3.11-slim, runs Streamlit on port `8501`.
   * [docker-compose.yml](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/docker-compose.yml): Networks API and UI together (`API_URL=http://api:8000`).
   * [.dockerignore](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/.dockerignore): Configured to ignore virtual environments, cache, and raw scraping dumps.
   * [ui/app.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/ui/app.py): Updated to read `API_URL` dynamically from environment variables.

---

## 3. Deployment Roadmap & What Is Left

### 🟡 Phase 1: Local Dockerization (85% Done — Immediate Starting Point)
- [x] Step 1: Clean `requirements.txt`.
- [x] Step 2: `Dockerfile.api`.
- [x] Step 3: `Dockerfile.ui`.
- [x] Step 4: `docker-compose.yml`.
- [ ] **Step 5 (NEXT ACTION):** Start Docker Desktop on Windows, run `docker compose up --build`, and verify:
  * FastAPI docs at `http://localhost:8000/docs`
  * Streamlit UI at `http://localhost:8501`
- [ ] **Git Commit:** Stage and commit Docker files and modified scripts.

---

### ⚪ Phase 2: Database Migration to AWS RDS PostgreSQL (0% Done)
*Current state: Data is in SQLite `Data_load/flight.db` (15,000 flights, 62 signal entries, 80 price history rows).*
- [ ] **Step 1:** User creates an AWS Account / logs into AWS Console.
- [ ] **Step 2:** Provision an Amazon RDS PostgreSQL database instance (`db.t3.micro` or `db.t4g.micro`, Free Tier).
- [ ] **Step 3:** Configure AWS RDS Security Group inbound rule to allow port `5432` from local IP / EC2.
- [ ] **Step 4:** Add `psycopg2-binary` to `requirements.txt` and add `DATABASE_URL` to `.env`.
- [ ] **Step 5:** Refactor [api/services.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/api/services.py) and [scheduler/jobs.py](file:///c:/Users/pc/Desktop/AI%20Dynamic%20Ticket%20Pricing/scheduler/jobs.py):
  * Replace `sqlite3.connect` with PostgreSQL connection handling (supports `DATABASE_URL`).
  * Replace SQLite `?` parameter markers with Postgres `%s` markers.
- [ ] **Step 6:** Write and run a migration script (e.g., `scripts/migrate_sqlite_to_rds.py`) to transfer tables and rows from `flight.db` to AWS RDS PostgreSQL.

---

### ⚪ Phase 3: Cloud Server Setup on AWS EC2 (0% Done)
- [ ] **Step 1:** Launch an Amazon EC2 instance (Ubuntu 22.04 / 24.04 LTS, `t2.micro` or `t3.small`).
- [ ] **Step 2:** Configure EC2 Security Groups:
  * Port 22 (SSH)
  * Port 8000 (FastAPI Backend)
  * Port 8501 (Streamlit Frontend)
- [ ] **Step 3:** SSH into EC2 instance from local terminal using `.pem` key.
- [ ] **Step 4:** Install Docker and Docker Compose plugin on Ubuntu EC2.
- [ ] **Step 5:** Clone repository onto EC2, supply production `.env`, and test `docker compose up -d`.

---

### ⚪ Phase 4: Automated CI/CD with GitHub Actions (0% Done)
- [ ] **Step 1:** Set up AWS ECR (Elastic Container Registry) repositories for API and UI images.
- [ ] **Step 2:** Add GitHub Repository Secrets:
  * `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
  * `DAGSHUB_USER`, `DAGSHUB_TOKEN`
  * `EC2_SSH_KEY`, `EC2_HOST`
- [ ] **Step 3:** Write `.github/workflows/deploy.yml`:
  1. Checkout code.
  2. Run unit tests (`pytest`).
  3. Retrain model & verify evaluation thresholds.
  4. Build API and UI Docker images.
  5. Push images to AWS ECR.
  6. SSH into EC2, pull latest images, and restart containers without downtime.

---

### ⚪ Phase 5: Cloud Scheduler & Autopilot (10% Done)
*Current state: Local scheduler logic exists in `scheduler/run_autopilot.py` and `scheduler/jobs.py`.*
- [ ] **Step 1:** Add a background worker service in `docker-compose.yml` or set up a Linux `cron` / `systemd` timer on EC2.
- [ ] **Step 2:** Configure the scheduler to run `scheduler/jobs.py` (scrapers + ETL) and trigger dynamic repricing every few hours.
- [ ] **Step 3:** Verify automated database updates and live price reflections in the Streamlit UI.

---

## 4. Key Local File Locations

| File / Folder | Purpose |
| :--- | :--- |
| `CLOUD_MIGRATION_ROADMAP.md` | Master roadmap document outlining cloud objectives. |
| `Dockerfile.api` | Docker configuration for FastAPI backend. |
| `Dockerfile.ui` | Docker configuration for Streamlit frontend. |
| `docker-compose.yml` | Multi-container composition uniting API and UI. |
| `requirements.txt` | Production Python dependencies. |
| `Data_load/flight.db` | Local SQLite database (source for future RDS migration). |
| `api/services.py` | Core API data layer, model inference, and DB queries. |
| `ui/app.py` | Interactive pricing dashboard. |
| `models/train_demand_model.py` | Training script with MLflow logging. |
| `scheduler/run_autopilot.py` | Autonomous signal scraper & delta repricing daemon. |
| `.env` | Environment configuration (DagsHub MLflow credentials). |

---

## 5. Instructions for the Agent Starting the Next Session

When the user starts the next session and gives you this file:
1. **Acknowledge the current position:** Phase 1 is 85% complete.
2. **First Question to User:** Ask the user if Docker Desktop is running so you can test `docker compose up --build` together, OR if they are ready to jump directly to **Phase 2 (AWS RDS PostgreSQL setup)**.
3. Guide the user step-by-step with clear, concise instructions and verify each step before moving forward.
