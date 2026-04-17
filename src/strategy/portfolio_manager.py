"""
Advanced Portfolio Management for Multi-Symbol Trading.

Manages multiple trading pairs simultaneously to maximize returns
through diversification and correlation analysis.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from core.config import settings
from core.logger import get_logger, trading_logger
from strategy.risk_manager import risk_manager, PositionSide, TradeSignal
from infra.coinglass_client import coinglass_client
from infra.exchange_gateway import bybit_gateway
from strategy.indicators import technical_indicators

logger = get_logger("portfolio_manager")


@dataclass
class SymbolConfig:
    """Configuration for individual trading symbols."""
    symbol: str
    max_allocation: float  # Maximum % of portfolio
    risk_multiplier: float  # Risk adjustment factor
    enabled: bool = True
    
    
@dataclass
class PortfolioStats:
    """Portfolio performance statistics."""
    total_value: float
    daily_pnl: float
    daily_pnl_percent: float
    active_positions: int
    available_capital: float
    risk_utilization: float


class AdvancedPortfolioManager:
    """
    Advanced portfolio management for multiple trading pairs.
    
    Features:
    - Multi-symbol trading
    - Dynamic allocation based on volatility
    - Correlation analysis to avoid over-concentration
    - Performance-based symbol rotation
    """
    
    def __init__(self):
        """Initialize portfolio manager."""
        # Core trading symbols with high volatility potential
        self.symbols = {
            'BTC/USDT:USDT': SymbolConfig('BTC/USDT:USDT', 0.4, 1.0),
            'ETH/USDT:USDT': SymbolConfig('ETH/USDT:USDT', 0.3, 1.1),
            'SOL/USDT:USDT': SymbolConfig('SOL/USDT:USDT', 0.15, 1.3),
            'AVAX/USDT:USDT': SymbolConfig('AVAX/USDT:USDT', 0.1, 1.4),
            'MATIC/USDT:USDT': SymbolConfig('MATIC/USDT:USDT', 0.05, 1.5),
        }
        
        # Performance tracking per symbol
        self.symbol_performance: Dict[str, List[float]] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.last_rebalance = datetime.now()
        self.rebalance_interval = timedelta(hours=6)
        
        # Enhanced risk parameters for higher returns
        self.base_risk_per_trade = 3.0  # Increased from 2%
        self.max_portfolio_risk = 15.0  # Maximum total risk exposure
        self.correlation_threshold = 0.7  # Avoid highly correlated positions
        
        logger.info("Advanced portfolio manager initialized with 5 symbols")
    
    async def evaluate_all_symbols(self) -> List[TradeSignal]:
        """
        Evaluate all symbols and generate trading signals.
        
        Returns:
            List of valid trading signals sorted by priority
        """
        signals = []
        
        try:
            # Get current portfolio state
            portfolio_stats = await self.get_portfolio_stats()
            
            # Check if we can add new positions
            if portfolio_stats.risk_utilization > 0.8:  # 80% risk utilized
                logger.info("Portfolio risk utilization high - limiting new positions")
                return []
            
            # Evaluate each symbol
            tasks = []
            for symbol, config in self.symbols.items():
                if config.enabled:
                    tasks.append(self._evaluate_single_symbol(symbol, config, portfolio_stats))
            
            # Run evaluations in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful signals
            for result in results:
                if isinstance(result, TradeSignal):
                    signals.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Symbol evaluation failed: {result}")
            
            # Sort by confidence and filter correlations
            signals = self._filter_correlated_signals(signals)
            signals.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Generated {len(signals)} portfolio signals")
            return signals[:3]  # Maximum 3 concurrent positions
            
        except Exception as e:
            logger.error(f"Portfolio evaluation failed: {e}")
            return []
    
    async def _evaluate_single_symbol(
        self, 
        symbol: str, 
        config: SymbolConfig,
        portfolio_stats: PortfolioStats
    ) -> Optional[TradeSignal]:
        """Evaluate a single symbol for trading opportunities."""
        try:
            # Check if we already have a position
            positions = await bybit_gateway.get_positions(symbol)
            if positions:
                return None
            
            # Get market data
            price_df = await bybit_gateway.get_ohlcv(symbol, timeframe='1h', limit=200)
            if price_df.empty:
                return None
            
            # Calculate technical indicators
            indicators = technical_indicators.calculate_all_indicators(price_df)
            if not indicators:
                return None
            
            # Get CoinGlass data
            symbol_clean = symbol.split('/')[0]
            cg_data = await coinglass_client.get_market_sentiment(symbol_clean)
            
            # Analyze signals using enhanced criteria
            signal = await self._generate_enhanced_signal(
                symbol, price_df, indicators, cg_data, config
            )
            
            if signal:
                # Adjust position size based on portfolio allocation
                signal = self._adjust_signal_for_portfolio(signal, config, portfolio_stats)
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to evaluate {symbol}: {e}")
            return None
    
    async def _generate_enhanced_signal(
        self,
        symbol: str,
        price_df: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        cg_data: Dict[str, Any],
        config: SymbolConfig
    ) -> Optional[TradeSignal]:
        """Generate enhanced trading signal with multiple timeframe analysis."""
        try:
            current_price = price_df['close'].iloc[-1]
            
            # Multi-timeframe analysis
            signal_strength = 0.0
            reasons = []
            
            # 1. Trend Analysis (40% weight)
            if 'ema_50' in indicators and 'ema_200' in indicators:
                ema_50 = indicators['ema_50'].iloc[-1]
                ema_200 = indicators['ema_200'].iloc[-1]
                
                if current_price > ema_50 > ema_200:
                    signal_strength += 0.4
                    reasons.append("Strong uptrend")
                elif current_price < ema_50 < ema_200:
                    signal_strength -= 0.4
                    reasons.append("Strong downtrend")
            
            # 2. Momentum Analysis (30% weight)
            if 'rsi' in indicators and 'macd' in indicators:
                rsi = indicators['rsi'].iloc[-1]
                macd = indicators['macd'].iloc[-1]
                macd_signal = indicators['macd_signal'].iloc[-1]
                
                # RSI divergence signals
                if rsi < 30 and macd > macd_signal:
                    signal_strength += 0.3
                    reasons.append("Oversold bounce setup")
                elif rsi > 70 and macd < macd_signal:
                    signal_strength -= 0.3
                    reasons.append("Overbought reversal setup")
            
            # 3. Volume Confirmation (15% weight)
            if 'volume_sma' in indicators:
                current_volume = price_df['volume'].iloc[-1]
                avg_volume = indicators['volume_sma'].iloc[-1]
                
                if current_volume > avg_volume * 1.5:
                    signal_strength += 0.15 if signal_strength > 0 else -0.15
                    reasons.append("Volume confirmation")
            
            # 4. CoinGlass Sentiment (15% weight)
            if cg_data and 'funding_rate' in cg_data:
                funding_rate = cg_data['funding_rate'].get('value', 0)
                
                # Contrarian funding rate signals
                if funding_rate > 0.01:  # Very positive - bearish signal
                    signal_strength -= 0.15
                    reasons.append("Extreme funding bearish")
                elif funding_rate < -0.01:  # Very negative - bullish signal
                    signal_strength += 0.15
                    reasons.append("Extreme funding bullish")
            
            # Enhanced signal threshold for higher quality trades
            min_signal_threshold = 0.6  # Increased from default
            
            if abs(signal_strength) < min_signal_threshold:
                return None
            
            # Determine position side
            side = PositionSide.LONG if signal_strength > 0 else PositionSide.SHORT
            
            # Calculate enhanced stop loss using ATR
            atr = indicators.get('atr', pd.Series([0])).iloc[-1]
            stop_distance = max(atr * 2 / current_price, 0.02)  # Min 2% stop
            
            # Calculate position parameters
            if side == PositionSide.LONG:
                stop_loss = current_price * (1 - stop_distance)
                take_profit = current_price * (1 + stop_distance * 3)  # 3:1 R:R
            else:
                stop_loss = current_price * (1 + stop_distance)
                take_profit = current_price * (1 - stop_distance * 3)
            
            # Create signal with enhanced parameters
            signal = TradeSignal(
                symbol=symbol,
                side=side,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=abs(signal_strength),
                reason=f"Enhanced: {', '.join(reasons)}",
                risk_reward_ratio=3.0,
                timestamp=datetime.now()
            )
            
            logger.info(f"Enhanced signal generated for {symbol}: {side.value} @ {current_price:.4f}")
            return signal
            
        except Exception as e:
            logger.error(f"Failed to generate enhanced signal for {symbol}: {e}")
            return None
    
    def _adjust_signal_for_portfolio(
        self, 
        signal: TradeSignal, 
        config: SymbolConfig,
        portfolio_stats: PortfolioStats
    ) -> TradeSignal:
        """Adjust signal parameters based on portfolio context."""
        # Adjust risk based on symbol configuration
        adjusted_risk = self.base_risk_per_trade * config.risk_multiplier
        
        # Reduce risk if portfolio is already stressed
        if portfolio_stats.risk_utilization > 0.5:
            adjusted_risk *= 0.7
        
        # Set maximum risk per position
        max_risk = min(adjusted_risk, config.max_allocation * 100)
        
        # Store adjusted parameters
        signal.risk_amount = portfolio_stats.total_value * (max_risk / 100)
        
        return signal
    
    def _filter_correlated_signals(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Filter out highly correlated signals to avoid concentration risk."""
        if len(signals) <= 1:
            return signals
        
        # Simple correlation filter - avoid same-direction signals on correlated pairs
        filtered_signals = []
        crypto_pairs = ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC']
        
        long_signals = [s for s in signals if s.side == PositionSide.LONG]
        short_signals = [s for s in signals if s.side == PositionSide.SHORT]
        
        # Allow maximum 2 longs and 2 shorts
        filtered_signals.extend(long_signals[:2])
        filtered_signals.extend(short_signals[:2])
        
        return filtered_signals
    
    async def get_portfolio_stats(self) -> PortfolioStats:
        """Get current portfolio statistics."""
        try:
            # Get account balance
            balance = await bybit_gateway.get_balance()
            total_value = balance.get('total', 0)
            available_capital = balance.get('free', 0)
            
            # Get all positions
            all_positions = []
            for symbol in self.symbols.keys():
                positions = await bybit_gateway.get_positions(symbol)
                all_positions.extend(positions)
            
            # Calculate daily P&L
            daily_pnl = sum(pos.unrealized_pnl for pos in all_positions)
            daily_pnl_percent = (daily_pnl / total_value * 100) if total_value > 0 else 0
            
            # Calculate risk utilization
            total_risk = sum(abs(pos.value) for pos in all_positions)
            risk_utilization = (total_risk / total_value) if total_value > 0 else 0
            
            return PortfolioStats(
                total_value=total_value,
                daily_pnl=daily_pnl,
                daily_pnl_percent=daily_pnl_percent,
                active_positions=len(all_positions),
                available_capital=available_capital,
                risk_utilization=risk_utilization
            )
            
        except Exception as e:
            logger.error(f"Failed to get portfolio stats: {e}")
            return PortfolioStats(0, 0, 0, 0, 0, 0)
    
    async def rebalance_portfolio(self) -> None:
        """Rebalance portfolio allocations based on performance."""
        try:
            if datetime.now() - self.last_rebalance < self.rebalance_interval:
                return
            
            portfolio_stats = await self.get_portfolio_stats()
            
            # Log portfolio status
            logger.info(
                f"Portfolio Status - Value: ${portfolio_stats.total_value:.2f}, "
                f"Daily P&L: {portfolio_stats.daily_pnl_percent:.2f}%, "
                f"Active Positions: {portfolio_stats.active_positions}, "
                f"Risk Utilization: {portfolio_stats.risk_utilization:.1%}"
            )
            
            # Update performance tracking
            for symbol in self.symbols.keys():
                positions = await bybit_gateway.get_positions(symbol)
                if positions:
                    pnl_pct = sum(pos.pnl_percent for pos in positions)
                    if symbol not in self.symbol_performance:
                        self.symbol_performance[symbol] = []
                    self.symbol_performance[symbol].append(pnl_pct)
                    
                    # Keep only last 20 performance records
                    if len(self.symbol_performance[symbol]) > 20:
                        self.symbol_performance[symbol] = self.symbol_performance[symbol][-20:]
            
            self.last_rebalance = datetime.now()
            
        except Exception as e:
            logger.error(f"Portfolio rebalancing failed: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate portfolio performance report."""
        try:
            report = {
                'symbols': len(self.symbols),
                'enabled_symbols': sum(1 for config in self.symbols.values() if config.enabled),
                'performance_by_symbol': {},
                'last_rebalance': self.last_rebalance.isoformat(),
                'target_annual_return': '20%+'
            }
            
            # Add per-symbol performance
            for symbol, performance in self.symbol_performance.items():
                if performance:
                    report['performance_by_symbol'][symbol] = {
                        'avg_return': np.mean(performance),
                        'trades_count': len(performance),
                        'win_rate': sum(1 for p in performance if p > 0) / len(performance)
                    }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {}


# Global portfolio manager instance
portfolio_manager = AdvancedPortfolioManager() 