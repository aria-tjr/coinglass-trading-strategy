"""
Scheduler for periodic tasks using APScheduler.

Manages automated tasks like data fetching, strategy evaluation,
and position management on configurable intervals.
"""

import asyncio
from typing import Callable, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore

from .config import settings
from .logger import get_logger

logger = get_logger("scheduler")


class TradingScheduler:
    """
    Manages periodic tasks for the trading bot.
    
    Handles scheduling of data updates, strategy evaluation,
    and position management tasks.
    """
    
    def __init__(self):
        """Initialize the scheduler with async executor."""
        # Configure job stores and executors
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': True,  # Coalesce missed jobs
            'max_instances': 1,  # One instance of each job at a time
            'misfire_grace_time': 30  # Grace period for misfired jobs
        }
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Track registered jobs
        self._jobs = {}
        self._running = False
        
        logger.info("Scheduler initialized")
    
    async def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler already running")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")
    
    def add_interval_job(
        self,
        func: Callable,
        seconds: int,
        job_id: str,
        args: tuple = None,
        kwargs: dict = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None
    ) -> None:
        """
        Add a job that runs at regular intervals.
        
        Args:
            func: The function to execute
            seconds: Interval in seconds
            job_id: Unique identifier for the job
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            start_date: When to start running the job
            end_date: When to stop running the job
        """
        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(seconds=seconds),
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                start_date=start_date,
                end_date=end_date,
                replace_existing=True
            )
            
            self._jobs[job_id] = job
            logger.info(f"Added interval job '{job_id}' with {seconds}s interval")
            
        except Exception as e:
            logger.error(f"Failed to add interval job '{job_id}': {e}")
            raise
    
    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        cron_expression: str = None,
        args: tuple = None,
        kwargs: dict = None,
        **cron_kwargs
    ) -> None:
        """
        Add a job that runs on a cron schedule.
        
        Args:
            func: The function to execute
            job_id: Unique identifier for the job
            cron_expression: Cron expression string
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            **cron_kwargs: Cron parameters (hour, minute, etc.)
        """
        try:
            if cron_expression:
                # Parse cron expression
                parts = cron_expression.split()
                if len(parts) == 5:
                    minute, hour, day, month, day_of_week = parts
                    cron_kwargs.update({
                        'minute': minute,
                        'hour': hour,
                        'day': day,
                        'month': month,
                        'day_of_week': day_of_week
                    })
            
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger(**cron_kwargs),
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True
            )
            
            self._jobs[job_id] = job
            logger.info(f"Added cron job '{job_id}' with schedule: {cron_kwargs}")
            
        except Exception as e:
            logger.error(f"Failed to add cron job '{job_id}': {e}")
            raise
    
    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self._jobs:
                del self._jobs[job_id]
            logger.info(f"Removed job '{job_id}'")
        except Exception as e:
            logger.error(f"Failed to remove job '{job_id}': {e}")
    
    def pause_job(self, job_id: str) -> None:
        """Pause a scheduled job."""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job '{job_id}'")
        except Exception as e:
            logger.error(f"Failed to pause job '{job_id}': {e}")
    
    def resume_job(self, job_id: str) -> None:
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job '{job_id}'")
        except Exception as e:
            logger.error(f"Failed to resume job '{job_id}': {e}")
    
    def get_job_info(self, job_id: str) -> dict:
        """Get information about a specific job."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    'id': job.id,
                    'name': job.name,
                    'func': job.func.__name__,
                    'trigger': str(job.trigger),
                    'next_run': job.next_run_time,
                    'coalesce': job.coalesce,
                    'max_instances': job.max_instances
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get job info for '{job_id}': {e}")
            return {}
    
    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(self.get_job_info(job.id))
        return jobs
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


class TradingJobManager:
    """
    High-level manager for trading-specific scheduled jobs.
    
    Provides convenient methods to set up the standard trading bot jobs.
    """
    
    def __init__(self, scheduler: TradingScheduler):
        """Initialize with a scheduler instance."""
        self.scheduler = scheduler
        self.logger = get_logger("job_manager")
    
    def setup_trading_jobs(
        self,
        update_data_func: Callable,
        evaluate_strategy_func: Callable,
        manage_positions_func: Callable
    ) -> None:
        """
        Set up the standard trading bot jobs.
        
        Args:
            update_data_func: Function to update market data
            evaluate_strategy_func: Function to evaluate trading strategy
            manage_positions_func: Function to manage open positions
        """
        # Data update job - runs every 30 seconds by default
        self.scheduler.add_interval_job(
            func=update_data_func,
            seconds=settings.data_update_interval,
            job_id="update_data",
        )
        
        # Strategy evaluation job - runs every 60 seconds by default
        self.scheduler.add_interval_job(
            func=evaluate_strategy_func,
            seconds=settings.strategy_eval_interval,
            job_id="evaluate_strategy",
        )
        
        # Position management job - runs every 5 minutes by default
        self.scheduler.add_interval_job(
            func=manage_positions_func,
            seconds=settings.position_management_interval,
            job_id="manage_positions",
        )
        
        self.logger.info("Trading jobs configured")
    
    def setup_maintenance_jobs(self, cleanup_func: Callable = None) -> None:
        """
        Set up maintenance jobs like daily cleanup.
        
        Args:
            cleanup_func: Optional cleanup function to run daily
        """
        if cleanup_func:
            # Daily cleanup at 2 AM UTC
            self.scheduler.add_cron_job(
                func=cleanup_func,
                job_id="daily_cleanup",
                hour=2,
                minute=0
            )
            
            self.logger.info("Maintenance jobs configured")
    
    def enable_strategy(self) -> None:
        """Enable strategy evaluation job."""
        self.scheduler.resume_job("evaluate_strategy")
        self.logger.info("Strategy evaluation enabled")
    
    def disable_strategy(self) -> None:
        """Disable strategy evaluation job."""
        self.scheduler.pause_job("evaluate_strategy")
        self.logger.info("Strategy evaluation disabled")
    
    def get_status(self) -> dict:
        """Get status of all trading jobs."""
        return {
            "scheduler_running": self.scheduler.is_running,
            "jobs": self.scheduler.list_jobs()
        }


# Global scheduler instance
scheduler = TradingScheduler()
job_manager = TradingJobManager(scheduler) 