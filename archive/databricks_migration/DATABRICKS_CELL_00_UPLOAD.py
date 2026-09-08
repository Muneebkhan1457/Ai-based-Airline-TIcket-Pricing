# DATABRICKS CELL: Upload External Signals CSV to Volume
# Run this FIRST before Phase 3

print("=" * 70)
print("UPLOAD: External Signals CSV to Databricks Volume")
print("=" * 70)

# Create sample data for testing (in case file not accessible)
# You can either:
# 1. Upload the file manually via Databricks UI
# 2. Use dbutils.fs.put to copy from workspace
# 3. Create Delta table directly from CSV in workspace

# Option: Try to read from local workspace path and write to volume
try:
    # Attempt to read CSV from workspace
    df_signals = spark.read.option("header", True).option("inferSchema", True).csv(
        "/Workspace/Users/[YOUR_USER]/external_signals_export.csv"
    )
    print(f"✅ Read from workspace: {df_signals.count()} rows")
except:
    print("⚠️  Workspace path not found. Using alternative approach...")
    # Will load from uploaded location in next cell

print("\n✅ Ready for Phase 3. Make sure external_signals_export.csv is in Databricks workspace.")
