#!/usr/bin/env python3
"""
Quick test script to verify the backtest validation system is working correctly.

This performs basic checks on the validation components before running
the full comprehensive validation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from core.logger import get_logger
from src.backtesting_engine import get_crypto_data, CoinGlassTradingStrategy
from backtesting import Backtest

logger = get_logger("validation_test")


async def test_data_availability():
    """Test if we can fetch crypto data successfully."""
    logger.info("🔍 Testing data availability...")
    
    try:
        # Test data fetch for BTC
        data = get_crypto_data("BTC-USD", "6mo", "1h")
        
        if data is not None and not data.empty:
            logger.info(f"✅ Data fetch successful: {len(data)} records for BTC-USD")
            logger.info(f"   Date range: {data.index[0]} to {data.index[-1]}")
            return True
        else:
            logger.error("❌ Data fetch failed - no data returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Data fetch failed: {e}")
        return False


async def test_basic_backtest():
    """Test if basic backtesting works."""
    logger.info("🔍 Testing basic backtest functionality...")
    
    try:
        # Get sample data
        data = get_crypto_data("BTC-USD", "3mo", "1h")
        
        if data is None or data.empty:
            logger.error("❌ Cannot test backtest - no data available")
            return False
        
        # Run basic backtest
        bt = Backtest(
            data,
            CoinGlassTradingStrategy,
            cash=10000,
            commission=0.001
        )
        
        results = bt.run()
        
        if results is not None:
            logger.info(f"✅ Basic backtest successful")
            logger.info(f"   Total Return: {results['Return [%]']:.2f}%")
            logger.info(f"   Total Trades: {results['# Trades']}")
            logger.info(f"   Sharpe Ratio: {results['Sharpe Ratio']:.3f}")
            return True
        else:
            logger.error("❌ Backtest failed - no results returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}")
        return False


async def test_validation_imports():
    """Test if validation system imports work."""
    logger.info("🔍 Testing validation system imports...")
    
    try:
        from src.backtesting_validation import backtest_validator, ValidationMetrics
        logger.info("✅ Validation system imports successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation imports failed: {e}")
        return False


async def test_quick_validation():
    """Test a quick validation run with minimal data."""
    logger.info("🔍 Testing quick validation with limited data...")
    
    try:
        from src.backtesting_validation import backtest_validator
        
        # Test with just one symbol and short period
        metrics = await backtest_validator.validate_backtest_comprehensive(
            symbols=['BTC-USD'],
            period="3mo",
            interval="1h"
        )
        
        if metrics is not None:
            logger.info(f"✅ Quick validation successful")
            logger.info(f"   Validity Score: {metrics.overall_validity_score:.1%}")
            logger.info(f"   Annual Return: {metrics.annual_return:.2f}%")
            return True
        else:
            logger.error("❌ Quick validation failed - no metrics returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Quick validation failed: {e}")
        return False


async def main():
    """Main test runner."""
    print("\n🧪 BACKTEST VALIDATION SYSTEM TEST")
    print("=" * 50)
    
    tests = [
        ("Data Availability", test_data_availability),
        ("Basic Backtest", test_basic_backtest),
        ("Validation Imports", test_validation_imports),
        ("Quick Validation", test_quick_validation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name} test...")
        
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 TEST RESULTS:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {passed/total:.1%}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED - Validation system is ready!")
        print(f"   You can now run: python validate_backtest_results.py")
        return 0
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Please fix issues before proceeding")
        return 1


if __name__ == "__main__":
    asyncio.run(main()) 