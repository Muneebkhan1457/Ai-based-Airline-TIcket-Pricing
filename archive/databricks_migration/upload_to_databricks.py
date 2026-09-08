#!/usr/bin/env python3
"""
Upload external_signals_export.csv to Databricks Volume
This should be run as a Databricks notebook cell
"""

import subprocess
import os

# Read the CSV file
csv_path = "/Workspace/Users/user@example.com/external_signals_export.csv"
volume_path = "/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv"

# Copy using dbutils (works in Databricks notebook)
try:
    dbutils.fs.cp("file:///Users/pc/Desktop/data/external_signals_export.csv", f"dbfs:{volume_path}", overwrite=True)
    print(f"✅ Uploaded to {volume_path}")
except Exception as e:
    print(f"Error: {e}")
    print("Trying alternative method...")
