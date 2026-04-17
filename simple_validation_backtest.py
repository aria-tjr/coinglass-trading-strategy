#!/usr/bin/env python3
"""
Simple Working Backtest for Validation System Demo.

This demonstrates a properly validated crypto trading strategy using 
real data and industry best practices.
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from core.logger import get_logger

logger = get_logger("simple_validation")


class SimpleCryptoStrategy(Strategy):
    """
    Simple but effective crypto trading strategy for validation testing.
    
    Uses basic technical indicators with proper risk management.
    """
    
    # Strategy parameters
    sma_fast = 20
    sma_slow = 50
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    risk_per_trade = 0.02  # 2% risk per trade
    
    def init(self):
        """Initialize strategy indicators."""
        close = self.data.Close
        
        # Simple Moving Averages
        self.sma_fast = self.I(lambda x: pd.Series(x).rolling(self.sma_fast).mean(), close)
        self.sma_slow = self.I(lambda x: pd.Series(x).rolling(self.sma_slow).mean(), close)
        
        # RSI
        def rsi(close, period):
            close = pd.Series(close)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return (100 - (100 / (1 + rs))).fillna(50)
        
        self.rsi = self.I(rsi, close, self.rsi_period)
    
    def next(self):
        """Main strategy logic."""
        # Skip if not enough data
        if len(self.data) < self.sma_slow:
            return
        
        # Get current values
        current_rsi = self.rsi[-1]
        current_price = self.data.Close[-1]
        
        # Exit conditions
        if self.position:
            # Exit long if bearish crossover or RSI overbought
            if (self.position.is_long and 
                (crossover(self.sma_slow, self.sma_fast) or current_rsi > self.rsi_overbought)):
                self.position.close()
            
            # Exit short if bullish crossover or RSI oversold  
            elif (self.position.is_short and 
                  (crossover(self.sma_fast, self.sma_slow) or current_rsi < self.rsi_oversold)):
                self.position.close()
        
        # Entry conditions
        else:
            # Long entry: bullish crossover + RSI not overbought
            if (crossover(self.sma_fast, self.sma_slow) and 
                current_rsi < self.rsi_overbought):
                self.buy(size=self.risk_per_trade)
            
            # Short entry: bearish crossover + RSI not oversold
            elif (crossover(self.sma_slow, self.sma_fast) and 
                  current_rsi > self.rsi_oversold):
                self.sell(size=self.risk_per_trade)


def get_crypto_data(symbol: str, period: str = "1y", interval: str = "1h"):
    """Fetch crypto data from Yahoo Finance."""
    try:
        logger.info(f"Fetching {symbol} data for period {period} with interval {interval}")
        
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            logger.error(f"No data retrieved for {symbol}")
            return None
        
        # Clean data
        data = data.dropna()
        data.index = pd.to_datetime(data.index)
        
        logger.info(f"Retrieved {len(data)} data points from {data.index[0]} to {data.index[-1]}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return None


def run_validation_backtest(
    symbol: str = "BTC-USD",
    period: str = "1y",
    interval: str = "1h"
):
    """Run a validated backtest with proper analysis."""
    
    logger.info("🎯 SIMPLE CRYPTO STRATEGY VALIDATION")
    logger.info("=" * 60)
    
    # Fetch data
    data = get_crypto_data(symbol, period, interval)
    if data is None:
        logger.error("Cannot run backtest - no data available")
        return None
    
    logger.info(f"📊 Data Quality Check:")
    logger.info(f"   Records: {len(data)}")
    logger.info(f"   Missing Values: {data.isnull().sum().sum()}")
    logger.info(f"   Date Range: {data.index[0]} to {data.index[-1]}")
    logger.info(f"   Zero Volume: {(data['Volume'] == 0).sum()} ({(data['Volume'] == 0).mean():.1%})")
    
    # Run backtests with different fee scenarios
    fee_scenarios = [
        {'commission': 0.0005, 'name': 'Low Fees (0.05%)'},
        {'commission': 0.001, 'name': 'Standard Fees (0.1%)'},
        {'commission': 0.002, 'name': 'High Fees (0.2%)'}
    ]
    
    results = {}
    
    for scenario in fee_scenarios:
        logger.info(f"\n🔄 Running backtest: {scenario['name']}")
        
        bt = Backtest(
            data,
            SimpleCryptoStrategy,
            cash=100000,  # Increased for BTC trading
            commission=scenario['commission'],
            exclusive_orders=True
        )
        
        try:
            result = bt.run()
            results[scenario['name']] = result
            
            logger.info(f"   Total Return: {result['Return [%]']:.2f}%")
            logger.info(f"   Annual Return: {result['Return (Ann.) [%]']:.2f}%")
            logger.info(f"   Sharpe Ratio: {result['Sharpe Ratio']:.3f}")
            logger.info(f"   Max Drawdown: {result['Max. Drawdown [%]']:.2f}%")
            logger.info(f"   Total Trades: {result['# Trades']}")
            logger.info(f"   Win Rate: {result['Win Rate [%]']:.1f}%")
            
        except Exception as e:
            logger.error(f"   Backtest failed: {e}")
            results[scenario['name']] = None
    
    # Analysis
    logger.info(f"\n📊 VALIDATION ANALYSIS:")
    logger.info("=" * 60)
    
    valid_results = {k: v for k, v in results.items() if v is not None}
    
    if not valid_results:
        logger.error("❌ All backtests failed - strategy needs debugging")
        return None
    
    # Compare performance across fee scenarios
    standard_result = valid_results.get('Standard Fees (0.1%)')
    if standard_result is not None:
        annual_return = standard_result['Return (Ann.) [%]']
        sharpe_ratio = standard_result['Sharpe Ratio']
        max_drawdown = standard_result['Max. Drawdown [%]']
        total_trades = standard_result['# Trades']
        win_rate = standard_result['Win Rate [%]']
        
        logger.info(f"📈 PERFORMANCE ASSESSMENT:")
        
        # Return analysis
        if annual_return >= 20:
            logger.info(f"   ✅ EXCELLENT: {annual_return:.1f}% annual return exceeds 20% target")
        elif annual_return >= 10:
            logger.info(f"   ✅ GOOD: {annual_return:.1f}% annual return is solid")
        elif annual_return > 0:
            logger.info(f"   ⚠️  MODERATE: {annual_return:.1f}% annual return is positive but low")
        else:
            logger.info(f"   ❌ POOR: {annual_return:.1f}% annual return is negative")
        
        # Risk analysis
        if sharpe_ratio >= 1.5:
            logger.info(f"   ✅ EXCELLENT: Sharpe ratio {sharpe_ratio:.2f} shows outstanding risk-adjusted returns")
        elif sharpe_ratio >= 1.0:
            logger.info(f"   ✅ GOOD: Sharpe ratio {sharpe_ratio:.2f} shows strong risk-adjusted returns")
        elif sharpe_ratio >= 0.5:
            logger.info(f"   ⚠️  MODERATE: Sharpe ratio {sharpe_ratio:.2f} is acceptable")
        else:
            logger.info(f"   ❌ POOR: Sharpe ratio {sharpe_ratio:.2f} shows poor risk-adjusted returns")
        
        # Drawdown analysis
        if max_drawdown > -10:
            logger.info(f"   ✅ LOW RISK: Max drawdown {max_drawdown:.1f}% is manageable")
        elif max_drawdown > -20:
            logger.info(f"   ⚠️  MODERATE RISK: Max drawdown {max_drawdown:.1f}% requires attention")
        else:
            logger.info(f"   ❌ HIGH RISK: Max drawdown {max_drawdown:.1f}% is concerning")
        
        # Trade frequency
        if total_trades >= 50:
            logger.info(f"   ✅ SUFFICIENT: {total_trades} trades provide good statistical sample")
        elif total_trades >= 20:
            logger.info(f"   ⚠️  MODERATE: {total_trades} trades provide minimum sample size")
        else:
            logger.info(f"   ❌ INSUFFICIENT: {total_trades} trades is too few for reliable results")
        
        # Win rate
        if win_rate >= 60:
            logger.info(f"   ✅ EXCELLENT: {win_rate:.1f}% win rate is very good")
        elif win_rate >= 50:
            logger.info(f"   ✅ GOOD: {win_rate:.1f}% win rate is solid")
        else:
            logger.info(f"   ⚠️  LOW: {win_rate:.1f}% win rate needs improvement")
    
    # Fee impact analysis
    if len(valid_results) > 1:
        logger.info(f"\n💰 FEE IMPACT ANALYSIS:")
        low_fees = valid_results.get('Low Fees (0.05%)')
        high_fees = valid_results.get('High Fees (0.2%)')
        
        if low_fees is not None and high_fees is not None:
            fee_impact = low_fees['Return (Ann.) [%]'] - high_fees['Return (Ann.) [%]']
            logger.info(f"   Fee Impact: {fee_impact:.2f}% annual return reduction")
            logger.info(f"   Low Fees Return: {low_fees['Return (Ann.) [%]']:.2f}%")
            logger.info(f"   High Fees Return: {high_fees['Return (Ann.) [%]']:.2f}%")
            
            if fee_impact > 5:
                logger.info(f"   ⚠️  HIGH IMPACT: Fees significantly affect profitability")
            else:
                logger.info(f"   ✅ LOW IMPACT: Strategy is robust to fee variations")
    
    # Final verdict
    logger.info(f"\n🎯 FINAL VALIDATION VERDICT:")
    logger.info("=" * 60)
    
    if standard_result is not None:
        score = 0
        score += min(annual_return / 20, 1) * 40  # Performance (40%)
        score += min(max(sharpe_ratio, 0) / 1.5, 1) * 30  # Risk-adjusted (30%)
        score += min(total_trades / 50, 1) * 15  # Statistical significance (15%)
        score += min(win_rate / 60, 1) * 15  # Win rate (15%)
        
        logger.info(f"   Overall Score: {score:.0f}/100")
        
        if score >= 80:
            logger.info(f"   🎉 VERDICT: EXCELLENT - Ready for live trading")
        elif score >= 60:
            logger.info(f"   ✅ VERDICT: GOOD - Suitable for live trading with monitoring")
        elif score >= 40:
            logger.info(f"   ⚠️  VERDICT: MODERATE - Needs improvements before live trading")
        else:
            logger.info(f"   ❌ VERDICT: POOR - Significant strategy improvements needed")
    
    logger.info("=" * 60)
    return results


async def main():
    """Main validation runner."""
    
    print("\n🎯 CRYPTO STRATEGY VALIDATION SYSTEM")
    print("Industry Best Practices Implementation")
    print("=" * 60)
    
    # Test multiple crypto symbols
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        results = run_validation_backtest(symbol, period="6mo", interval="1h")
        
        if results:
            print(f"✅ {symbol} validation completed")
        else:
            print(f"❌ {symbol} validation failed")
    
    print(f"\n✅ Validation system demonstration completed!")
    print(f"📄 Check logs for detailed analysis")


if __name__ == "__main__":
    asyncio.run(main()) 