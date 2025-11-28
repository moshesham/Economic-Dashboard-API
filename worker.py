#!/usr/bin/env python3
"""
Worker entry point - Background job processor.

This is the main entry point for the worker container.
It runs the APScheduler-based job orchestration system.
"""

import logging
import signal
import sys
import time
from typing import Optional

# Configure logging first
from core.logging import setup_logging
setup_logging()

logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main worker entry point."""
    from services.scheduler import get_scheduler, setup_all_jobs
    from core.config import settings
    
    logger.info("=" * 60)
    logger.info("Economic Dashboard Worker Starting")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"Database Path: {settings.DUCKDB_PATH}")
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize scheduler
    scheduler = get_scheduler()
    
    # Configure all jobs
    logger.info("Configuring scheduled jobs...")
    setup_all_jobs(scheduler)
    
    # List configured jobs
    jobs = scheduler.get_jobs()
    logger.info(f"Configured {len(jobs)} jobs:")
    for job in jobs:
        logger.info(f"  - {job['name']}: {job['trigger']}")
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started, waiting for jobs...")
    
    # Run initial data refresh if configured
    if settings.WORKER_RUN_ON_STARTUP:
        logger.info("Running initial data refresh...")
        try:
            scheduler.run_job_now('fred_refresh')
            scheduler.run_job_now('stock_refresh')
            scheduler.run_job_now('options_refresh')
            scheduler.run_job_now('feature_computation')
        except Exception as e:
            logger.error(f"Initial refresh failed: {e}")
    
    # Keep the worker running
    try:
        while True:
            time.sleep(60)
            
            # Log heartbeat every 5 minutes
            if int(time.time()) % 300 < 60:
                jobs = scheduler.get_jobs()
                next_jobs = sorted(
                    [(j['name'], j['next_run']) for j in jobs if j['next_run']],
                    key=lambda x: x[1]
                )[:3]
                logger.info(f"Worker heartbeat - {len(jobs)} jobs scheduled")
                for name, next_run in next_jobs:
                    logger.info(f"  Next: {name} at {next_run}")
                    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()
