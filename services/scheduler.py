"""
APScheduler-based job orchestration for background data processing.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logger = logging.getLogger(__name__)


class WorkerScheduler:
    """
    Background job scheduler for the Economic Dashboard.
    
    Manages all scheduled tasks:
    - Data refresh jobs (FRED, stock prices, options, SEC filings)
    - Feature computation jobs (technical indicators, ML features)
    - Maintenance jobs (cleanup, compaction, backups)
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,  # Combine missed runs
                'max_instances': 1,  # Prevent overlapping runs
                'misfire_grace_time': 300,  # 5 min grace period
            }
        )
        self._job_history: Dict[str, Dict[str, Any]] = {}
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up job execution event listeners."""
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )
    
    def _on_job_executed(self, event):
        """Log successful job execution."""
        job_id = event.job_id
        self._job_history[job_id] = {
            'status': 'success',
            'executed_at': datetime.utcnow().isoformat(),
            'runtime': event.retval if hasattr(event, 'retval') else None,
        }
        logger.info(f"Job {job_id} executed successfully")
    
    def _on_job_error(self, event):
        """Log job errors."""
        job_id = event.job_id
        self._job_history[job_id] = {
            'status': 'error',
            'executed_at': datetime.utcnow().isoformat(),
            'error': str(event.exception),
        }
        logger.error(f"Job {job_id} failed: {event.exception}")
    
    # =========================================================================
    # Data Refresh Jobs
    # =========================================================================
    
    def add_fred_refresh_job(self, hour: int = 8, minute: int = 0):
        """
        Schedule FRED data refresh.
        
        Runs daily at specified time (default 8:00 AM).
        FRED data typically updates at 8:30 AM ET.
        """
        self.scheduler.add_job(
            self._refresh_fred_data,
            CronTrigger(hour=hour, minute=minute),
            id='fred_refresh',
            name='FRED Data Refresh',
            replace_existing=True,
        )
        logger.info(f"Scheduled FRED refresh at {hour:02d}:{minute:02d}")
    
    def add_stock_refresh_job(self, interval_minutes: int = 5):
        """
        Schedule stock price refresh during market hours.
        
        Runs every N minutes during market hours (9:30 AM - 4:00 PM ET).
        """
        self.scheduler.add_job(
            self._refresh_stock_data,
            CronTrigger(
                day_of_week='mon-fri',
                hour='9-16',
                minute=f'*/{interval_minutes}'
            ),
            id='stock_refresh',
            name='Stock Price Refresh',
            replace_existing=True,
        )
        logger.info(f"Scheduled stock refresh every {interval_minutes} min")
    
    def add_options_refresh_job(self, interval_minutes: int = 15):
        """
        Schedule options data refresh during market hours.
        
        Runs every N minutes during market hours.
        """
        self.scheduler.add_job(
            self._refresh_options_data,
            CronTrigger(
                day_of_week='mon-fri',
                hour='9-16',
                minute=f'*/{interval_minutes}'
            ),
            id='options_refresh',
            name='Options Data Refresh',
            replace_existing=True,
        )
        logger.info(f"Scheduled options refresh every {interval_minutes} min")
    
    def add_sec_refresh_job(self, hour: int = 6, minute: int = 0):
        """
        Schedule SEC filings refresh.
        
        Runs daily before market open.
        """
        self.scheduler.add_job(
            self._refresh_sec_data,
            CronTrigger(hour=hour, minute=minute),
            id='sec_refresh',
            name='SEC Filings Refresh',
            replace_existing=True,
        )
        logger.info(f"Scheduled SEC refresh at {hour:02d}:{minute:02d}")
    
    # =========================================================================
    # Feature Computation Jobs
    # =========================================================================
    
    def add_feature_computation_job(self, interval_minutes: int = 30):
        """
        Schedule feature computation after data refresh.
        
        Computes:
        - Technical indicators
        - Volatility metrics
        - Options-derived features
        """
        self.scheduler.add_job(
            self._compute_features,
            IntervalTrigger(minutes=interval_minutes),
            id='feature_computation',
            name='Feature Computation',
            replace_existing=True,
        )
        logger.info(f"Scheduled feature computation every {interval_minutes} min")
    
    def add_prediction_job(self, hour: int = 9, minute: int = 25):
        """
        Schedule ML predictions before market open.
        
        Generates predictions for all monitored stocks.
        """
        self.scheduler.add_job(
            self._run_predictions,
            CronTrigger(
                day_of_week='mon-fri',
                hour=hour,
                minute=minute
            ),
            id='ml_predictions',
            name='ML Predictions',
            replace_existing=True,
        )
        logger.info(f"Scheduled predictions at {hour:02d}:{minute:02d}")
    
    # =========================================================================
    # Maintenance Jobs
    # =========================================================================
    
    def add_cleanup_job(self, hour: int = 2, minute: int = 0):
        """
        Schedule database cleanup.
        
        Removes expired data based on retention policies.
        """
        self.scheduler.add_job(
            self._run_cleanup,
            CronTrigger(hour=hour, minute=minute),
            id='db_cleanup',
            name='Database Cleanup',
            replace_existing=True,
        )
        logger.info(f"Scheduled cleanup at {hour:02d}:{minute:02d}")
    
    def add_backup_job(self, hour: int = 3, minute: int = 0):
        """
        Schedule database backup.
        
        Creates snapshot of DuckDB database.
        """
        self.scheduler.add_job(
            self._run_backup,
            CronTrigger(hour=hour, minute=minute),
            id='db_backup',
            name='Database Backup',
            replace_existing=True,
        )
        logger.info(f"Scheduled backup at {hour:02d}:{minute:02d}")
    
    def add_compaction_job(self, day_of_week: str = 'sun', hour: int = 4):
        """
        Schedule weekly database compaction.
        
        Optimizes storage and reclaims space.
        """
        self.scheduler.add_job(
            self._run_compaction,
            CronTrigger(day_of_week=day_of_week, hour=hour),
            id='db_compaction',
            name='Database Compaction',
            replace_existing=True,
        )
        logger.info(f"Scheduled compaction on {day_of_week} at {hour:02d}:00")
    
    # =========================================================================
    # Job Implementations
    # =========================================================================
    
    def _refresh_fred_data(self):
        """Refresh FRED economic indicators."""
        from modules.data_loader import FREDDataLoader
        
        start_time = datetime.utcnow()
        loader = FREDDataLoader()
        
        # Refresh all configured series
        series_list = [
            'GDP', 'GDPC1', 'UNRATE', 'CPIAUCSL', 'FEDFUNDS',
            'T10Y2Y', 'T10YIE', 'BAA10Y', 'VIXCLS', 'DGS10'
        ]
        
        for series_id in series_list:
            try:
                loader.fetch_series(series_id)
                logger.debug(f"Refreshed FRED series: {series_id}")
            except Exception as e:
                logger.error(f"Failed to refresh {series_id}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"FRED refresh completed in {duration:.2f}s")
        return duration
    
    def _refresh_stock_data(self):
        """Refresh stock price data."""
        from modules.data_loader import StockDataLoader
        from modules.database import get_monitored_tickers
        
        start_time = datetime.utcnow()
        loader = StockDataLoader()
        tickers = get_monitored_tickers()
        
        for ticker in tickers:
            try:
                loader.fetch_latest(ticker)
            except Exception as e:
                logger.error(f"Failed to refresh {ticker}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Stock refresh completed in {duration:.2f}s")
        return duration
    
    def _refresh_options_data(self):
        """Refresh options chain data."""
        from modules.data_loader import OptionsDataLoader
        from modules.database import get_monitored_tickers
        
        start_time = datetime.utcnow()
        loader = OptionsDataLoader()
        tickers = get_monitored_tickers()
        
        for ticker in tickers:
            try:
                loader.fetch_chain(ticker)
            except Exception as e:
                logger.error(f"Failed to refresh options for {ticker}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Options refresh completed in {duration:.2f}s")
        return duration
    
    def _refresh_sec_data(self):
        """Refresh SEC filings data."""
        from modules.features.insider_trading_tracker import InsiderTradingTracker
        
        start_time = datetime.utcnow()
        tracker = InsiderTradingTracker()
        tracker.refresh_all_filings()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"SEC refresh completed in {duration:.2f}s")
        return duration
    
    def _compute_features(self):
        """Compute all features for monitored tickers."""
        from modules.database import get_monitored_tickers
        from modules.features.feature_store import FeatureStore
        
        start_time = datetime.utcnow()
        store = FeatureStore()
        tickers = get_monitored_tickers()
        
        for ticker in tickers:
            try:
                store.compute_and_store(ticker)
            except Exception as e:
                logger.error(f"Failed to compute features for {ticker}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Feature computation completed in {duration:.2f}s")
        return duration
    
    def _run_predictions(self):
        """Run ML predictions for all tickers."""
        from modules.database import get_monitored_tickers
        from modules.ml.prediction import PredictionEngine
        
        start_time = datetime.utcnow()
        engine = PredictionEngine()
        tickers = get_monitored_tickers()
        
        for ticker in tickers:
            try:
                engine.predict(ticker=ticker, store_result=True)
            except Exception as e:
                logger.error(f"Failed prediction for {ticker}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Predictions completed in {duration:.2f}s")
        return duration
    
    def _run_cleanup(self):
        """Run database cleanup based on retention policies."""
        from modules.database.maintenance import run_cleanup
        
        start_time = datetime.utcnow()
        run_cleanup()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Cleanup completed in {duration:.2f}s")
        return duration
    
    def _run_backup(self):
        """Create database backup."""
        from modules.database.maintenance import create_backup
        
        start_time = datetime.utcnow()
        create_backup()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Backup completed in {duration:.2f}s")
        return duration
    
    def _run_compaction(self):
        """Run database compaction."""
        from modules.database.maintenance import run_compaction
        
        start_time = datetime.utcnow()
        run_compaction()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Compaction completed in {duration:.2f}s")
        return duration
    
    # =========================================================================
    # Scheduler Control
    # =========================================================================
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")
    
    def get_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
            }
            for job in self.scheduler.get_jobs()
        ]
    
    def get_job_history(self, job_id: Optional[str] = None):
        """Get job execution history."""
        if job_id:
            return self._job_history.get(job_id)
        return self._job_history
    
    def run_job_now(self, job_id: str):
        """Trigger immediate execution of a job."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.utcnow())
            logger.info(f"Triggered immediate run of job: {job_id}")
            return True
        return False


# Singleton instance
_scheduler: Optional[WorkerScheduler] = None


def get_scheduler() -> WorkerScheduler:
    """Get the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = WorkerScheduler()
    return _scheduler


def setup_all_jobs(scheduler: Optional[WorkerScheduler] = None):
    """Configure all default jobs."""
    if scheduler is None:
        scheduler = get_scheduler()
    
    # Data refresh jobs
    scheduler.add_fred_refresh_job(hour=8, minute=0)
    scheduler.add_stock_refresh_job(interval_minutes=5)
    scheduler.add_options_refresh_job(interval_minutes=15)
    scheduler.add_sec_refresh_job(hour=6, minute=0)
    
    # Feature computation
    scheduler.add_feature_computation_job(interval_minutes=30)
    scheduler.add_prediction_job(hour=9, minute=25)
    
    # Maintenance jobs
    scheduler.add_cleanup_job(hour=2, minute=0)
    scheduler.add_backup_job(hour=3, minute=0)
    scheduler.add_compaction_job(day_of_week='sun', hour=4)
    
    logger.info("All default jobs configured")
    return scheduler
