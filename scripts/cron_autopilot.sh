#!/bin/bash
# =============================================================================
# PIA AI Dynamic Ticket Pricing — Automated Cloud Autopilot
# Phase 5: Cloud Scheduler
# Runs scrapers & AI repricing automatically in the background
# =============================================================================

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/home/ubuntu/app/cron_autopilot.log"

echo "==========================================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] Starting scheduled autopilot cycle..." >> "$LOG_FILE"

# Step 1: Trigger ETL refresh (scrape PSO fuel, competitor fares, FX rate)
echo "[$TIMESTAMP] Step 1: Scraping fresh market signals (ETL)..." >> "$LOG_FILE"
ETL_RESP=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST http://localhost:8000/signals/trigger-etl)
echo "$ETL_RESP" >> "$LOG_FILE"

sleep 5

# Step 2: Trigger AI Batch Reprice across all routes using updated market signals
echo "[$TIMESTAMP] Step 2: Running AI Batch Repricer on all routes..." >> "$LOG_FILE"
REPRICE_RESP=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST http://localhost:8000/pricing/batch-reprice)
echo "$REPRICE_RESP" >> "$LOG_FILE"

echo "[$TIMESTAMP] Scheduled autopilot cycle finished successfully!" >> "$LOG_FILE"
echo "==========================================================" >> "$LOG_FILE"
