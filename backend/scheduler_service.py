import asyncio
import logging
import random
from datetime import datetime, timedelta
import pytz
from typing import List
import database
import research
import research_pipeline
import email_service
import utils

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')

class ScheduledResearchExecutor:
    def __init__(self):
        self.is_running = False
        
    async def calculate_next_run_time(self, research_config: dict) -> datetime:
        """
        Calculate the next run time for a scheduled research based on its configuration.
        
        Args:
            research_config: The scheduled research configuration
            
        Returns:
            datetime: The next scheduled run time
        """
        now = datetime.now(ADELAIDE_TZ)
        hour = research_config['hour']
        minute = research_config['minute']
        
        if research_config['frequency'] == 'daily':
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif research_config['frequency'] == 'weekly':
            day_of_week = research_config['day_of_week']  # 0=Monday, 6=Sunday
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = day_of_week - next_run.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run += timedelta(days_ahead)
            
        elif research_config['frequency'] == 'monthly':
            day_of_month = research_config['day_of_month']
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run.day >= day_of_month:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)
            # Set the day
            next_run = next_run.replace(day=min(day_of_month, self._days_in_month(next_run)))
            
        else:
            # Default to daily if frequency is not recognized
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        return next_run
    
    def _days_in_month(self, dt: datetime) -> int:
        """Get the number of days in the month of the given datetime."""
        if dt.month == 12:
            return 31
        next_month = dt.replace(month=dt.month + 1, day=1)
        return (next_month - timedelta(days=1)).day
    
    async def should_run_now(self, research_config: dict) -> bool:
        """
        Check if a scheduled research should run now.
        
        Args:
            research_config: The scheduled research configuration
            
        Returns:
            bool: True if the research should run now, False otherwise
        """
        # Check if it's active
        if not research_config.get('is_active', True):
            return False
            
        # Check if it's the right time of day
        now = datetime.now(ADELAIDE_TZ)
        if now.hour != research_config['hour'] or now.minute != research_config['minute']:
            return False
            
        # For weekly, check if it's the right day of week
        if research_config['frequency'] == 'weekly':
            if now.weekday() != research_config['day_of_week']:
                return False
                
        # For monthly, check if it's the right day of month
        if research_config['frequency'] == 'monthly':
            if now.day != research_config['day_of_month']:
                return False
                
        # Check if we have a last run time
        last_run = research_config.get('last_run')
        if last_run:
            # Parse the last run time
            if isinstance(last_run, str):
                last_run = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
            
            # Check if it's the same day as last run
            if last_run.date() == now.date():
                # If it's the same day, check if the task was updated after the last run
                # This allows updated tasks to run again on the same day
                updated_at = research_config.get('updated_at')
                if updated_at:
                    # Parse the updated time
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    
                    # If the task was updated after it last ran, allow it to run again today
                    if updated_at > last_run:
                        return True
                    else:
                        # Already ran today and wasn't updated after last run
                        return False
                else:
                    # No updated_at field, so don't run again today
                    return False
            
            # For different days, check frequency-based thresholds
            if research_config['frequency'] == 'daily':
                # Daily tasks can run once per day
                if (now - last_run).total_seconds() < 23 * 3600:
                    return False
            elif research_config['frequency'] == 'weekly':
                # Weekly tasks can run once per week
                if (now - last_run).total_seconds() < 6 * 24 * 3600:
                    return False
            elif research_config['frequency'] == 'monthly':
                # Monthly tasks can run once per month
                if (now - last_run).total_seconds() < 27 * 24 * 3600:
                    return False
        
        return True
    
    async def execute_scheduled_research(self, research_config: dict):
        """
        Execute a scheduled research task.
        
        Args:
            research_config: The scheduled research configuration
        """
        try:
            logger.info(f"Executing scheduled research: {research_config['name']}")
            
            # Calculate date range for research
            date_range_days = research_config.get('date_range_days', 7)
            end_date = datetime.now(ADELAIDE_TZ)
            start_date = end_date - timedelta(days=date_range_days)
            
            # Format dates for query
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Create query
            query = f"cybersecurity incidents in Australia from {start_date_str} to {end_date_str}"
            
            # Get server configuration
            server_name = research_config.get('server_name')
            server_type = research_config.get('server_type', 'ollama')
            model_name = research_config.get('model_name', 'granite3.3')
            
            # If no server specified, get the first available server
            if not server_name:
                if server_type == 'ollama':
                    servers = await database.get_ollama_servers()
                    if servers:
                        server_name = servers[0]['name']
                elif server_type == 'gemini':
                    servers = await database.get_external_ai_servers()
                    if servers:
                        server_name = servers[0]['name']
            
            # Run improved research pipeline job and wait for completion
            try:
                target_count = int(utils.config.get('research_pipeline', {}).get('scheduled_target_count', 10))
            except Exception:
                target_count = 10
            # Force API-free discovery focusing on RSS only for scheduled email reports
            try:
                sources_cfg = utils.config.get('sources', {}) if hasattr(utils, 'config') else {}
            except Exception:
                sources_cfg = {}
            job_config = {
                "discovery": {
                    "mode": "api_free",
                    "recency_days": int(date_range_days)
                },
                "sources": {
                    "rss_urls": sources_cfg.get("rss_urls", []),
                    "sitemap_domains": []
                },
                # Provide empty include list to discourage domain crawling; pipeline will prefer defaults if set
                "domains": {
                    "include": []
                },
                # Explicitly disable API search providers
                "search": {
                    "use_serpapi": False,
                    "use_tavily": False
                },
                # Soft hint: keep domain crawling impact minimal
                "discovery_hints": {
                    "max_pages_per_domain": 0
                }
            }
            job_id = await database.add_research_job(query, server_name, model_name, server_type, target_count, config=job_config)
            await research_pipeline.run_research_job(job_id, seed_urls=None, focus_on_seed=True)
            job = await database.get_research_job(job_id)
            result_text = None
            if job and job.get('status') == 'finalized' and job.get('research_id'):
                r = await database.get_research_by_id(int(job['research_id']))
                if r and r.get('result'):
                    result_text = r['result']

            if result_text:
                # Send email with results and email_config_id if provided
                email_config_id = research_config.get('email_config_id')
                success = await email_service.send_scheduled_research_email(
                    research_config,
                    result_text,
                    None,
                    email_config_id,
                    date_range_start=start_date_str,
                    date_range_end=end_date_str
                )
                if success:
                    logger.info(f"Successfully sent research report for: {research_config['name']}")
                else:
                    logger.error(f"Failed to send research report for: {research_config['name']}")
            else:
                logger.warning(f"No results found for scheduled research: {research_config['name']}")
                
        except Exception as e:
            logger.error(f"Error executing scheduled research {research_config['name']}: {str(e)}")
    
    async def run_scheduler(self):
        """
        Main scheduler loop that checks for and executes scheduled research tasks.
        """
        self.is_running = True
        logger.info("Scheduled research executor started")
        
        while self.is_running:
            try:
                # Get all scheduled research configurations
                research_list = await database.get_scheduled_research_list()
                
                # Check each scheduled research
                for research_config in research_list:
                    if await self.should_run_now(research_config):
                        logger.info(f"Scheduled research '{research_config['name']}' should run now")
                        # Optional jitter to avoid same-minute pileups
                        try:
                            jitter_max = utils.config.get('scheduler', {}).get('jitter_seconds_max', 0)
                            if jitter_max and jitter_max > 0:
                                delay = random.uniform(0, float(jitter_max))
                                logger.info(f"Applying jitter of {delay:.1f}s before executing '{research_config['name']}'")
                                await asyncio.sleep(delay)
                        except Exception:
                            pass
                        # Execute the research
                        await self.execute_scheduled_research(research_config)
                        
                        # Update last run time
                        await database.update_scheduled_research_run_times(
                            research_config['id'],
                            last_run=datetime.now(ADELAIDE_TZ)
                        )
                
                # Sleep for a minute before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                # Sleep for a minute even if there's an error
                await asyncio.sleep(60)
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        self.is_running = False
        logger.info("Scheduled research executor stopped")

# Global instance
scheduler_executor = ScheduledResearchExecutor()
