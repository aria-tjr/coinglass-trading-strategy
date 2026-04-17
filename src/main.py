"""
Main application entry point for telegram_coinglass_trader.

Initializes all components and starts the trading bot with proper
async handling, error management, and graceful shutdown.
"""

import asyncio
import signal
import sys
from typing import Dict, Any
import uvloop

from core.config import settings
from core.logger import get_logger, trading_logger
from core.scheduler import scheduler as trading_scheduler
from infra.coinglass_client import coinglass_client
from infra.exchange_gateway import bybit_gateway
from infra.telegram_bot import telegram_bot
from strategy.engine import trading_strategy
from strategy.indicators import technical_indicators
from strategy.risk_manager import risk_manager
from strategy.portfolio_manager import portfolio_manager
from strategy.performance_optimizer import performance_optimizer

logger = get_logger("main")


class TradingApplication:
    """Main trading application orchestrator."""
    
    def __init__(self):
        """Initialize the trading application."""
        self.running = False
        self.components_started = False
        logger.info("Trading application initialized")
    
    async def initialize_components(self) -> bool:
        """
        Initialize all trading components.
        
        Returns:
            True if all components initialized successfully
        """
        try:
            logger.info("Initializing trading components...")
            
            # Initialize core components
            logger.info("Setting up logging system...")
            trading_logger.info("Trading system startup initiated", extra={
                "symbol": settings.default_symbol,
                "strategy_enabled": settings.strategy_enabled,
                "max_risk": settings.max_risk_percent
            })
            
            # Initialize CoinGlass client
            logger.info("Initializing CoinGlass client...")
            if not await coinglass_client.health_check():
                logger.error("CoinGlass client health check failed")
                return False
            
            # Initialize exchange gateway
            logger.info("Initializing Bybit exchange gateway...")
            if not await bybit_gateway.health_check():
                logger.error("Bybit exchange health check failed")
                return False
            
            # Set trading leverage
            await bybit_gateway.set_leverage(settings.default_symbol, settings.leverage)
            
            # Initialize risk manager with current account balance
            balance = await bybit_gateway.get_balance()
            account_balance = balance.get('free', 0)
            if account_balance <= 0:
                logger.error("Invalid account balance")
                return False
            
            risk_manager.set_account_balance(account_balance)
            logger.info(f"Risk manager initialized with balance: ${account_balance:.2f}")
            
            # Initialize Telegram bot
            logger.info("Initializing Telegram bot...")
            await telegram_bot.initialize()
            
            logger.info("All components initialized successfully")
            self.components_started = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    async def setup_scheduled_tasks(self) -> None:
        """Set up all scheduled trading tasks."""
        try:
            logger.info("Setting up scheduled tasks...")
            
            # Data update task (every 30 seconds)
            trading_scheduler.add_interval_job(
                func=trading_strategy.update_market_data,
                seconds=settings.data_update_interval,
                job_id='market_data_update'
            )
            
            # Strategy evaluation task (every 60 seconds)
            trading_scheduler.add_interval_job(
                func=trading_strategy.evaluate_strategy,
                seconds=settings.strategy_eval_interval,
                job_id='strategy_evaluation'
            )
            
            # Position management task (every 5 minutes)
            async def manage_positions():
                """Periodic position management."""
                try:
                    positions = await bybit_gateway.get_positions(settings.default_symbol)
                    if positions:
                        await trading_strategy._manage_existing_positions(positions)
                        
                        # Update trailing stops
                        for position in positions:
                            current_price = position.mark_price
                            risk_manager.update_trailing_stop(position.symbol, current_price)
                            
                except Exception as e:
                    logger.error(f"Position management error: {e}")
            
            trading_scheduler.add_interval_job(
                func=manage_positions,
                seconds=settings.position_management_interval,
                job_id='position_management'
            )
            
            # Balance update task (every 10 minutes)
            async def update_balance():
                """Update account balance for risk management."""
                try:
                    balance = await bybit_gateway.get_balance()
                    account_balance = balance.get('free', 0)
                    risk_manager.set_account_balance(account_balance)
                    
                    # Send daily summary if needed
                    from datetime import datetime
                    if datetime.now().hour == 0 and datetime.now().minute < 10:
                        await telegram_bot.send_daily_summary(
                            balance=account_balance,
                            positions=await bybit_gateway.get_positions(),
                            strategy_stats=trading_strategy.get_status()
                        )
                        
                except Exception as e:
                    logger.error(f"Balance update error: {e}")
            
            trading_scheduler.add_interval_job(
                func=update_balance,
                seconds=600,  # 10 minutes
                job_id='balance_update'
            )
            
            # Performance tracking task (every hour)
            async def track_performance():
                """Track and optimize performance for 20%+ returns."""
                try:
                    # Track current performance
                    metrics = await performance_optimizer.track_performance()
                    
                    # Log progress towards targets
                    targets = performance_optimizer.get_performance_targets()
                    logger.info(f"Target Progress: {targets['progress_to_target']:.1f}%")
                    
                    # Send performance update via Telegram (daily)
                    if datetime.now().hour == 12 and datetime.now().minute < 10:  # Noon
                        performance_text = f"""📊 *Performance Update*

Annual Return: {metrics.annual_return:.1f}% (Target: 20%+)
Monthly Return: {metrics.monthly_return:.1f}%
Win Rate: {metrics.win_rate:.1f}%
Profit Factor: {metrics.profit_factor:.2f}
Max Drawdown: {metrics.max_drawdown:.1f}%
Total Trades: {metrics.total_trades}

Progress to Target: {targets['progress_to_target']:.1f}%"""
                        
                        await telegram_bot.send_alert(performance_text)
                    
                except Exception as e:
                    logger.error(f"Performance tracking error: {e}")
            
            trading_scheduler.add_interval_job(
                func=track_performance,
                seconds=3600,  # 1 hour
                job_id='performance_tracking'
            )
            
            # Parameter optimization task (weekly)
            async def optimize_parameters():
                """Weekly parameter optimization for enhanced returns."""
                try:
                    optimizations = await performance_optimizer.optimize_parameters()
                    
                    if optimizations:
                        opt_text = "🔧 *Parameter Optimizations Applied*\n\n"
                        for opt in optimizations:
                            opt_text += f"• {opt.parameter}: {opt.original_value} → {opt.optimized_value} (+{opt.performance_improvement:.1f}%)\n"
                        
                        await telegram_bot.send_alert(opt_text)
                        
                except Exception as e:
                    logger.error(f"Parameter optimization error: {e}")
            
            trading_scheduler.add_interval_job(
                func=optimize_parameters,
                seconds=604800,  # 1 week
                job_id='parameter_optimization'
            )
            
            # Market regime detection task (every 4 hours)
            async def detect_market_regime():
                """Detect market regime for adaptive strategies."""
                try:
                    regime = await performance_optimizer.detect_market_regime()
                    logger.debug(f"Current market regime: {regime}")
                    
                except Exception as e:
                    logger.error(f"Market regime detection error: {e}")
            
            trading_scheduler.add_interval_job(
                func=detect_market_regime,
                seconds=14400,  # 4 hours
                job_id='regime_detection'
            )
            
            # Start the scheduler
            await trading_scheduler.start()
            logger.info("Scheduled tasks configured and started")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduled tasks: {e}")
            raise
    
    async def start(self) -> None:
        """Start the trading application."""
        try:
            logger.info("Starting telegram_coinglass_trader...")
            
            # Initialize components
            if not await self.initialize_components():
                logger.error("Component initialization failed")
                sys.exit(1)
            
            # Setup scheduled tasks
            await self.setup_scheduled_tasks()
            
            # Start Telegram bot polling
            logger.info("Starting Telegram bot...")
            await telegram_bot.start_polling()
            
            self.running = True
            logger.info("🚀 Trading application started successfully!")
            
            # Send startup notification
            await telegram_bot.send_startup_notification(
                version="0.1.0",
                symbol=settings.default_symbol,
                strategy_enabled=settings.strategy_enabled,
                balance=await bybit_gateway.get_balance()
            )
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            sys.exit(1)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the trading application."""
        try:
            logger.info("Shutting down trading application...")
            self.running = False
            
            # Stop scheduler
            if trading_scheduler.running:
                trading_scheduler.shutdown(wait=True)
                logger.info("Scheduler stopped")
            
            # Close connections
            if self.components_started:
                await coinglass_client.close()
                await bybit_gateway.close()
                await telegram_bot.stop()
                logger.info("All connections closed")
            
            # Final log
            trading_logger.info("Trading system shutdown completed")
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global application instance
app = TradingApplication()


def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(app.shutdown())


async def main():
    """Main application entry point."""
    try:
        # Install uvloop for better performance
        if hasattr(uvloop, 'install'):
            uvloop.install()
            logger.info("uvloop installed for enhanced async performance")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the application
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await app.shutdown()
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        await app.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 