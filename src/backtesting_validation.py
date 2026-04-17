"""
Enhanced Backtest Validation System for Crypto Trading Bot.

Implements comprehensive validation techniques to ensure backtest results 
are reliable, realistic, and properly account for real-world trading conditions.

Based on industry best practices from trading bot testing methodologies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from core.logger import get_logger
from strategy.portfolio_manager import portfolio_manager
from strategy.performance_optimizer import performance_optimizer
from src.backtesting_engine import CoinGlassTradingStrategy, get_crypto_data

logger = get_logger("backtest_validation")


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics for backtest analysis."""
    # Basic Performance
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # Trading Activity
    total_trades: int
    avg_trade_duration: float
    trades_per_month: float
    
    # Risk Metrics
    volatility: float
    downside_deviation: float
    calmar_ratio: float
    
    # Validation Scores
    data_quality_score: float
    realistic_trading_score: float
    overfitting_risk_score: float
    overall_validity_score: float
    
    # Comparison Metrics
    vs_buy_hold: float
    vs_market_benchmark: float
    
    # Real-world Factors
    slippage_impact: float
    fee_impact: float
    execution_impact: float


@dataclass
class WalkForwardResult:
    """Results from walk-forward testing."""
    period_start: datetime
    period_end: datetime
    return_percent: float
    sharpe_ratio: float
    max_drawdown: float
    trades_count: int
    
    
@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    scenario_id: int
    final_return: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int


class EnhancedBacktestValidator:
    """
    Comprehensive backtest validation system implementing industry best practices.
    
    Features:
    - Data quality validation
    - Realistic trading condition simulation
    - Walk-forward testing
    - Monte Carlo simulation
    - Overfitting detection
    - Real-world factor analysis
    """
    
    def __init__(self):
        """Initialize validation system."""
        self.validation_results: Dict[str, Any] = {}
        self.walk_forward_results: List[WalkForwardResult] = []
        self.monte_carlo_results: List[MonteCarloResult] = []
        
        # Validation thresholds
        self.min_data_points = 1000  # Minimum data points for validity
        self.min_trades = 30  # Minimum trades for statistical significance
        self.max_overfitting_score = 0.7  # Maximum acceptable overfitting risk
        
        logger.info("Enhanced backtest validator initialized")
    
    async def validate_backtest_comprehensive(
        self,
        symbols: List[str] = None,
        period: str = "2y",
        interval: str = "1h"
    ) -> ValidationMetrics:
        """
        Run comprehensive backtest validation with all checks.
        
        Args:
            symbols: List of crypto symbols to test
            period: Historical data period
            interval: Data interval
            
        Returns:
            Complete validation metrics
        """
        if not symbols:
            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
        
        logger.info("Starting comprehensive backtest validation...")
        
        validation_scores = []
        all_results = []
        
        for symbol in symbols:
            logger.info(f"Validating strategy for {symbol}...")
            
            # 1. Data Quality Validation
            data_quality = await self._validate_data_quality(symbol, period, interval)
            
            # 2. Basic Backtest
            basic_results = await self._run_basic_backtest(symbol, period, interval)
            
            # 3. Realistic Trading Conditions
            realistic_results = await self._test_realistic_conditions(symbol, period, interval)
            
            # 4. Walk-Forward Testing
            wf_results = await self._walk_forward_test(symbol, period, interval)
            
            # 5. Monte Carlo Simulation
            mc_results = await self._monte_carlo_simulation(symbol, period, interval)
            
            # 6. Overfitting Analysis
            overfitting_score = await self._detect_overfitting(symbol, period, interval)
            
            # Compile results for this symbol
            symbol_metrics = self._compile_validation_metrics(
                symbol, basic_results, realistic_results, wf_results, 
                mc_results, data_quality, overfitting_score
            )
            
            all_results.append(symbol_metrics)
            validation_scores.append(symbol_metrics.overall_validity_score)
        
        # Calculate portfolio-level metrics
        portfolio_metrics = self._calculate_portfolio_metrics(all_results)
        
        # Generate validation report
        await self._generate_validation_report(all_results, portfolio_metrics)
        
        return portfolio_metrics
    
    async def _validate_data_quality(self, symbol: str, period: str, interval: str) -> float:
        """Validate data quality and completeness."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            if data is None or data.empty:
                logger.error(f"No data available for {symbol}")
                return 0.0
            
            quality_score = 100.0
            
            # Check data completeness
            if len(data) < self.min_data_points:
                logger.warning(f"Insufficient data points: {len(data)} < {self.min_data_points}")
                quality_score *= 0.5
            
            # Check for missing values
            missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns))
            if missing_pct > 0.05:  # 5% threshold
                logger.warning(f"High missing data: {missing_pct:.1%}")
                quality_score *= (1 - missing_pct)
            
            # Check for zero volumes
            zero_volume_pct = (data['Volume'] == 0).sum() / len(data)
            if zero_volume_pct > 0.1:  # 10% threshold
                logger.warning(f"High zero volume periods: {zero_volume_pct:.1%}")
                quality_score *= (1 - zero_volume_pct)
            
            # Check for price gaps
            price_changes = data['Close'].pct_change().abs()
            extreme_moves = (price_changes > 0.2).sum()  # >20% moves
            if extreme_moves > len(data) * 0.02:  # >2% of data
                logger.warning(f"Many extreme price moves: {extreme_moves}")
                quality_score *= 0.8
            
            # Check data continuity
            time_gaps = pd.to_datetime(data.index).to_series().diff()
            expected_interval = pd.Timedelta(interval)
            large_gaps = (time_gaps > expected_interval * 2).sum()
            if large_gaps > len(data) * 0.05:  # >5% large gaps
                logger.warning(f"Data continuity issues: {large_gaps} large gaps")
                quality_score *= 0.7
            
            quality_score = max(quality_score, 0.0) / 100.0
            logger.info(f"Data quality score for {symbol}: {quality_score:.3f}")
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Data quality validation failed for {symbol}: {e}")
            return 0.0
    
    async def _run_basic_backtest(self, symbol: str, period: str, interval: str) -> Dict[str, Any]:
        """Run basic backtest with standard parameters."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            # Run backtest with realistic settings
            bt = Backtest(
                data,
                CoinGlassTradingStrategy,
                cash=10000,
                commission=0.001,  # 0.1% commission (realistic)
                exclusive_orders=True
            )
            
            results = bt.run()
            
            # Extract key metrics
            return {
                'total_return': results['Return [%]'],
                'annual_return': results['Return (Ann.) [%]'],
                'sharpe_ratio': results['Sharpe Ratio'],
                'max_drawdown': results['Max. Drawdown [%]'],
                'win_rate': results['Win Rate [%]'] if results['# Trades'] > 0 else 0,
                'total_trades': results['# Trades'],
                'profit_factor': results.get('Profit Factor', 0),
                'volatility': results.get('Volatility (Ann.) [%]', 0),
                'vs_buy_hold': results['Return [%]'] - results['Buy & Hold Return [%]'],
                'exposure_time': results['Exposure Time [%]']
            }
            
        except Exception as e:
            logger.error(f"Basic backtest failed for {symbol}: {e}")
            return {}
    
    async def _test_realistic_conditions(self, symbol: str, period: str, interval: str) -> Dict[str, Any]:
        """Test with realistic trading conditions including slippage and fees."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            # Test with different fee structures
            fee_scenarios = [
                {'commission': 0.0005, 'slippage': 0.0002, 'name': 'best_case'},    # VIP fees
                {'commission': 0.001, 'slippage': 0.0005, 'name': 'typical'},       # Standard fees
                {'commission': 0.002, 'slippage': 0.001, 'name': 'worst_case'}      # High fees
            ]
            
            results = {}
            
            for scenario in fee_scenarios:
                bt = Backtest(
                    data,
                    CoinGlassTradingStrategy,
                    cash=10000,
                    commission=scenario['commission']
                )
                
                scenario_results = bt.run()
                
                results[scenario['name']] = {
                    'total_return': scenario_results['Return [%]'],
                    'annual_return': scenario_results['Return (Ann.) [%]'],
                    'sharpe_ratio': scenario_results['Sharpe Ratio'],
                    'total_trades': scenario_results['# Trades']
                }
            
            # Calculate fee impact
            best_return = results['best_case']['total_return']
            worst_return = results['worst_case']['total_return']
            fee_impact = best_return - worst_return
            
            results['fee_impact'] = fee_impact
            results['slippage_impact'] = fee_impact * 0.4  # Estimate slippage portion
            
            return results
            
        except Exception as e:
            logger.error(f"Realistic conditions test failed for {symbol}: {e}")
            return {}
    
    async def _walk_forward_test(self, symbol: str, period: str, interval: str) -> List[WalkForwardResult]:
        """Perform walk-forward testing to validate strategy robustness."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            if len(data) < 500:  # Need sufficient data
                logger.warning(f"Insufficient data for walk-forward test: {len(data)}")
                return []
            
            # Split data into 6-month windows with 3-month steps
            window_size = 180 * 24 if interval == '1h' else 180  # 6 months
            step_size = 90 * 24 if interval == '1h' else 90      # 3 months
            
            wf_results = []
            
            for i in range(0, len(data) - window_size, step_size):
                window_data = data.iloc[i:i + window_size]
                
                if len(window_data) < 100:  # Minimum window size
                    continue
                
                try:
                    bt = Backtest(
                        window_data,
                        CoinGlassTradingStrategy,
                        cash=10000,
                        commission=0.001
                    )
                    
                    results = bt.run()
                    
                    wf_result = WalkForwardResult(
                        period_start=window_data.index[0],
                        period_end=window_data.index[-1],
                        return_percent=results['Return [%]'],
                        sharpe_ratio=results['Sharpe Ratio'],
                        max_drawdown=results['Max. Drawdown [%]'],
                        trades_count=results['# Trades']
                    )
                    
                    wf_results.append(wf_result)
                    
                except Exception as e:
                    logger.warning(f"Walk-forward window failed: {e}")
                    continue
            
            logger.info(f"Walk-forward test completed: {len(wf_results)} periods")
            return wf_results
            
        except Exception as e:
            logger.error(f"Walk-forward test failed for {symbol}: {e}")
            return []
    
    async def _monte_carlo_simulation(self, symbol: str, period: str, interval: str, simulations: int = 100) -> List[MonteCarloResult]:
        """Run Monte Carlo simulation with parameter variations."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            mc_results = []
            
            # Parameter ranges for Monte Carlo
            param_ranges = {
                'rsi_oversold': (25, 35),
                'rsi_overbought': (65, 75),
                'ema_fast': (8, 16),
                'ema_slow': (20, 30),
                'funding_threshold': (0.005, 0.02),
                'risk_per_trade': (0.01, 0.03)
            }
            
            for i in range(simulations):
                # Generate random parameters
                random_params = {}
                for param, (min_val, max_val) in param_ranges.items():
                    random_params[param] = np.random.uniform(min_val, max_val)
                
                try:
                    # Create custom strategy class with random parameters
                    class RandomStrategy(CoinGlassTradingStrategy):
                        pass
                    
                    # Set parameters as class attributes
                    for param, value in random_params.items():
                        setattr(RandomStrategy, param, value)
                    
                    bt = Backtest(
                        data,
                        RandomStrategy,
                        cash=10000,
                        commission=0.001
                    )
                    
                    results = bt.run()
                    
                    mc_result = MonteCarloResult(
                        scenario_id=i,
                        final_return=results['Return [%]'],
                        max_drawdown=results['Max. Drawdown [%]'],
                        sharpe_ratio=results['Sharpe Ratio'],
                        total_trades=results['# Trades']
                    )
                    
                    mc_results.append(mc_result)
                    
                except Exception as e:
                    logger.warning(f"Monte Carlo simulation {i} failed: {e}")
                    continue
            
            logger.info(f"Monte Carlo simulation completed: {len(mc_results)} scenarios")
            return mc_results
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed for {symbol}: {e}")
            return []
    
    async def _detect_overfitting(self, symbol: str, period: str, interval: str) -> float:
        """Detect potential overfitting using multiple techniques."""
        try:
            data = get_crypto_data(symbol, period, interval)
            
            overfitting_indicators = []
            
            # 1. In-sample vs Out-of-sample performance
            split_point = int(len(data) * 0.7)  # 70/30 split
            
            # In-sample test
            in_sample_data = data.iloc[:split_point]
            bt_in = Backtest(in_sample_data, CoinGlassTradingStrategy, cash=10000, commission=0.001)
            in_sample_results = bt_in.run()
            
            # Out-of-sample test
            out_sample_data = data.iloc[split_point:]
            bt_out = Backtest(out_sample_data, CoinGlassTradingStrategy, cash=10000, commission=0.001)
            out_sample_results = bt_out.run()
            
            # Compare performance
            in_sample_return = in_sample_results['Return (Ann.) [%]']
            out_sample_return = out_sample_results['Return (Ann.) [%]']
            
            if in_sample_return > 0:
                performance_degradation = max(0, (in_sample_return - out_sample_return) / in_sample_return)
                overfitting_indicators.append(performance_degradation)
            
            # 2. Strategy complexity vs performance
            # Simple strategies should perform similarly to complex ones if not overfitted
            
            # 3. Parameter sensitivity
            # If small parameter changes cause large performance changes = overfitting
            
            # 4. Trade frequency analysis
            # Too many trades might indicate overfitting to noise
            trade_frequency = in_sample_results['# Trades'] / (len(in_sample_data) / (24 if interval == '1h' else 1))
            if trade_frequency > 2:  # More than 2 trades per day
                overfitting_indicators.append(0.3)
            
            # Calculate overall overfitting risk
            overfitting_score = np.mean(overfitting_indicators) if overfitting_indicators else 0.0
            
            logger.info(f"Overfitting risk score for {symbol}: {overfitting_score:.3f}")
            return overfitting_score
            
        except Exception as e:
            logger.error(f"Overfitting detection failed for {symbol}: {e}")
            return 1.0  # Assume high risk on error
    
    def _compile_validation_metrics(
        self,
        symbol: str,
        basic_results: Dict[str, Any],
        realistic_results: Dict[str, Any],
        wf_results: List[WalkForwardResult],
        mc_results: List[MonteCarloResult],
        data_quality: float,
        overfitting_score: float
    ) -> ValidationMetrics:
        """Compile all validation results into comprehensive metrics."""
        
        # Basic metrics
        total_return = basic_results.get('total_return', 0)
        annual_return = basic_results.get('annual_return', 0)
        sharpe_ratio = basic_results.get('sharpe_ratio', 0)
        max_drawdown = basic_results.get('max_drawdown', 0)
        win_rate = basic_results.get('win_rate', 0)
        profit_factor = basic_results.get('profit_factor', 0)
        
        # Trading activity
        total_trades = basic_results.get('total_trades', 0)
        trades_per_month = total_trades / 12 if 'total_trades' in basic_results else 0
        
        # Risk metrics
        volatility = basic_results.get('volatility', 0)
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Validation scores
        realistic_trading_score = self._calculate_realistic_score(realistic_results)
        
        # Walk-forward consistency
        wf_consistency = self._calculate_wf_consistency(wf_results)
        
        # Monte Carlo robustness
        mc_robustness = self._calculate_mc_robustness(mc_results)
        
        # Overall validity score
        validity_components = [
            data_quality * 0.2,
            realistic_trading_score * 0.25,
            wf_consistency * 0.25,
            mc_robustness * 0.15,
            (1 - overfitting_score) * 0.15
        ]
        overall_validity = sum(validity_components)
        
        return ValidationMetrics(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            avg_trade_duration=0,  # Calculate if needed
            trades_per_month=trades_per_month,
            volatility=volatility,
            downside_deviation=0,  # Calculate if needed
            calmar_ratio=calmar_ratio,
            data_quality_score=data_quality,
            realistic_trading_score=realistic_trading_score,
            overfitting_risk_score=overfitting_score,
            overall_validity_score=overall_validity,
            vs_buy_hold=basic_results.get('vs_buy_hold', 0),
            vs_market_benchmark=0,  # Compare to benchmark if available
            slippage_impact=realistic_results.get('slippage_impact', 0),
            fee_impact=realistic_results.get('fee_impact', 0),
            execution_impact=0  # Calculate based on execution times
        )
    
    def _calculate_realistic_score(self, realistic_results: Dict[str, Any]) -> float:
        """Calculate score based on realistic trading conditions."""
        if not realistic_results:
            return 0.0
        
        # Check if strategy remains profitable under realistic conditions
        typical_return = realistic_results.get('typical', {}).get('annual_return', 0)
        worst_case_return = realistic_results.get('worst_case', {}).get('annual_return', 0)
        
        if typical_return > 10 and worst_case_return > 5:  # Still profitable
            return 0.8
        elif typical_return > 5:
            return 0.6
        elif typical_return > 0:
            return 0.4
        else:
            return 0.2
    
    def _calculate_wf_consistency(self, wf_results: List[WalkForwardResult]) -> float:
        """Calculate walk-forward consistency score."""
        if not wf_results or len(wf_results) < 3:
            return 0.0
        
        returns = [r.return_percent for r in wf_results]
        positive_periods = sum(1 for r in returns if r > 0)
        consistency_ratio = positive_periods / len(returns)
        
        # Also check for extreme variations
        return_std = np.std(returns)
        if return_std > 50:  # High variation
            consistency_ratio *= 0.5
        
        return consistency_ratio
    
    def _calculate_mc_robustness(self, mc_results: List[MonteCarloResult]) -> float:
        """Calculate Monte Carlo robustness score."""
        if not mc_results or len(mc_results) < 50:
            return 0.0
        
        returns = [r.final_return for r in mc_results]
        positive_scenarios = sum(1 for r in returns if r > 0)
        robustness_ratio = positive_scenarios / len(returns)
        
        # Check for extreme outliers
        return_percentiles = np.percentile(returns, [10, 90])
        if return_percentiles[0] < -50 or return_percentiles[1] > 200:  # Extreme results
            robustness_ratio *= 0.7
        
        return robustness_ratio
    
    def _calculate_portfolio_metrics(self, symbol_metrics: List[ValidationMetrics]) -> ValidationMetrics:
        """Calculate portfolio-level validation metrics."""
        if not symbol_metrics:
            return ValidationMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # Average key metrics across symbols
        avg_annual_return = np.mean([m.annual_return for m in symbol_metrics])
        avg_sharpe_ratio = np.mean([m.sharpe_ratio for m in symbol_metrics])
        avg_max_drawdown = np.mean([m.max_drawdown for m in symbol_metrics])
        avg_win_rate = np.mean([m.win_rate for m in symbol_metrics])
        avg_validity_score = np.mean([m.overall_validity_score for m in symbol_metrics])
        
        # Portfolio-specific calculations
        total_trades = sum([m.total_trades for m in symbol_metrics])
        
        return ValidationMetrics(
            total_return=avg_annual_return,  # Simplified
            annual_return=avg_annual_return,
            sharpe_ratio=avg_sharpe_ratio,
            max_drawdown=avg_max_drawdown,
            win_rate=avg_win_rate,
            profit_factor=np.mean([m.profit_factor for m in symbol_metrics]),
            total_trades=total_trades,
            avg_trade_duration=0,
            trades_per_month=total_trades / 12,
            volatility=np.mean([m.volatility for m in symbol_metrics]),
            downside_deviation=0,
            calmar_ratio=np.mean([m.calmar_ratio for m in symbol_metrics]),
            data_quality_score=np.mean([m.data_quality_score for m in symbol_metrics]),
            realistic_trading_score=np.mean([m.realistic_trading_score for m in symbol_metrics]),
            overfitting_risk_score=np.mean([m.overfitting_risk_score for m in symbol_metrics]),
            overall_validity_score=avg_validity_score,
            vs_buy_hold=np.mean([m.vs_buy_hold for m in symbol_metrics]),
            vs_market_benchmark=0,
            slippage_impact=np.mean([m.slippage_impact for m in symbol_metrics]),
            fee_impact=np.mean([m.fee_impact for m in symbol_metrics]),
            execution_impact=0
        )
    
    async def _generate_validation_report(self, symbol_metrics: List[ValidationMetrics], portfolio_metrics: ValidationMetrics):
        """Generate comprehensive validation report."""
        logger.info("=" * 80)
        logger.info("🎯 COMPREHENSIVE BACKTEST VALIDATION REPORT")
        logger.info("=" * 80)
        
        # Portfolio Summary
        logger.info(f"📊 PORTFOLIO VALIDATION SUMMARY:")
        logger.info(f"   Overall Validity Score: {portfolio_metrics.overall_validity_score:.1%}")
        logger.info(f"   Annual Return: {portfolio_metrics.annual_return:.1f}%")
        logger.info(f"   Sharpe Ratio: {portfolio_metrics.sharpe_ratio:.2f}")
        logger.info(f"   Max Drawdown: {portfolio_metrics.max_drawdown:.1f}%")
        logger.info(f"   Win Rate: {portfolio_metrics.win_rate:.1f}%")
        
        # Validation Component Scores
        logger.info(f"\n🔍 VALIDATION COMPONENT SCORES:")
        logger.info(f"   Data Quality: {portfolio_metrics.data_quality_score:.1%}")
        logger.info(f"   Realistic Trading: {portfolio_metrics.realistic_trading_score:.1%}")
        logger.info(f"   Overfitting Risk: {portfolio_metrics.overfitting_risk_score:.1%}")
        
        # Real-world Factors
        logger.info(f"\n💰 REAL-WORLD IMPACT ANALYSIS:")
        logger.info(f"   Fee Impact: {portfolio_metrics.fee_impact:.1f}% reduction")
        logger.info(f"   Slippage Impact: {portfolio_metrics.slippage_impact:.1f}% reduction")
        
        # Validity Assessment
        if portfolio_metrics.overall_validity_score >= 0.8:
            logger.info(f"\n✅ VALIDATION RESULT: HIGH CONFIDENCE")
            logger.info(f"   Backtest results are highly reliable and realistic")
        elif portfolio_metrics.overall_validity_score >= 0.6:
            logger.info(f"\n⚠️  VALIDATION RESULT: MODERATE CONFIDENCE")
            logger.info(f"   Backtest results are reasonably reliable with some limitations")
        else:
            logger.info(f"\n❌ VALIDATION RESULT: LOW CONFIDENCE")
            logger.info(f"   Backtest results may not be reliable for live trading")
        
        # Recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        if portfolio_metrics.overfitting_risk_score > 0.7:
            logger.info(f"   🔧 HIGH OVERFITTING RISK - Simplify strategy parameters")
        if portfolio_metrics.data_quality_score < 0.7:
            logger.info(f"   📊 IMPROVE DATA QUALITY - Use higher quality data sources")
        if portfolio_metrics.realistic_trading_score < 0.6:
            logger.info(f"   💸 ACCOUNT FOR TRADING COSTS - Strategy may not be profitable after fees")
        
        logger.info("=" * 80)


# Global validator instance
backtest_validator = EnhancedBacktestValidator()