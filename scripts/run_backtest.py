#!/usr/bin/env python3
"""
Backtesting runner script for telegram_coinglass_trader.

This script provides an easy way to run backtests with different
configurations and generate comprehensive reports.
"""

import sys
import os
import argparse
from pathlib import Path
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backtesting_engine import (
    run_backtest, 
    optimize_strategy, 
    get_crypto_data,
    CoinGlassTradingStrategy
)
from core.logger import get_logger

logger = get_logger("backtest_runner")


def run_single_backtest(args):
    """Run a single backtest with specified parameters."""
    print("🚀 Starting CoinGlass Trading Strategy Backtest")
    print("=" * 60)
    print(f"Symbol: {args.symbol}")
    print(f"Period: {args.period}")
    print(f"Interval: {args.interval}")
    print(f"Initial Cash: ${args.cash:,.2f}")
    print(f"Commission: {args.commission*100:.2f}%")
    print("=" * 60)
    
    # Custom strategy parameters
    strategy_params = {}
    if args.rsi_period:
        strategy_params['rsi_period'] = args.rsi_period
    if args.rsi_oversold:
        strategy_params['rsi_oversold'] = args.rsi_oversold
    if args.rsi_overbought:
        strategy_params['rsi_overbought'] = args.rsi_overbought
    if args.ema_fast:
        strategy_params['ema_fast'] = args.ema_fast
    if args.ema_slow:
        strategy_params['ema_slow'] = args.ema_slow
    
    try:
        results, bt = run_backtest(
            symbol=args.symbol,
            period=args.period,
            interval=args.interval,
            cash=args.cash,
            commission=args.commission,
            **strategy_params
        )
        
        # Print results
        print("\n📊 BACKTEST RESULTS:")
        print("=" * 60)
        print(f"📈 Final Equity: ${results['Equity Final [$]']:,.2f}")
        print(f"📈 Total Return: {results['Return [%]']:.2f}%")
        print(f"📈 Annual Return: {results['Return (Ann.) [%]']:.2f}%")
        print(f"📈 Buy & Hold Return: {results['Buy & Hold Return [%]']:.2f}%")
        print(f"📊 Sharpe Ratio: {results['Sharpe Ratio']:.3f}")
        print(f"📊 Sortino Ratio: {results['Sortino Ratio']:.3f}")
        print(f"📉 Max Drawdown: {results['Max. Drawdown [%]']:.2f}%")
        print(f"🎯 Win Rate: {results['Win Rate [%]']:.1f}%")
        print(f"🔢 Total Trades: {results['# Trades']}")
        print(f"⏱️  Exposure Time: {results['Exposure Time [%]']:.1f}%")
        
        # Calculate some additional metrics
        if results['# Trades'] > 0:
            profit_factor = results.get('Profit Factor', 0)
            print(f"💰 Profit Factor: {profit_factor:.2f}")
            
            avg_trade = results.get('Avg. Trade [%]', 0)
            print(f"📊 Avg Trade: {avg_trade:.2f}%")
        
        print("=" * 60)
        
        # Save results if requested
        if args.save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{args.symbol.replace('/', '_')}_{timestamp}.json"
            
            results_dict = {
                'symbol': args.symbol,
                'period': args.period,
                'interval': args.interval,
                'timestamp': timestamp,
                'parameters': strategy_params,
                'results': dict(results)
            }
            
            with open(filename, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            
            print(f"💾 Results saved to: {filename}")
        
        # Show plot if requested
        if args.plot:
            print("📈 Generating interactive plot...")
            bt.plot()
        
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        print(f"❌ Backtest failed: {e}")
        return None


def run_optimization(args):
    """Run strategy optimization."""
    print("🔧 Starting Strategy Optimization")
    print("=" * 60)
    print(f"Symbol: {args.symbol}")
    print(f"Period: {args.period}")
    print(f"Optimization Target: Sharpe Ratio")
    print("=" * 60)
    
    try:
        results = optimize_strategy(
            symbol=args.symbol,
            period=args.period,
            interval=args.interval,
            cash=args.cash,
            commission=args.commission
        )
        
        print("\n🎯 OPTIMIZATION RESULTS:")
        print("=" * 60)
        print(f"Best Strategy: {results._strategy}")
        print(f"Best Sharpe Ratio: {results['Sharpe Ratio']:.3f}")
        print(f"Final Equity: ${results['Equity Final [$]']:,.2f}")
        print(f"Total Return: {results['Return [%]']:.2f}%")
        print(f"Max Drawdown: {results['Max. Drawdown [%]']:.2f}%")
        print(f"Win Rate: {results['Win Rate [%]']:.1f}%")
        print("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        print(f"❌ Optimization failed: {e}")
        return None


def run_multiple_symbols(args):
    """Run backtests on multiple symbols."""
    symbols = args.symbols.split(',')
    
    print(f"🔄 Running backtests on {len(symbols)} symbols")
    print("=" * 60)
    
    all_results = {}
    
    for symbol in symbols:
        symbol = symbol.strip()
        print(f"\n📊 Testing {symbol}...")
        
        try:
            results, _ = run_backtest(
                symbol=symbol,
                period=args.period,
                interval=args.interval,
                cash=args.cash,
                commission=args.commission
            )
            
            all_results[symbol] = {
                'return': results['Return [%]'],
                'sharpe': results['Sharpe Ratio'],
                'drawdown': results['Max. Drawdown [%]'],
                'win_rate': results['Win Rate [%]'],
                'trades': results['# Trades']
            }
            
            print(f"✅ {symbol}: {results['Return [%]']:.1f}% return, {results['Sharpe Ratio']:.2f} Sharpe")
            
        except Exception as e:
            print(f"❌ {symbol}: Failed - {e}")
            all_results[symbol] = None
    
    # Summary
    print("\n📋 SUMMARY REPORT:")
    print("=" * 80)
    print(f"{'Symbol':<12} {'Return %':<10} {'Sharpe':<8} {'Drawdown %':<12} {'Win Rate %':<12} {'Trades':<8}")
    print("-" * 80)
    
    for symbol, data in all_results.items():
        if data:
            print(f"{symbol:<12} {data['return']:<10.1f} {data['sharpe']:<8.2f} "
                  f"{data['drawdown']:<12.1f} {data['win_rate']:<12.1f} {data['trades']:<8}")
        else:
            print(f"{symbol:<12} {'FAILED':<10} {'-':<8} {'-':<12} {'-':<12} {'-':<8}")
    
    print("=" * 80)
    
    return all_results


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Run backtests for telegram_coinglass_trader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic backtest
  python run_backtest.py --symbol BTC-USD --period 6mo
  
  # With custom parameters
  python run_backtest.py --symbol ETH-USD --rsi-period 21 --ema-fast 10 --ema-slow 30
  
  # Optimization
  python run_backtest.py --optimize --symbol BTC-USD --period 3mo
  
  # Multiple symbols
  python run_backtest.py --symbols "BTC-USD,ETH-USD,SOL-USD" --period 6mo
  
  # Save results and show plot
  python run_backtest.py --symbol BTC-USD --save-results --plot
        """
    )
    
    # Main options
    parser.add_argument('--symbol', default='BTC-USD', 
                       help='Trading symbol (default: BTC-USD)')
    parser.add_argument('--symbols', 
                       help='Multiple symbols separated by commas (e.g., BTC-USD,ETH-USD)')
    parser.add_argument('--period', default='6mo',
                       choices=['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'],
                       help='Data period (default: 6mo)')
    parser.add_argument('--interval', default='1h',
                       choices=['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
                       help='Data interval (default: 1h)')
    parser.add_argument('--cash', type=float, default=10000,
                       help='Initial cash (default: 10000)')
    parser.add_argument('--commission', type=float, default=0.002,
                       help='Trading commission (default: 0.002)')
    
    # Strategy parameters
    parser.add_argument('--rsi-period', type=int, help='RSI period')
    parser.add_argument('--rsi-oversold', type=int, help='RSI oversold level')
    parser.add_argument('--rsi-overbought', type=int, help='RSI overbought level')
    parser.add_argument('--ema-fast', type=int, help='Fast EMA period')
    parser.add_argument('--ema-slow', type=int, help='Slow EMA period')
    
    # Actions
    parser.add_argument('--optimize', action='store_true',
                       help='Run parameter optimization')
    parser.add_argument('--plot', action='store_true',
                       help='Show interactive plot')
    parser.add_argument('--save-results', action='store_true',
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.symbols and args.optimize:
        print("❌ Cannot run optimization with multiple symbols")
        return 1
    
    if args.ema_fast and args.ema_slow and args.ema_fast >= args.ema_slow:
        print("❌ Fast EMA period must be less than slow EMA period")
        return 1
    
    # Run the appropriate function
    try:
        if args.optimize:
            run_optimization(args)
        elif args.symbols:
            run_multiple_symbols(args)
        else:
            run_single_backtest(args)
        
        print("\n✅ Backtest completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Backtest interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Unexpected error in backtest runner: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 