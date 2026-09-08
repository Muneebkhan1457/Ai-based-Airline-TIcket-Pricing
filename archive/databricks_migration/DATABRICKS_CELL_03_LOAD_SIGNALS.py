# DATABRICKS CELL: PHASE 3 (FIXED) - Load Real External Signals
from pyspark.sql.functions import col

print("=" * 70)
print("PHASE 3 (FIXED): LOAD REAL EXTERNAL SIGNALS")
print("=" * 70)

# Path to external signals CSV (uploaded to volume)
volume_path = "/Volumes/airline_daw/pia_pricing/pia_data/external_signals.csv"

try:
    df_signals_real = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(volume_path)
    )
    
    # Convert recorded_date to timestamp
    df_signals_real = df_signals_real.withColumn(
        "recorded_date", 
        col("recorded_date").cast("timestamp")
    )
    
    # Save to Delta table
    df_signals_real.write.format("delta").mode("overwrite").saveAsTable(
        "airline_daw.pia_pricing.external_signals"
    )
    
    print(f"✅ Real signals loaded and saved to Delta table")
    print(f"   Total rows: {df_signals_real.count()}")
    print(f"   Signal types: {df_signals_real.select('signal_type').distinct().count()} types")
    
    # Show distribution
    print("\n📊 SIGNAL DISTRIBUTION:")
    df_signals_real.groupby("signal_type", "route").count().show()
    
except Exception as e:
    print(f"❌ Error loading signals: {e}")
    print("Make sure external_signals.csv is uploaded to the volume path.")
