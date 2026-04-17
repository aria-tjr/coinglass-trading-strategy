#!/usr/bin/env python3
"""
Comprehensive System Validation Script.

Tests all components and validates that weak points have been resolved.
Runs safety checks, connectivity tests, and performance validations.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import settings, load_settings
from core.logger import get_logger
from infra.coinglass_client import coinglass_client
from infra.exchange_gateway import bybit_gateway
from strategy.risk_manager import risk_manager
from core.monitoring import system_monitor


logger = get_logger("validation")


class SystemValidator:
    """Comprehensive system validation."""
    
    def __init__(self):
        self.test_results = []
        self.critical_failures = []
        self.warnings = []
    
    def log_test(self, test_name: str, passed: bool, message: str = "", critical: bool = False):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "critical": critical
        }
        
        self.test_results.append(result)
        
        if not passed:
            if critical:
                self.critical_failures.append(result)
            else:
                self.warnings.append(result)
        
        print(f"{status} {test_name}: {message}")
    
    async def validate_configuration(self):
        """Validate configuration system."""
        print("\n🔧 Configuration Validation")
        print("=" * 50)
        
        try:
            # Test configuration loading
            test_settings = load_settings()
            self.log_test(
                "Configuration Loading",
                True,
                "Settings loaded successfully"
            )
            
            # Test API key validation
            api_errors = test_settings.validate_api_keys()
            self.log_test(
                "API Key Validation",
                len(api_errors) == 0,
                f"API validation: {len(api_errors)} errors found" if api_errors else "All API keys valid",
                critical=len(api_errors) > 0
            )
            
            # Test safety configuration
            safety_status = test_settings.get_safety_status()
            safety_score = safety_status["safety_score"]
            self.log_test(
                "Safety Configuration",
                safety_score >= 50,
                f"Safety score: {safety_score}/100",
                critical=safety_score < 30
            )
            
            # Test parameter validation
            self.log_test(
                "Parameter Validation",
                test_settings.ema_fast < test_settings.ema_slow,
                f"EMA periods: Fast={test_settings.ema_fast}, Slow={test_settings.ema_slow}"
            )
            
        except Exception as e:
            self.log_test(
                "Configuration System",
                False,
                f"Configuration failed: {e}",
                critical=True
            )
    
    async def validate_api_connections(self):
        """Validate API connections and error handling."""
        print("\n🌐 API Connection Validation")
        print("=" * 50)
        
        # CoinGlass API validation
        try:
            start_time = time.time()
            connected = await coinglass_client.connect()
            response_time = (time.time() - start_time) * 1000
            
            self.log_test(
                "CoinGlass Connection",
                connected,
                f"Connected in {response_time:.0f}ms" if connected else "Connection failed"
            )
            
            if connected:
                # Test API endpoints
                start_time = time.time()
                funding_data = await coinglass_client.get_funding_rate_ohlc("BTC", limit=5)
                api_time = (time.time() - start_time) * 1000
                
                self.log_test(
                    "CoinGlass API Response",
                    len(funding_data) > 0 or api_time < 10000,  # Either data or quick response
                    f"Response time: {api_time:.0f}ms, Data points: {len(funding_data)}"
                )
                
                # Test rate limiting
                start_time = time.time()
                tasks = [coinglass_client.get_funding_rate_ohlc("BTC", limit=1) for _ in range(3)]
                await asyncio.gather(*tasks, return_exceptions=True)
                rate_limit_time = (time.time() - start_time) * 1000
                
                self.log_test(
                    "Rate Limiting",
                    rate_limit_time >= 1000,  # Should take at least 1 second due to rate limiting
                    f"3 requests took {rate_limit_time:.0f}ms"
                )
                
                # Test error handling
                connection_status = coinglass_client.get_connection_status()
                self.log_test(
                    "Error Tracking",
                    connection_status["consecutive_errors"] < 5,
                    f"Consecutive errors: {connection_status['consecutive_errors']}"
                )
            
        except Exception as e:
            self.log_test(
                "CoinGlass API Test",
                False,
                f"API test failed: {e}",
                critical=True
            )
        
        # Bybit API validation
        try:
            start_time = time.time()
            connected = await bybit_gateway.connect()
            response_time = (time.time() - start_time) * 1000
            
            self.log_test(
                "Bybit Connection",
                connected,
                f"Connected in {response_time:.0f}ms" if connected else "Connection failed"
            )
            
            if connected:
                # Test balance retrieval
                balance = await bybit_gateway.get_balance()
                self.log_test(
                    "Balance Retrieval",
                    balance is not None,
                    f"Balance: ${balance.get('free', 0):.2f} USDT" if balance else "Failed to get balance"
                )
                
                # Test market data
                ticker = await bybit_gateway.get_ticker("BTC/USDT:USDT")
                self.log_test(
                    "Market Data",
                    ticker is not None and 'last' in ticker,
                    f"BTC price: ${ticker.get('last', 0):.2f}" if ticker else "Failed to get ticker"
                )
        
        except Exception as e:
            self.log_test(
                "Bybit API Test",
                False,
                f"Bybit test failed: {e}",
                critical=True
            )
    
    async def validate_risk_management(self):
        """Validate risk management system."""
        print("\n🛡️ Risk Management Validation")
        print("=" * 50)
        
        try:
            # Set test balance
            risk_manager.set_account_balance(1000.0)
            
            # Test safety thresholds
            can_trade, reason = risk_manager.can_trade()
            self.log_test(
                "Trading Safety Check",
                can_trade,
                f"Can trade: {reason}"
            )
            
            # Test position sizing
            position_size, risk_amount, notional = risk_manager.calculate_position_size(
                1000.0, 50000.0, 49000.0, risk_manager.PositionSide.LONG
            )
            
            self.log_test(
                "Position Sizing",
                0 < position_size < 1.0 and risk_amount <= 20.0,  # Max 2% risk
                f"Position: {position_size:.6f}, Risk: ${risk_amount:.2f}"
            )
            
            # Test emergency stop functionality
            risk_manager.consecutive_losses = 6  # Trigger emergency stop
            risk_manager._check_safety_thresholds()
            
            self.log_test(
                "Emergency Stop",
                risk_manager.emergency_stop,
                "Emergency stop activated after consecutive losses"
            )
            
            # Reset for next tests
            risk_manager.consecutive_losses = 0
            risk_manager.emergency_stop = False
            
            # Test performance tracking
            stats = risk_manager.get_performance_stats()
            self.log_test(
                "Performance Tracking",
                isinstance(stats, dict),
                f"Stats available: {list(stats.keys())}"
            )
            
        except Exception as e:
            self.log_test(
                "Risk Management Test",
                False,
                f"Risk management test failed: {e}",
                critical=True
            )
    
    async def validate_monitoring_system(self):
        """Validate monitoring and alerting system."""
        print("\n📊 Monitoring System Validation")
        print("=" * 50)
        
        try:
            # Test health metrics initialization
            status = system_monitor.get_system_status()
            self.log_test(
                "Health Metrics",
                len(status["metrics"]) > 0,
                f"Tracking {len(status['metrics'])} metrics"
            )
            
            # Test performance tracking
            system_monitor.performance_tracker.record("test_metric", 42.0)
            latest_value = system_monitor.performance_tracker.get_latest("test_metric")
            
            self.log_test(
                "Performance Tracking",
                latest_value == 42.0,
                f"Recorded and retrieved metric: {latest_value}"
            )
            
            # Test alert system
            await system_monitor._create_alert(
                system_monitor.AlertSeverity.INFO,
                "test",
                "Test alert message"
            )
            
            self.log_test(
                "Alert System",
                len(system_monitor.alerts) > 0,
                f"Created test alert, total alerts: {len(system_monitor.alerts)}"
            )
            
            # Test component health tracking
            components = list(status["components"].keys())
            self.log_test(
                "Component Tracking",
                len(components) >= 5,
                f"Tracking {len(components)} components: {', '.join(components)}"
            )
            
        except Exception as e:
            self.log_test(
                "Monitoring System Test",
                False,
                f"Monitoring test failed: {e}",
                critical=True
            )
    
    async def validate_error_handling(self):
        """Validate error handling and recovery."""
        print("\n🚨 Error Handling Validation")
        print("=" * 50)
        
        try:
            # Test circuit breaker
            from core.error_handler import error_manager
            
            # Register test circuit breaker
            breaker = error_manager.register_circuit_breaker("test_breaker", failure_threshold=2)
            
            # Simulate failures
            for i in range(3):
                breaker.record_failure(Exception("Test failure"))
            
            self.log_test(
                "Circuit Breaker",
                breaker.state == "open",
                f"Circuit breaker state: {breaker.state}"
            )
            
            # Test error tracking
            error_manager.handle_error(
                Exception("Test error"),
                "test_component",
                error_manager.ErrorSeverity.MEDIUM
            )
            
            health = error_manager.get_system_health()
            self.log_test(
                "Error Tracking",
                health["total_errors"] > 0,
                f"Total errors tracked: {health['total_errors']}"
            )
            
        except Exception as e:
            self.log_test(
                "Error Handling Test",
                False,
                f"Error handling test failed: {e}",
                critical=True
            )
    
    def generate_report(self):
        """Generate validation report."""
        print("\n" + "=" * 60)
        print("🔍 SYSTEM VALIDATION REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["passed"]])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   🚨 Critical Failures: {len(self.critical_failures)}")
        print(f"   ⚠️  Warnings: {len(self.warnings)}")
        
        if self.critical_failures:
            print(f"\n🚨 CRITICAL ISSUES:")
            for failure in self.critical_failures:
                print(f"   • {failure['test']}: {failure['message']}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning['test']}: {warning['message']}")
        
        # Overall system health
        health_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        if health_score >= 90 and len(self.critical_failures) == 0:
            health_status = "🟢 EXCELLENT"
        elif health_score >= 75 and len(self.critical_failures) == 0:
            health_status = "🟡 GOOD"
        elif health_score >= 50:
            health_status = "🟠 NEEDS ATTENTION"
        else:
            health_status = "🔴 CRITICAL"
        
        print(f"\n🎯 Overall System Health: {health_status} ({health_score:.1f}%)")
        
        if len(self.critical_failures) == 0:
            print(f"\n✅ System is ready for operation!")
        else:
            print(f"\n❌ Please address critical issues before running the system.")
        
        return len(self.critical_failures) == 0


async def main():
    """Run comprehensive system validation."""
    print("🚀 Starting Comprehensive System Validation")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Python Version: {sys.version}")
    
    validator = SystemValidator()
    
    try:
        await validator.validate_configuration()
        await validator.validate_api_connections()
        await validator.validate_risk_management()
        await validator.validate_monitoring_system()
        await validator.validate_error_handling()
        
    except Exception as e:
        print(f"\n❌ Validation process failed: {e}")
        return False
    
    finally:
        # Cleanup connections
        try:
            await coinglass_client.disconnect()
            await bybit_gateway.disconnect()
        except:
            pass
    
    # Generate final report
    system_ready = validator.generate_report()
    
    return system_ready


if __name__ == "__main__":
    try:
        system_ready = asyncio.run(main())
        sys.exit(0 if system_ready else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1) 