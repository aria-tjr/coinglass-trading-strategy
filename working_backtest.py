#!/usr/bin/env python3
"""
Working CoinGlass Strategy Backtest with Active Trading
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.test import GOOG
from backtesting.lib import crossover


class ActiveCoinGlassStrategy(Strategy):
    """
    Active CoinGlass trading strategy that generates more trades.
    """
    
    # More aggressive parameters for demonstration
    rsi_period = 14
    rsi_oversold = 40  # Less extreme for more signals
    rsi_overbought = 60  # Less extreme for more signals
    
    ema_fast = 10
    ema_slow = 20
    
    risk_per_trade = 0.15  # 15% position size
    
    def init(self):
        """Initialize strategy."""
        print("🔧 Initializing Active CoinGlass Strategy...")
        
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        
        # Calculate indicators
        self.rsi = self.I(self._rsi, close, self.rsi_period)
        self.ema_fast = self.I(self._ema, close, self.ema_fast)
        self.ema_slow = self.I(self._ema, close, self.ema_slow)
        
        # Simulated CoinGlass sentiment (more volatile for signals)
        self.sentiment = self._simulate_sentiment(close)
        
        print("✅ Active strategy initialized!")
        
    def _rsi(self, close, period):
        """Calculate RSI."""
        close_series = pd.Series(close) if hasattr(close, '__array__') else close
        delta = close_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).values
    
    def _ema(self, close, period):
        """Calculate EMA."""
        close_series = pd.Series(close) if hasattr(close, '__array__') else close
        return close_series.ewm(span=period).mean().values
    
    def _simulate_sentiment(self, close):
        """Simulate market sentiment with higher volatility."""
        close_series = pd.Series(close) if hasattr(close, '__array__') else close
        
        # Calculate momentum-based sentiment
        momentum = close_series.pct_change(10) * 100
        volatility = close_series.rolling(10).std()
        
        # Create oscillating sentiment between -1 and 1
        sentiment = np.sin(np.arange(len(close_series)) / 10) * 0.5
        sentiment += momentum.fillna(0) * 0.02  # Add momentum component
        sentiment = np.clip(sentiment, -1, 1)
        
        return sentiment
    
    def next(self):
        """Main trading logic."""
        # Skip if not enough data
        if len(self.data) < max(self.ema_slow, self.rsi_period):
            return
        
        current_rsi = self.rsi[-1]
        current_sentiment = self.sentiment[len(self.data) - 1]
        
        # More aggressive signal generation
        strong_bullish = (current_rsi < self.rsi_oversold and current_sentiment > 0.2) or \
                        (crossover(self.ema_fast, self.ema_slow) and current_sentiment > 0)
        
        strong_bearish = (current_rsi > self.rsi_overbought and current_sentiment < -0.2) or \
                        (crossover(self.ema_slow, self.ema_fast) and current_sentiment < 0)
        
        # Close position if signal reverses
        if self.position:
            if (self.position.is_long and strong_bearish) or \
               (self.position.is_short and strong_bullish):
                self.position.close()
        
        # Enter new positions
        elif strong_bullish and not self.position:
            self.buy(size=self.risk_per_trade)
            
        elif strong_bearish and not self.position:
            self.sell(size=self.risk_per_trade)


def run_active_backtest():
    """Run an active trading backtest."""
    print("🚀 Active CoinGlass Trading Strategy Backtest")
    print("=" * 60)
    print("📊 Using Google stock data (2004-2013)")
    print("🎯 More aggressive parameters for active trading")
    print("=" * 60)
    
    # Run backtest
    bt = Backtest(
        GOOG,
        ActiveCoinGlassStrategy,
        cash=10000,
        commission=0.002,
        exclusive_orders=True
    )
    
    print("🔄 Running backtest...")
    results = bt.run()
    
    print("\n📊 BACKTEST RESULTS:")
    print("=" * 60)
    
    # Extract key metrics
    initial_cash = 10000
    final_equity = results['Equity Final [$]']
    total_return = results['Return [%]']
    annual_return = results['Return (Ann.) [%]']
    buy_hold_return = results['Buy & Hold Return [%]']
    sharpe_ratio = results['Sharpe Ratio']
    max_drawdown = results['Max. Drawdown [%]']
    win_rate = results['Win Rate [%]'] if results['# Trades'] > 0 else 0
    total_trades = results['# Trades']
    exposure_time = results['Exposure Time [%]']
    
    print(f"💰 Initial Capital: ${initial_cash:,.2f}")
    print(f"💰 Final Equity: ${final_equity:,.2f}")
    print(f"📈 Total Return: {total_return:.2f}%")
    print(f"📈 Annual Return: {annual_return:.2f}%")
    print(f"📊 Buy & Hold Return: {buy_hold_return:.2f}%")
    print(f"⚡ Sharpe Ratio: {sharpe_ratio:.3f}")
    print(f"📉 Max Drawdown: {max_drawdown:.2f}%")
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    print(f"🔢 Total Trades: {total_trades}")
    print(f"⏰ Exposure Time: {exposure_time:.1f}%")
    
    if total_trades > 0:
        profit_factor = results.get('Profit Factor', 0)
        avg_trade = results.get('Avg. Trade [%]', 0)
        best_trade = results.get('Best Trade [%]', 0)
        worst_trade = results.get('Worst Trade [%]', 0)
        
        print(f"💵 Profit Factor: {profit_factor:.2f}")
        print(f"📊 Avg Trade: {avg_trade:.2f}%")
        print(f"🎯 Best Trade: {best_trade:.2f}%")
        print(f"💥 Worst Trade: {worst_trade:.2f}%")
    
    print("=" * 60)
    
    # Performance analysis
    print("\n🎯 PERFORMANCE ANALYSIS:")
    print("-" * 40)
    
    if total_return > buy_hold_return:
        outperformance = total_return - buy_hold_return
        print(f"🎉 Strategy OUTPERFORMED buy-and-hold by {outperformance:.2f}%!")
    else:
        underperformance = buy_hold_return - total_return
        print(f"📉 Strategy underperformed buy-and-hold by {underperformance:.2f}%")
    
    # Risk analysis
    if sharpe_ratio > 1.5:
        print("⭐ Outstanding risk-adjusted returns (Sharpe > 1.5)")
    elif sharpe_ratio > 1.0:
        print("✨ Excellent risk-adjusted returns (Sharpe > 1.0)")
    elif sharpe_ratio > 0.5:
        print("✅ Good risk-adjusted returns (Sharpe > 0.5)")
    elif sharpe_ratio > 0:
        print("⚠️  Moderate risk-adjusted returns")
    else:
        print("❌ Poor risk-adjusted returns (Negative Sharpe)")
    
    # Drawdown analysis
    if max_drawdown > -20:
        print(f"🚨 High drawdown risk: {max_drawdown:.1f}%")
    elif max_drawdown > -10:
        print(f"⚠️  Moderate drawdown: {max_drawdown:.1f}%")
    else:
        print(f"✅ Low drawdown risk: {max_drawdown:.1f}%")
    
    # Trading activity analysis
    if total_trades > 50:
        print(f"📈 High trading activity: {total_trades} trades")
    elif total_trades > 20:
        print(f"📊 Moderate trading activity: {total_trades} trades")
    elif total_trades > 0:
        print(f"📉 Low trading activity: {total_trades} trades")
    else:
        print("⚠️  No trades generated - strategy too conservative")
    
    # Win rate analysis
    if win_rate > 60:
        print(f"🎯 High win rate: {win_rate:.1f}%")
    elif win_rate > 50:
        print(f"✅ Good win rate: {win_rate:.1f}%")
    elif win_rate > 0:
        print(f"📊 Win rate: {win_rate:.1f}%")
    
    print("\n💡 STRATEGY FEATURES:")
    print("-" * 30)
    print("✓ CoinGlass-inspired sentiment analysis")
    print("✓ RSI momentum indicators") 
    print("✓ EMA trend confirmation")
    print("✓ Risk-managed position sizing")
    print("✓ Both long and short positions")
    print("✓ Automatic exit signals")
    
    print("\n🔧 PARAMETERS USED:")
    print("-" * 25)
    print(f"• RSI Period: {results._strategy.rsi_period}")
    print(f"• RSI Oversold: {results._strategy.rsi_oversold}")
    print(f"• RSI Overbought: {results._strategy.rsi_overbought}")
    print(f"• EMA Fast: {results._strategy.ema_fast}")
    print(f"• EMA Slow: {results._strategy.ema_slow}")
    print(f"• Position Size: {results._strategy.risk_per_trade*100:.0f}%")
    
    print(f"\n📈 Generating interactive plot...")
    try:
        bt.plot()
        print("✅ Interactive plot opened in browser!")
    except Exception as e:
        print(f"⚠️  Plot generation failed: {str(e)[:100]}...")
    
    return results, bt


if __name__ == "__main__":
    try:
        print("🎬 Starting Active CoinGlass Strategy Demo...")
        print()
        
        results, bt = run_active_backtest()
        
        print("\n" + "="*60)
        print("✅ BACKTEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\n🎁 What you've accomplished:")
        print("• ✅ Built a complete CoinGlass trading strategy")
        print("• ✅ Integrated technical analysis with market sentiment")
        print("• ✅ Implemented proper risk management")
        print("• ✅ Backtested with historical data")
        print("• ✅ Generated comprehensive performance metrics")
        
        print("\n🚀 Next Steps:")
        print("• 📊 Run backtests on crypto data (BTC, ETH)")
        print("• 🔧 Optimize strategy parameters")
        print("• 📈 Add real CoinGlass API integration")
        print("• 🤖 Deploy live trading bot")
        print("• 📱 Set up Telegram notifications")
        
        print("\n💭 Note: This demo simulates CoinGlass sentiment.")
        print("   For live trading, connect to real CoinGlass API")
        print("   and crypto exchanges for actual market data.")
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc() 