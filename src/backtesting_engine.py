"""
Backtesting Engine for telegram_coinglass_trader.

Adapts the existing trading strategy for backtesting using backtesting.py framework.
Simulates CoinGlass data patterns and integrates with existing technical indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from core.logger import get_logger
from strategy.indicators import TechnicalIndicators
from strategy.risk_manager import PositionSide

# For backtesting, we don't need live API keys, so we'll use mock settings
import os
os.environ.setdefault('COINGLASS_API_KEY', 'backtest_mock')
os.environ.setdefault('BYBIT_API_KEY', 'backtest_mock')
os.environ.setdefault('BYBIT_API_SECRET', 'backtest_mock')
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'backtest_mock')
os.environ.setdefault('TELEGRAM_CHAT_ID', '12345')

from core.config import settings

logger = get_logger("backtesting_engine")


class CoinGlassSimulator:
    """
    Simulates CoinGlass-like market data for backtesting purposes.
    
    Since historical CoinGlass data isn't available for backtesting,
    we simulate realistic funding rates, OI changes, and long/short ratios
    based on price action and volatility patterns.
    """
    
    def __init__(self, price_data: pd.DataFrame):
        """Initialize with price data."""
        self.price_data = price_data.copy()
        self.indicators = TechnicalIndicators()
        
    def simulate_funding_rate(self) -> pd.Series:
        """
        Simulate funding rates based on price momentum and volatility.
        
        Funding rates tend to be:
        - Positive during strong uptrends (longs pay shorts)
        - Negative during strong downtrends (shorts pay longs)
        - Correlated with price momentum and volatility
        """
        close = self.price_data['Close']
        
        # Calculate price momentum (20-period ROC)
        momentum = close.pct_change(20) * 100
        
        # Calculate volatility (20-period rolling std)
        volatility = close.pct_change().rolling(20).std() * 100
        
        # Base funding rate simulation
        # Positive momentum -> positive funding (bullish bias)
        # High volatility -> higher absolute funding
        base_funding = momentum * 0.1  # Scale factor
        volatility_multiplier = 1 + (volatility / volatility.mean() - 1) * 0.5
        
        funding_rate = base_funding * volatility_multiplier
        
        # Add some noise and cap extreme values
        noise = np.random.normal(0, 0.005, len(funding_rate))
        funding_rate = funding_rate + noise
        funding_rate = np.clip(funding_rate, -0.05, 0.05)  # Cap at ±5%
        
        return pd.Series(funding_rate, index=close.index, name='funding_rate')
    
    def simulate_long_short_ratio(self) -> pd.Series:
        """
        Simulate long/short ratio based on price action and momentum.
        
        Ratio tends to be:
        - Higher during uptrends (more longs)
        - Lower during downtrends (more shorts)
        - Mean-reverting around 0.5
        """
        close = self.price_data['Close']
        
        # Calculate short-term momentum
        momentum_5 = close.pct_change(5)
        momentum_20 = close.pct_change(20)
        
        # Base ratio starts at 0.5 (neutral)
        base_ratio = 0.5
        
        # Adjust based on momentum
        momentum_effect = (momentum_5 + momentum_20) * 5  # Scale factor
        
        # Apply mean reversion
        ratio = base_ratio + momentum_effect
        ratio = np.clip(ratio, 0.2, 0.8)  # Keep within realistic bounds
        
        # Add noise
        noise = np.random.normal(0, 0.02, len(ratio))
        ratio = ratio + noise
        ratio = np.clip(ratio, 0.1, 0.9)
        
        return pd.Series(ratio, index=close.index, name='long_short_ratio')
    
    def simulate_open_interest_change(self) -> pd.Series:
        """
        Simulate Open Interest changes based on volume and volatility.
        
        OI changes tend to correlate with:
        - High volume periods
        - High volatility periods
        - Strong directional moves
        """
        volume = self.price_data['Volume']
        close = self.price_data['Close']
        
        # Calculate price change and volume change
        price_change = abs(close.pct_change())
        volume_norm = volume / volume.rolling(20).mean()
        
        # OI tends to increase with volume and volatility
        base_oi_change = (volume_norm - 1) * price_change * 100
        
        # Add trend component
        trend = close.pct_change(10)
        trend_effect = abs(trend) * 50  # Strong trends increase OI
        
        oi_change = base_oi_change + trend_effect
        
        # Add noise and realistic bounds
        noise = np.random.normal(0, 2, len(oi_change))
        oi_change = oi_change + noise
        oi_change = np.clip(oi_change, -20, 20)  # ±20% daily change max
        
        return pd.Series(oi_change, index=close.index, name='oi_change')
    
    def generate_coinglass_data(self) -> Dict[str, pd.Series]:
        """Generate all simulated CoinGlass data."""
        return {
            'funding_rate': self.simulate_funding_rate(),
            'long_short_ratio': self.simulate_long_short_ratio(),
            'oi_change': self.simulate_open_interest_change()
        }


class CoinGlassTradingStrategy(Strategy):
    """
    Backtesting.py Strategy that implements the CoinGlass trading logic.
    
    This adapts the existing strategy engine for use with backtesting.py,
    combining simulated CoinGlass data with technical analysis.
    """
    
    # Strategy parameters (can be optimized)
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    ema_fast = 12
    ema_slow = 26
    
    funding_threshold = 0.01
    ls_ratio_threshold = 0.65
    oi_change_threshold = 5.0
    
    risk_per_trade = 0.02  # 2% risk per trade
    
    def init(self):
        """Initialize strategy indicators and data."""
        logger.info("Initializing CoinGlass backtesting strategy...")
        
        # Get price data
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume
        
        # Create CoinGlass simulator
        price_df = pd.DataFrame({
            'Close': close,
            'High': high,
            'Low': low,
            'Volume': volume
        })
        
        self.cg_simulator = CoinGlassSimulator(price_df)
        self.cg_data = self.cg_simulator.generate_coinglass_data()
        
        # Calculate technical indicators
        self.rsi = self.I(self._calculate_rsi, close, self.rsi_period)
        self.ema_fast = self.I(self._calculate_ema, close, self.ema_fast)
        self.ema_slow = self.I(self._calculate_ema, close, self.ema_slow)
        self.atr = self.I(self._calculate_atr, high, low, close, 14)
        
        # Store additional data
        self.funding_rate = self.cg_data['funding_rate']
        self.ls_ratio = self.cg_data['long_short_ratio']
        self.oi_change = self.cg_data['oi_change']
        
        logger.info("Strategy initialization complete")
    
    def _calculate_rsi(self, close, period: int):
        """Calculate RSI indicator."""
        close = pd.Series(close) if not isinstance(close, pd.Series) else close
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).values  # Return numpy array with NaN filled
    
    def _calculate_ema(self, close, period: int):
        """Calculate EMA indicator."""
        close = pd.Series(close) if not isinstance(close, pd.Series) else close
        return close.ewm(span=period).mean().values  # Return numpy array
    
    def _calculate_atr(self, high, low, close, period: int):
        """Calculate ATR indicator."""
        high = pd.Series(high) if not isinstance(high, pd.Series) else high
        low = pd.Series(low) if not isinstance(low, pd.Series) else low
        close = pd.Series(close) if not isinstance(close, pd.Series) else close
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.fillna(0).values  # Return numpy array with NaN filled
    
    def analyze_coinglass_sentiment(self, index: int) -> Tuple[str, float]:
        """
        Analyze CoinGlass data for market sentiment.
        
        Returns:
            Tuple of (sentiment, confidence)
        """
        if index >= len(self.funding_rate):
            return "neutral", 0.0
            
        funding = self.funding_rate.iloc[index]
        ls_ratio = self.ls_ratio.iloc[index]
        oi_change = self.oi_change.iloc[index]
        
        sentiment_score = 0.0
        factors = 0
        
        # Analyze funding rate
        if abs(funding) > self.funding_threshold:
            if funding > self.funding_threshold:
                sentiment_score -= 2  # High positive funding = bearish
            elif funding < -self.funding_threshold:
                sentiment_score += 2  # High negative funding = bullish
            factors += 1
        
        # Analyze long/short ratio
        if ls_ratio > self.ls_ratio_threshold:
            sentiment_score -= 1  # Too many longs = bearish
            factors += 1
        elif ls_ratio < (1 - self.ls_ratio_threshold):
            sentiment_score += 1  # Too many shorts = bullish
            factors += 1
        
        # Analyze OI changes
        if abs(oi_change) > self.oi_change_threshold:
            # Get price change for context
            if index > 0:
                price_change = (self.data.Close[index] - self.data.Close[index-1]) / self.data.Close[index-1]
                if oi_change > 0 and price_change > 0:
                    sentiment_score += 1  # OI up with price up = bullish
                elif oi_change > 0 and price_change < 0:
                    sentiment_score -= 1  # OI up with price down = bearish
                factors += 1
        
        if factors == 0:
            return "neutral", 0.0
        
        # Determine sentiment and confidence
        avg_score = sentiment_score / factors
        confidence = min(abs(avg_score) / 2.0, 1.0)
        
        if avg_score > 0.5:
            return "bullish", confidence
        elif avg_score < -0.5:
            return "bearish", confidence
        else:
            return "neutral", confidence
    
    def analyze_technical_signals(self, index: int) -> Tuple[str, float]:
        """
        Analyze technical indicators for trading signals.
        
        Returns:
            Tuple of (signal, confidence)
        """
        if index < max(self.ema_slow, self.rsi_period):
            return "neutral", 0.0
        
        current_rsi = self.rsi[index]
        current_price = self.data.Close[index]
        
        signal_score = 0.0
        factors = 0
        
        # RSI analysis
        if current_rsi <= self.rsi_oversold:
            signal_score += 2  # Oversold = bullish
            factors += 1
        elif current_rsi >= self.rsi_overbought:
            signal_score -= 2  # Overbought = bearish
            factors += 1
        
        # EMA crossover analysis
        if index > 0:
            prev_fast = self.ema_fast[index-1]
            prev_slow = self.ema_slow[index-1]
            curr_fast = self.ema_fast[index]
            curr_slow = self.ema_slow[index]
            
            # Check for crossovers
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                signal_score += 1  # Bullish crossover
                factors += 1
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                signal_score -= 1  # Bearish crossover
                factors += 1
        
        if factors == 0:
            return "neutral", 0.0
        
        # Determine signal and confidence
        avg_score = signal_score / factors
        confidence = min(abs(avg_score) / 2.0, 1.0)
        
        if avg_score > 0.5:
            return "bullish", confidence
        elif avg_score < -0.5:
            return "bearish", confidence
        else:
            return "neutral", confidence
    
    def calculate_position_size(self, current_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management."""
        if stop_loss <= 0 or current_price <= 0:
            return 0.0
        
        account_balance = self.equity
        risk_amount = account_balance * self.risk_per_trade
        
        # Calculate risk per share
        risk_per_share = abs(current_price - stop_loss)
        
        if risk_per_share <= 0:
            return 0.0
        
        # Calculate position size
        position_size = risk_amount / risk_per_share
        max_position_value = account_balance * 0.95  # Max 95% of account
        max_shares = max_position_value / current_price
        
        return min(position_size, max_shares)
    
    def next(self):
        """Main strategy logic called for each bar."""
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        
        # Skip if not enough data
        if current_index < max(self.ema_slow, self.rsi_period):
            return
        
        # Analyze market conditions
        cg_sentiment, cg_confidence = self.analyze_coinglass_sentiment(current_index)
        tech_signal, tech_confidence = self.analyze_technical_signals(current_index)
        
        # Require confluence of signals
        combined_confidence = (cg_confidence + tech_confidence) / 2
        
        # Close position if confidence is low
        if self.position and combined_confidence < 0.3:
            self.position.close()
            return
        
        # Generate trading signals
        if (cg_sentiment == "bullish" and tech_signal == "bullish" and 
            combined_confidence > 0.6):
            
            # Calculate stop loss (2 ATR below entry)
            current_atr = self.atr[-1]
            stop_loss = current_price - (2 * current_atr)
            
            # Calculate position size
            size = self.calculate_position_size(current_price, stop_loss)
            
            if size > 0 and not self.position:
                self.buy(size=size)
                
        elif (cg_sentiment == "bearish" and tech_signal == "bearish" and 
              combined_confidence > 0.6):
            
            # Calculate stop loss (2 ATR above entry)
            current_atr = self.atr[-1]
            stop_loss = current_price + (2 * current_atr)
            
            # Calculate position size
            size = self.calculate_position_size(current_price, stop_loss)
            
            if size > 0 and not self.position:
                self.sell(size=size)


def get_crypto_data(symbol: str, period: str = "1y", interval: str = "1h") -> pd.DataFrame:
    """
    Get cryptocurrency data from Yahoo Finance.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USD', 'ETH-USD')
        period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching {symbol} data for period {period} with interval {interval}")
    
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval)
    
    if data.empty:
        raise ValueError(f"No data found for symbol {symbol}")
    
    # Clean up the data
    data.index = pd.to_datetime(data.index)
    data = data.dropna()
    
    logger.info(f"Retrieved {len(data)} data points from {data.index[0]} to {data.index[-1]}")
    
    return data


def run_backtest(
    symbol: str = "BTC-USD",
    period: str = "1y", 
    interval: str = "1h",
    cash: float = 10000,
    commission: float = 0.002,
    **strategy_params
) -> Tuple[Any, Any]:
    """
    Run a backtest with the CoinGlass trading strategy.
    
    Args:
        symbol: Trading symbol
        period: Data period
        interval: Data interval  
        cash: Initial cash
        commission: Trading commission
        **strategy_params: Strategy parameters to override
        
    Returns:
        Tuple of (backtest_results, backtest_object)
    """
    logger.info(f"Starting backtest for {symbol}")
    
    # Get data
    data = get_crypto_data(symbol, period, interval)
    
    # Create strategy class with custom parameters
    class CustomStrategy(CoinGlassTradingStrategy):
        pass
    
    # Override strategy parameters
    for param, value in strategy_params.items():
        setattr(CustomStrategy, param, value)
    
    # Run backtest
    bt = Backtest(
        data, 
        CustomStrategy,
        cash=cash,
        commission=commission,
        exclusive_orders=True
    )
    
    results = bt.run()
    
    logger.info("Backtest completed successfully")
    logger.info(f"Final equity: ${results['Equity Final [$]']:,.2f}")
    logger.info(f"Total return: {results['Return [%]']:.2f}%")
    logger.info(f"Sharpe ratio: {results['Sharpe Ratio']:.2f}")
    logger.info(f"Max drawdown: {results['Max. Drawdown [%]']:.2f}%")
    
    return results, bt


def optimize_strategy(
    symbol: str = "BTC-USD",
    period: str = "6mo",
    interval: str = "1h", 
    cash: float = 10000,
    commission: float = 0.002
) -> Any:
    """
    Optimize strategy parameters using backtesting.py's optimizer.
    
    Returns:
        Optimization results
    """
    logger.info(f"Starting strategy optimization for {symbol}")
    
    # Get data
    data = get_crypto_data(symbol, period, interval)
    
    # Create backtest
    bt = Backtest(
        data,
        CoinGlassTradingStrategy, 
        cash=cash,
        commission=commission,
        exclusive_orders=True
    )
    
    # Optimize parameters
    results = bt.optimize(
        rsi_period=range(10, 21, 2),
        rsi_oversold=range(25, 36, 5),
        rsi_overbought=range(65, 76, 5),
        ema_fast=range(8, 16, 2),
        ema_slow=range(20, 32, 4),
        funding_threshold=[0.005, 0.01, 0.015, 0.02],
        maximize='Sharpe Ratio',
        constraint=lambda p: p.ema_fast < p.ema_slow
    )
    
    logger.info("Optimization completed")
    logger.info(f"Best parameters: {results._strategy}")
    logger.info(f"Best Sharpe ratio: {results['Sharpe Ratio']:.2f}")
    
    return results


if __name__ == "__main__":
    # Example usage
    results, bt = run_backtest(
        symbol="BTC-USD",
        period="6mo", 
        interval="1h",
        cash=10000,
        commission=0.002
    )
    
    print("\n" + "="*50)
    print("BACKTEST RESULTS")
    print("="*50)
    print(results)
    
    # Plot results
    bt.plot() 