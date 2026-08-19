import schedule
import time
import subprocess
import sys
from datetime import datetime
from loguru import logger

logger.add("logs/scheduler.log", rotation="1 day")

def run_pipeline():
    """Run the main scraper"""
    logger.info("🔄 Running scheduled pipeline...")
    try:
        subprocess.run([sys.executable, "src/main.py"], check=True)
        logger.success("✅ Pipeline completed successfully")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}")

# Schedule for 9 AM daily
schedule.every().day.at("09:00").do(run_pipeline)

# Also run once immediately
run_pipeline()

logger.info("⏰ Scheduler started. Running daily at 9:00 AM")

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)
