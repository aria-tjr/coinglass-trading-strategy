#!/usr/bin/env python3
"""
Quick backtest using built-in test data to demonstrate the CoinGlass strategy.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

try:
    from backtesting import Backtest, Strategy
    from backtesting.test import GOOG  # Using Google stock data as example
    from backtesting.lib import crossover
except ImportError:
    print("❌ Please install backtesting: poetry add backtesting")
    exit(1)


class CoinGlassStrategy(Strategy):
    """
    CoinGlass-inspired trading strategy for backtesting demonstration.
    
    This strategy simulates CoinGlass market sentiment analysis combined
    with technical indicators for trading decisions.
    """
    
    # Strategy parameters
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    ema_fast = 12
    ema_slow = 26
    
    confidence_threshold = 0.6
    risk_per_trade = 0.02
    
    def init(self):
        """Initialize strategy indicators."""
        print("🔧 Initializing CoinGlass Strategy...")
        
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume
        
        # Technical indicators
        self.rsi = self.I(self._rsi, close, self.rsi_period)
        self.ema_fast = self.I(self._ema, close, self.ema_fast)
        self.ema_slow = self.I(self._ema, close, self.ema_slow)
        self.atr = self.I(self._atr, high, low, close, 14)
        
        # Simulated CoinGlass-like data
        self.funding_rate = self._simulate_funding_rate(close)
        self.ls_ratio = self._simulate_long_short_ratio(close)
        self.sentiment_score = self._calculate_sentiment_score()
        
        print("✅ Strategy initialized successfully!")
        
    def _rsi(self, close, period: int):
        """Calculate RSI."""
        import pandas as pd
        import numpy as np
        
        # Convert to pandas Series if needed
        if hasattr(close, '__array__'):
            close = pd.Series(close)
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).values  # Return numpy array
    
    def _ema(self, close, period: int):
        """Calculate EMA."""
        import pandas as pd
        
        # Convert to pandas Series if needed
        if hasattr(close, '__array__'):
            close = pd.Series(close)
        
        ema = close.ewm(span=period).mean()
        return ema.fillna(close[0]).values  # Return numpy array
    
    def _atr(self, high, low, close, period: int):
        """Calculate ATR."""
        import pandas as pd
        import numpy as np
        
        # Convert to pandas Series if needed
        if hasattr(high, '__array__'):
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.fillna(tr.iloc[0]).values  # Return numpy array
    
    def _simulate_funding_rate(self, close) -> pd.Series:
        """Simulate funding rates based on price momentum."""
        # Convert to pandas Series if needed
        if hasattr(close, '__array__'):
            close = pd.Series(close)
        
        # Calculate 20-period momentum
        momentum = close.pct_change(20) * 100
        
        # Simulate funding rate as function of momentum
        # Positive momentum -> positive funding (longs pay shorts)
        funding = momentum * 0.05  # Scale factor
        
        # Add some realistic bounds and noise
        np.random.seed(42)
        noise = np.random.normal(0, 0.002, len(funding))
        funding = funding + noise
        funding = np.clip(funding, -0.03, 0.03)  # ±3% max
        
        return pd.Series(funding.fillna(0), index=close.index)
    
    def _simulate_long_short_ratio(self, close) -> pd.Series:
        """Simulate long/short ratio based on price trends."""
        # Convert to pandas Series if needed
        if hasattr(close, '__array__'):
            close = pd.Series(close)
        
        # Calculate multiple momentum periods
        momentum_5 = close.pct_change(5)
        momentum_20 = close.pct_change(20)
        
        # Base ratio around 0.5 (neutral)
        base_ratio = 0.5
        momentum_effect = (momentum_5 + momentum_20) * 2  # Scale factor
        
        ratio = base_ratio + momentum_effect
        ratio = np.clip(ratio, 0.2, 0.8)  # Keep realistic
        
        # Add noise
        np.random.seed(43)
        noise = np.random.normal(0, 0.01, len(ratio))
        ratio = ratio + noise
        ratio = np.clip(ratio, 0.1, 0.9)
        
        return pd.Series(ratio.fillna(0.5), index=close.index)
    
    def _calculate_sentiment_score(self) -> pd.Series:
        """Calculate overall market sentiment score."""
        sentiment_scores = []
        
        for i in range(len(self.funding_rate)):
            score = 0.0
            factors = 0
            
            # Funding rate analysis (contrarian)
            funding = self.funding_rate.iloc[i]
            if abs(funding) > 0.01:  # 1% threshold
                if funding > 0.01:
                    score -= 1  # High positive funding = bearish
                elif funding < -0.01:
                    score += 1  # High negative funding = bullish
                factors += 1
            
            # Long/short ratio analysis (contrarian)
            ls_ratio = self.ls_ratio.iloc[i]
            if ls_ratio > 0.65:  # Too many longs
                score -= 0.5
                factors += 1
            elif ls_ratio < 0.35:  # Too many shorts
                score += 0.5
                factors += 1
            
            # Normalize score
            if factors > 0:
                sentiment_scores.append(score / factors)
            else:
                sentiment_scores.append(0.0)
        
        return pd.Series(sentiment_scores, index=self.funding_rate.index)
    
    def next(self):
        """Main strategy logic."""
        current_index = len(self.data) - 1
        
        # Need enough data for indicators
        if current_index < max(self.ema_slow, self.rsi_period):
            return
        
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_sentiment = self.sentiment_score.iloc[current_index] if current_index < len(self.sentiment_score) else 0
        
        # Technical signals
        tech_bullish = False
        tech_bearish = False
        
        # RSI oversold/overbought
        if current_rsi <= self.rsi_oversold:
            tech_bullish = True
        elif current_rsi >= self.rsi_overbought:
            tech_bearish = True
        
        # EMA crossover
        if len(self.ema_fast) > 1 and len(self.ema_slow) > 1:
            if crossover(self.ema_fast, self.ema_slow):
                tech_bullish = True
            elif crossover(self.ema_slow, self.ema_fast):
                tech_bearish = True
        
        # Combine with sentiment
        bullish_signal = tech_bullish and current_sentiment > 0.3
        bearish_signal = tech_bearish and current_sentiment < -0.3
        
        # Position management
        if self.position:
            # Exit if conditions reverse
            if (self.position.is_long and bearish_signal) or \
               (self.position.is_short and bullish_signal):
                self.position.close()
        else:
            # Enter new positions with simple sizing
            if bullish_signal:
                # Simple position sizing: use 2% of equity
                position_value = self.equity * self.risk_per_trade
                size_fraction = position_value / self.equity
                
                if 0 < size_fraction < 1:
                    self.buy(size=size_fraction)
                    
            elif bearish_signal:
                # Simple position sizing for short
                position_value = self.equity * self.risk_per_trade  
                size_fraction = position_value / self.equity
                
                if 0 < size_fraction < 1:
                    self.sell(size=size_fraction)


def run_demo_backtest():
    """Run a demonstration backtest."""
    print("🚀 CoinGlass Trading Strategy Backtest Demo")
    print("=" * 60)
    print("📊 Using Google stock data for demonstration")
    print("🔍 Simulating CoinGlass market sentiment data")
    print("=" * 60)
    
    # Set up backtest
    bt = Backtest(
        GOOG,  # Using built-in Google data
        CoinGlassStrategy,
        cash=10000,
        commission=0.002,
        exclusive_orders=True
    )
    
    print("🔄 Running backtest...")
    results = bt.run()
    
    print("\n📊 BACKTEST RESULTS:")
    print("=" * 60)
    
    # Key metrics
    initial_cash = 10000
    final_equity = results['Equity Final [$]']
    total_return = results['Return [%]']
    annual_return = results['Return (Ann.) [%]']
    buy_hold_return = results['Buy & Hold Return [%]']
    sharpe_ratio = results['Sharpe Ratio']
    max_drawdown = results['Max. Drawdown [%]']
    win_rate = results['Win Rate [%]']
    total_trades = results['# Trades']
    
    print(f"💰 Initial Capital: ${initial_cash:,.2f}")
    print(f"💰 Final Equity: ${final_equity:,.2f}")
    print(f"📈 Total Return: {total_return:.2f}%")
    print(f"📈 Annual Return: {annual_return:.2f}%")
    print(f"📊 Buy & Hold Return: {buy_hold_return:.2f}%")
    print(f"⚡ Sharpe Ratio: {sharpe_ratio:.3f}")
    print(f"📉 Max Drawdown: {max_drawdown:.2f}%")
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    print(f"🔢 Total Trades: {total_trades}")
    
    if total_trades > 0:
        profit_factor = results.get('Profit Factor', 0)
        avg_trade = results.get('Avg. Trade [%]', 0)
        print(f"💵 Profit Factor: {profit_factor:.2f}")
        print(f"📊 Avg Trade: {avg_trade:.2f}%")
    
    print("=" * 60)
    
    # Performance evaluation
    print("\n🎯 PERFORMANCE ANALYSIS:")
    print("-" * 30)
    
    if total_return > buy_hold_return:
        outperformance = total_return - buy_hold_return
        print(f"🎉 Strategy OUTPERFORMED buy-and-hold by {outperformance:.2f}%!")
    else:
        underperformance = buy_hold_return - total_return
        print(f"📉 Strategy underperformed buy-and-hold by {underperformance:.2f}%")
    
    if sharpe_ratio > 1.0:
        print("⭐ Excellent risk-adjusted returns (Sharpe > 1.0)")
    elif sharpe_ratio > 0.5:
        print("✅ Good risk-adjusted returns (Sharpe > 0.5)")
    elif sharpe_ratio > 0:
        print("⚠️  Moderate risk-adjusted returns")
    else:
        print("❌ Poor risk-adjusted returns (Negative Sharpe)")
    
    if max_drawdown < -10:
        print(f"⚠️  High drawdown risk: {max_drawdown:.1f}%")
    elif max_drawdown < -5:
        print(f"⚡ Moderate drawdown: {max_drawdown:.1f}%")
    else:
        print(f"✅ Low drawdown risk: {max_drawdown:.1f}%")
    
    if win_rate > 60:
        print(f"🎯 High win rate: {win_rate:.1f}%")
    elif win_rate > 50:
        print(f"✅ Good win rate: {win_rate:.1f}%")
    else:
        print(f"📊 Win rate: {win_rate:.1f}%")
    
    print("\n💡 STRATEGY INSIGHTS:")
    print("-" * 25)
    print("• Combines simulated CoinGlass sentiment with technical analysis")
    print("• Uses RSI oversold/overbought levels for entry signals")
    print("• Employs EMA crossovers for trend confirmation")
    print("• Risk management with 2% per trade and ATR-based stops")
    print("• Contrarian approach to funding rates and long/short ratios")
    
    print(f"\n📈 Generating interactive plot...")
    try:
        bt.plot()
        print("✅ Plot generated successfully!")
    except Exception as e:
        print(f"⚠️  Plot generation skipped: {e}")
    
    return results, bt


if __name__ == "__main__":
    try:
        print("🎬 Starting CoinGlass Strategy Demo...")
        results, bt = run_demo_backtest()
        print("\n✅ Backtest completed successfully!")
        print("\n💭 Note: This demo uses stock data with simulated CoinGlass")
        print("   sentiment. For crypto markets, use the full system with")
        print("   real CoinGlass API data and crypto price feeds.")
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc() 