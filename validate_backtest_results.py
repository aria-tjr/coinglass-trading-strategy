#!/usr/bin/env python3
"""
Comprehensive Backtest Results Validation Runner.

This script implements industry best practices for validating crypto trading bot 
backtest results to ensure they are reliable, realistic, and ready for live trading.

Based on methodologies from leading trading bot testing companies.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from core.logger import get_logger
from src.backtesting_validation import backtest_validator, ValidationMetrics

logger = get_logger("validation_runner")


async def run_comprehensive_validation():
    """
    Run comprehensive backtest validation across multiple crypto symbols.
    
    This implements the complete validation methodology:
    1. Data Quality Assessment
    2. Basic Performance Testing
    3. Realistic Trading Conditions
    4. Walk-Forward Analysis
    5. Monte Carlo Simulation
    6. Overfitting Detection
    """
    
    logger.info("🚀 STARTING COMPREHENSIVE BACKTEST VALIDATION")
    logger.info("=" * 80)
    
    # Configuration
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD', 'MATIC-USD']
    period = "2y"  # 2 years of data for robust testing
    interval = "1h"  # Hourly data for detailed analysis
    
    logger.info(f"📊 Testing Configuration:")
    logger.info(f"   Symbols: {', '.join(symbols)}")
    logger.info(f"   Period: {period}")
    logger.info(f"   Interval: {interval}")
    logger.info(f"   Validation Framework: Industry Best Practices")
    
    try:
        # Run comprehensive validation
        portfolio_metrics = await backtest_validator.validate_backtest_comprehensive(
            symbols=symbols,
            period=period,
            interval=interval
        )
        
        # Detailed Analysis and Recommendations
        await generate_detailed_analysis(portfolio_metrics)
        
        # Final Verdict
        await generate_final_verdict(portfolio_metrics)
        
        return portfolio_metrics
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return None


async def generate_detailed_analysis(metrics: ValidationMetrics):
    """Generate detailed analysis of validation results."""
    
    logger.info("\n" + "=" * 80)
    logger.info("🔍 DETAILED VALIDATION ANALYSIS")
    logger.info("=" * 80)
    
    # Performance Analysis
    logger.info(f"📈 PERFORMANCE ANALYSIS:")
    logger.info(f"   Annual Return: {metrics.annual_return:.2f}%")
    
    if metrics.annual_return >= 20:
        logger.info(f"   ✅ EXCELLENT: Exceeds 20% target return")
    elif metrics.annual_return >= 15:
        logger.info(f"   ✅ GOOD: Strong positive returns")
    elif metrics.annual_return >= 10:
        logger.info(f"   ⚠️  MODERATE: Decent returns but below target")
    elif metrics.annual_return > 0:
        logger.info(f"   ⚠️  LOW: Positive but insufficient returns")
    else:
        logger.info(f"   ❌ POOR: Negative returns")
    
    # Risk Analysis
    logger.info(f"\n📉 RISK ANALYSIS:")
    logger.info(f"   Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
    logger.info(f"   Max Drawdown: {metrics.max_drawdown:.2f}%")
    logger.info(f"   Win Rate: {metrics.win_rate:.1f}%")
    
    if metrics.sharpe_ratio >= 1.5:
        logger.info(f"   ✅ EXCELLENT: Outstanding risk-adjusted returns")
    elif metrics.sharpe_ratio >= 1.0:
        logger.info(f"   ✅ GOOD: Strong risk-adjusted returns")
    elif metrics.sharpe_ratio >= 0.5:
        logger.info(f"   ⚠️  MODERATE: Acceptable risk-adjusted returns")
    else:
        logger.info(f"   ❌ POOR: Poor risk-adjusted returns")
    
    # Trading Activity Analysis
    logger.info(f"\n📊 TRADING ACTIVITY ANALYSIS:")
    logger.info(f"   Total Trades: {metrics.total_trades}")
    logger.info(f"   Trades per Month: {metrics.trades_per_month:.1f}")
    logger.info(f"   Profit Factor: {metrics.profit_factor:.2f}")
    
    if metrics.total_trades >= 50:
        logger.info(f"   ✅ SUFFICIENT: Adequate trade sample size")
    elif metrics.total_trades >= 30:
        logger.info(f"   ⚠️  MODERATE: Minimum acceptable sample size")
    else:
        logger.info(f"   ❌ INSUFFICIENT: Too few trades for statistical significance")
    
    # Validation Quality Analysis
    logger.info(f"\n🎯 VALIDATION QUALITY ANALYSIS:")
    logger.info(f"   Data Quality Score: {metrics.data_quality_score:.1%}")
    logger.info(f"   Realistic Trading Score: {metrics.realistic_trading_score:.1%}")
    logger.info(f"   Overfitting Risk: {metrics.overfitting_risk_score:.1%}")
    logger.info(f"   Overall Validity: {metrics.overall_validity_score:.1%}")
    
    # Real-World Impact Analysis
    logger.info(f"\n💰 REAL-WORLD IMPACT ANALYSIS:")
    logger.info(f"   Fee Impact: -{metrics.fee_impact:.2f}% (cost reduction)")
    logger.info(f"   Slippage Impact: -{metrics.slippage_impact:.2f}% (execution cost)")
    logger.info(f"   Net Expected Return: {metrics.annual_return - metrics.fee_impact - metrics.slippage_impact:.2f}%")
    
    # Comparison Analysis
    logger.info(f"\n📊 BENCHMARK COMPARISON:")
    logger.info(f"   vs Buy & Hold: {metrics.vs_buy_hold:+.2f}%")
    
    if metrics.vs_buy_hold > 5:
        logger.info(f"   ✅ OUTPERFORMS: Significantly beats buy-and-hold")
    elif metrics.vs_buy_hold > 0:
        logger.info(f"   ✅ OUTPERFORMS: Beats buy-and-hold")
    else:
        logger.info(f"   ❌ UNDERPERFORMS: Does not beat buy-and-hold")


async def generate_final_verdict(metrics: ValidationMetrics):
    """Generate final verdict on backtest validity."""
    
    logger.info("\n" + "=" * 80)
    logger.info("⚖️  FINAL VALIDATION VERDICT")
    logger.info("=" * 80)
    
    # Calculate component scores
    performance_score = min(metrics.annual_return / 20, 1.0)  # 20% target
    risk_score = min(max(metrics.sharpe_ratio / 1.5, 0), 1.0)  # 1.5 target
    validity_score = metrics.overall_validity_score
    
    # Overall assessment
    overall_score = (performance_score * 0.4 + risk_score * 0.3 + validity_score * 0.3)
    
    logger.info(f"📊 SCORE BREAKDOWN:")
    logger.info(f"   Performance Score: {performance_score:.1%} (40% weight)")
    logger.info(f"   Risk-Adjusted Score: {risk_score:.1%} (30% weight)")
    logger.info(f"   Validation Score: {validity_score:.1%} (30% weight)")
    logger.info(f"   OVERALL SCORE: {overall_score:.1%}")
    
    # Final recommendation
    if overall_score >= 0.8:
        logger.info(f"\n🎉 VERDICT: READY FOR LIVE TRADING")
        logger.info(f"   ✅ High confidence in backtest results")
        logger.info(f"   ✅ Strategy shows strong performance potential")
        logger.info(f"   ✅ Risk management appears adequate")
        logger.info(f"   ✅ Validation methodology confirms reliability")
        
        logger.info(f"\n💡 RECOMMENDED NEXT STEPS:")
        logger.info(f"   1. Start with small position sizes (1-2% of capital)")
        logger.info(f"   2. Monitor real trading vs backtest performance closely")
        logger.info(f"   3. Gradually increase position sizes if performance matches")
        logger.info(f"   4. Implement additional risk controls for live trading")
        
    elif overall_score >= 0.6:
        logger.info(f"\n⚠️  VERDICT: CAUTIOUS APPROVAL FOR TESTING")
        logger.info(f"   ⚠️  Moderate confidence in backtest results")
        logger.info(f"   ⚠️  Some concerns about strategy reliability")
        logger.info(f"   ✅ May be suitable for small-scale testing")
        
        logger.info(f"\n💡 RECOMMENDED NEXT STEPS:")
        logger.info(f"   1. Paper trade first to validate in real-time")
        logger.info(f"   2. Start with very small position sizes (<1% capital)")
        logger.info(f"   3. Address identified weaknesses before scaling")
        logger.info(f"   4. Implement strict stop-loss and monitoring")
        
    elif overall_score >= 0.4:
        logger.info(f"\n⚠️  VERDICT: SIGNIFICANT IMPROVEMENTS NEEDED")
        logger.info(f"   ⚠️  Low confidence in current backtest results")
        logger.info(f"   ❌ Strategy requires substantial improvements")
        logger.info(f"   ❌ Not recommended for live trading")
        
        logger.info(f"\n💡 RECOMMENDED NEXT STEPS:")
        logger.info(f"   1. Review and improve strategy parameters")
        logger.info(f"   2. Address data quality and overfitting issues")
        logger.info(f"   3. Re-run validation after improvements")
        logger.info(f"   4. Consider alternative strategy approaches")
        
    else:
        logger.info(f"\n❌ VERDICT: NOT READY FOR LIVE TRADING")
        logger.info(f"   ❌ Very low confidence in backtest results")
        logger.info(f"   ❌ Strategy shows poor performance or high risk")
        logger.info(f"   ❌ Validation methodology reveals serious issues")
        
        logger.info(f"\n💡 RECOMMENDED NEXT STEPS:")
        logger.info(f"   1. Completely revisit strategy design")
        logger.info(f"   2. Improve data sources and quality")
        logger.info(f"   3. Simplify strategy to reduce overfitting")
        logger.info(f"   4. Consider using proven strategy frameworks")
    
    # Specific Recommendations Based on Metrics
    logger.info(f"\n🔧 SPECIFIC IMPROVEMENT RECOMMENDATIONS:")
    
    if metrics.overfitting_risk_score > 0.7:
        logger.info(f"   🎯 HIGH PRIORITY: Reduce overfitting risk")
        logger.info(f"      - Simplify strategy parameters")
        logger.info(f"      - Use longer time periods for optimization")
        logger.info(f"      - Implement parameter stability testing")
    
    if metrics.data_quality_score < 0.7:
        logger.info(f"   📊 HIGH PRIORITY: Improve data quality")
        logger.info(f"      - Use professional data providers")
        logger.info(f"      - Check for and handle missing data")
        logger.info(f"      - Validate data consistency across timeframes")
    
    if metrics.realistic_trading_score < 0.6:
        logger.info(f"   💸 HIGH PRIORITY: Account for realistic trading costs")
        logger.info(f"      - Include higher commission rates (0.1-0.2%)")
        logger.info(f"      - Model realistic slippage (0.05-0.1%)")
        logger.info(f"      - Consider market impact and execution delays")
    
    if metrics.total_trades < 30:
        logger.info(f"   📈 MEDIUM PRIORITY: Increase trade frequency")
        logger.info(f"      - Adjust parameters for more trading opportunities")
        logger.info(f"      - Consider multiple timeframes")
        logger.info(f"      - Validate with longer historical periods")
    
    logger.info("=" * 80)


async def main():
    """Main validation runner."""
    
    print("\n🎯 CRYPTO TRADING BOT BACKTEST VALIDATION")
    print("Implementation of Industry Best Practices")
    print("Based on research from leading trading bot companies")
    print("=" * 80)
    
    # Run validation
    results = await run_comprehensive_validation()
    
    if results:
        print(f"\n✅ Validation completed successfully!")
        print(f"Overall Validity Score: {results.overall_validity_score:.1%}")
        
        # Save results
        with open("validation_results.txt", "w") as f:
            f.write(f"Backtest Validation Results\n")
            f.write(f"==========================\n")
            f.write(f"Timestamp: {asyncio.get_event_loop().time()}\n")
            f.write(f"Overall Validity Score: {results.overall_validity_score:.1%}\n")
            f.write(f"Annual Return: {results.annual_return:.2f}%\n")
            f.write(f"Sharpe Ratio: {results.sharpe_ratio:.3f}\n")
            f.write(f"Max Drawdown: {results.max_drawdown:.2f}%\n")
            f.write(f"Win Rate: {results.win_rate:.1f}%\n")
            f.write(f"Total Trades: {results.total_trades}\n")
            f.write(f"Data Quality: {results.data_quality_score:.1%}\n")
            f.write(f"Overfitting Risk: {results.overfitting_risk_score:.1%}\n")
        
        print(f"📄 Results saved to validation_results.txt")
        
    else:
        print(f"\n❌ Validation failed - check logs for details")
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main()) 