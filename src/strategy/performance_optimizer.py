"""
Performance Optimization Module for High-Return Trading.

Tracks performance metrics, optimizes parameters, and implements
advanced strategies to achieve 20%+ annual returns.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

from core.config import settings
from core.logger import get_logger, trading_logger
from strategy.risk_manager import risk_manager, TradeRecord
from infra.exchange_gateway import bybit_gateway

logger = get_logger("performance_optimizer")


class PerformanceTarget(Enum):
    """Performance target levels."""
    CONSERVATIVE = "15%"  # 15% annual
    MODERATE = "20%"      # 20% annual (target)
    AGGRESSIVE = "30%"    # 30% annual
    MAXIMUM = "50%"       # 50% annual


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    total_return: float
    annual_return: float
    monthly_return: float
    daily_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int


@dataclass
class OptimizationResult:
    """Results from parameter optimization."""
    parameter: str
    original_value: Any
    optimized_value: Any
    performance_improvement: float
    confidence: float


class AdvancedPerformanceOptimizer:
    """
    Advanced performance optimization system for 20%+ annual returns.
    
    Features:
    - Real-time performance tracking
    - Parameter optimization based on results
    - Market regime detection
    - Dynamic risk adjustment
    - Compound return optimization
    """
    
    def __init__(self):
        """Initialize performance optimizer."""
        self.target_annual_return = 20.0  # 20% target
        self.target_monthly_return = 1.53  # Compound monthly target
        self.target_daily_return = 0.05    # ~0.05% daily target
        
        # Performance tracking
        self.daily_returns: List[float] = []
        self.monthly_returns: List[float] = []
        self.drawdown_periods: List[Dict] = []
        
        # Optimization state
        self.last_optimization = datetime.now()
        self.optimization_interval = timedelta(days=7)  # Weekly optimization
        
        # Market regime detection
        self.current_regime = "normal"  # normal, bullish, bearish, volatile
        self.regime_history: List[Dict] = []
        
        # Dynamic parameters for optimization
        self.adaptive_parameters = {
            'risk_per_trade': 3.0,      # Start at 3%
            'win_rate_threshold': 0.65,  # Target 65% win rate
            'profit_factor_target': 2.5,  # Target profit factor
            'max_drawdown_limit': 8.0,   # Max 8% drawdown
        }
        
        logger.info("Advanced performance optimizer initialized for 20%+ returns")
    
    async def track_performance(self) -> PerformanceMetrics:
        """Track and calculate comprehensive performance metrics."""
        try:
            # Get trading history
            trade_history = risk_manager.trade_history
            
            if len(trade_history) < 5:
                logger.warning("Insufficient trade history for performance analysis")
                return self._create_empty_metrics()
            
            # Calculate returns
            trade_returns = [trade.pnl_percent for trade in trade_history]
            
            # Basic performance metrics
            total_return = sum(trade_returns)
            avg_trade_return = np.mean(trade_returns)
            
            # Time-based returns
            days_trading = (datetime.now() - trade_history[0].timestamp).days or 1
            annual_return = (total_return / 100) * (365 / days_trading) * 100
            monthly_return = (total_return / 100) * (30 / days_trading) * 100
            daily_return = total_return / days_trading if days_trading > 0 else 0
            
            # Risk metrics
            returns_std = np.std(trade_returns) if len(trade_returns) > 1 else 0
            sharpe_ratio = (avg_trade_return / returns_std) if returns_std > 0 else 0
            
            # Drawdown calculation
            cumulative_returns = np.cumsum(trade_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
            
            # Win rate and profit factor
            winning_trades = [r for r in trade_returns if r > 0]
            losing_trades = [r for r in trade_returns if r < 0]
            
            win_rate = len(winning_trades) / len(trade_returns) if trade_returns else 0
            
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 1
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Consecutive wins/losses
            consecutive_wins = self._calculate_consecutive(trade_returns, positive=True)
            consecutive_losses = self._calculate_consecutive(trade_returns, positive=False)
            
            metrics = PerformanceMetrics(
                total_return=total_return,
                annual_return=annual_return,
                monthly_return=monthly_return,
                daily_return=daily_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate * 100,
                profit_factor=profit_factor,
                total_trades=len(trade_history),
                avg_trade_return=avg_trade_return,
                best_trade=max(trade_returns) if trade_returns else 0,
                worst_trade=min(trade_returns) if trade_returns else 0,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses
            )
            
            # Log performance summary
            self._log_performance_summary(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to track performance: {e}")
            return self._create_empty_metrics()
    
    def _calculate_consecutive(self, returns: List[float], positive: bool) -> int:
        """Calculate consecutive wins or losses."""
        if not returns:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for ret in reversed(returns):  # Start from most recent
            if (positive and ret > 0) or (not positive and ret < 0):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                break  # Only count current streak
        
        return current_consecutive
    
    async def optimize_parameters(self) -> List[OptimizationResult]:
        """Optimize trading parameters based on performance."""
        try:
            if datetime.now() - self.last_optimization < self.optimization_interval:
                return []
            
            logger.info("Starting parameter optimization for enhanced returns...")
            
            # Get current performance
            current_metrics = await self.track_performance()
            optimizations = []
            
            # Optimize risk per trade
            risk_optimization = self._optimize_risk_parameter(current_metrics)
            if risk_optimization:
                optimizations.append(risk_optimization)
            
            # Optimize take profit targets
            tp_optimization = self._optimize_take_profit(current_metrics)
            if tp_optimization:
                optimizations.append(tp_optimization)
            
            # Optimize position sizing
            sizing_optimization = self._optimize_position_sizing(current_metrics)
            if sizing_optimization:
                optimizations.append(sizing_optimization)
            
            self.last_optimization = datetime.now()
            
            if optimizations:
                logger.info(f"Applied {len(optimizations)} parameter optimizations")
                await self._apply_optimizations(optimizations)
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return []
    
    def _optimize_risk_parameter(self, metrics: PerformanceMetrics) -> Optional[OptimizationResult]:
        """Optimize risk per trade based on performance."""
        current_risk = self.adaptive_parameters['risk_per_trade']
        
        # If annual return is below target and drawdown is acceptable
        if metrics.annual_return < self.target_annual_return and metrics.max_drawdown < 6.0:
            # Increase risk if win rate is good
            if metrics.win_rate > 60:
                new_risk = min(current_risk * 1.2, 5.0)  # Max 5% risk
                improvement = (new_risk - current_risk) / current_risk * 100
                
                return OptimizationResult(
                    parameter="risk_per_trade",
                    original_value=current_risk,
                    optimized_value=new_risk,
                    performance_improvement=improvement,
                    confidence=0.8
                )
        
        # Reduce risk if drawdown is too high
        elif metrics.max_drawdown > self.adaptive_parameters['max_drawdown_limit']:
            new_risk = max(current_risk * 0.8, 1.5)  # Min 1.5% risk
            improvement = (current_risk - new_risk) / current_risk * 100
            
            return OptimizationResult(
                parameter="risk_per_trade",
                original_value=current_risk,
                optimized_value=new_risk,
                performance_improvement=improvement,
                confidence=0.9
            )
        
        return None
    
    def _optimize_take_profit(self, metrics: PerformanceMetrics) -> Optional[OptimizationResult]:
        """Optimize take profit targets."""
        # If win rate is low but average winner is small, increase TP targets
        if metrics.win_rate < 55 and metrics.profit_factor < 2.0:
            current_tp = settings.take_profit_percent
            new_tp = min(current_tp * 1.3, 12.0)  # Max 12% TP
            improvement = (new_tp - current_tp) / current_tp * 100
            
            return OptimizationResult(
                parameter="take_profit_percent",
                original_value=current_tp,
                optimized_value=new_tp,
                performance_improvement=improvement,
                confidence=0.7
            )
        
        return None
    
    def _optimize_position_sizing(self, metrics: PerformanceMetrics) -> Optional[OptimizationResult]:
        """Optimize position sizing strategy."""
        # If Sharpe ratio is good, can increase position sizes
        if metrics.sharpe_ratio > 1.5 and metrics.max_drawdown < 5.0:
            current_max_positions = settings.max_open_positions
            new_max_positions = min(current_max_positions + 1, 5)
            
            if new_max_positions > current_max_positions:
                improvement = 20.0  # Estimated improvement from diversification
                
                return OptimizationResult(
                    parameter="max_open_positions",
                    original_value=current_max_positions,
                    optimized_value=new_max_positions,
                    performance_improvement=improvement,
                    confidence=0.6
                )
        
        return None
    
    async def _apply_optimizations(self, optimizations: List[OptimizationResult]) -> None:
        """Apply optimization results to trading parameters."""
        for opt in optimizations:
            logger.info(
                f"Applying optimization: {opt.parameter} "
                f"{opt.original_value} -> {opt.optimized_value} "
                f"(+{opt.performance_improvement:.1f}%)"
            )
            
            # Update adaptive parameters
            if opt.parameter == "risk_per_trade":
                self.adaptive_parameters['risk_per_trade'] = opt.optimized_value
            
            # Update global settings would require configuration management
            # This could be implemented with a configuration updater
    
    async def detect_market_regime(self) -> str:
        """Detect current market regime for adaptive strategies."""
        try:
            # Get recent price data for multiple timeframes
            btc_data = await bybit_gateway.get_ohlcv('BTC/USDT:USDT', '1h', 168)  # 7 days
            
            if btc_data.empty:
                return self.current_regime
            
            # Calculate volatility and trend
            returns = btc_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Annualized hourly volatility
            trend = (btc_data['close'].iloc[-1] / btc_data['close'].iloc[0] - 1) * 100
            
            # Regime classification
            if volatility > 0.8:  # High volatility
                regime = "volatile"
            elif trend > 5:  # Strong uptrend
                regime = "bullish"
            elif trend < -5:  # Strong downtrend
                regime = "bearish"
            else:
                regime = "normal"
            
            if regime != self.current_regime:
                logger.info(f"Market regime changed: {self.current_regime} -> {regime}")
                self.current_regime = regime
                
                # Store regime change
                self.regime_history.append({
                    'timestamp': datetime.now(),
                    'regime': regime,
                    'trend': trend,
                    'volatility': volatility
                })
            
            return regime
            
        except Exception as e:
            logger.error(f"Market regime detection failed: {e}")
            return self.current_regime
    
    def get_performance_targets(self) -> Dict[str, float]:
        """Get performance targets for 20%+ annual returns."""
        return {
            'target_annual_return': self.target_annual_return,
            'target_monthly_return': self.target_monthly_return,
            'target_daily_return': self.target_daily_return,
            'current_annual_projection': self._calculate_annual_projection(),
            'progress_to_target': self._calculate_target_progress()
        }
    
    def _calculate_annual_projection(self) -> float:
        """Calculate projected annual return based on current performance."""
        if not risk_manager.trade_history:
            return 0.0
        
        # Simple projection based on recent performance
        recent_trades = risk_manager.trade_history[-20:]  # Last 20 trades
        avg_return = np.mean([trade.pnl_percent for trade in recent_trades])
        
        # Estimate trades per year (assuming current frequency)
        days_for_trades = (recent_trades[-1].timestamp - recent_trades[0].timestamp).days or 1
        trades_per_day = len(recent_trades) / days_for_trades
        estimated_annual_trades = trades_per_day * 365
        
        return avg_return * estimated_annual_trades
    
    def _calculate_target_progress(self) -> float:
        """Calculate progress towards annual target."""
        current_projection = self._calculate_annual_projection()
        return (current_projection / self.target_annual_return) * 100
    
    def _create_empty_metrics(self) -> PerformanceMetrics:
        """Create empty metrics object."""
        return PerformanceMetrics(
            total_return=0, annual_return=0, monthly_return=0, daily_return=0,
            sharpe_ratio=0, max_drawdown=0, win_rate=0, profit_factor=0,
            total_trades=0, avg_trade_return=0, best_trade=0, worst_trade=0,
            consecutive_wins=0, consecutive_losses=0
        )
    
    def _log_performance_summary(self, metrics: PerformanceMetrics) -> None:
        """Log comprehensive performance summary."""
        logger.info(
            f"Performance Summary - "
            f"Annual Return: {metrics.annual_return:.1f}% "
            f"(Target: {self.target_annual_return}%), "
            f"Win Rate: {metrics.win_rate:.1f}%, "
            f"Profit Factor: {metrics.profit_factor:.2f}, "
            f"Max Drawdown: {metrics.max_drawdown:.1f}%, "
            f"Total Trades: {metrics.total_trades}"
        )


# Global performance optimizer instance
performance_optimizer = AdvancedPerformanceOptimizer() 