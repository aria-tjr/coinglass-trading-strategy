"""
Comprehensive System Monitoring and Health Tracking.

Monitors system performance, API health, trading metrics, 
and provides real-time alerts and diagnostics.
"""

import asyncio
import psutil
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from core.config import settings
from core.logger import get_logger, trading_logger

logger = get_logger("monitoring")


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: float
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def update(self, value: float):
        """Update metric value and status."""
        self.value = value
        self.timestamp = datetime.now()
        
        if value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif value >= self.threshold_warning:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY


@dataclass
class Alert:
    """System alert."""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    component: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PerformanceTracker:
    """Track system performance metrics."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics: Dict[str, List[float]] = {}
        self.timestamps: Dict[str, List[datetime]] = {}
    
    def record(self, metric_name: str, value: float):
        """Record a performance metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
            self.timestamps[metric_name] = []
        
        self.metrics[metric_name].append(value)
        self.timestamps[metric_name].append(datetime.now())
        
        # Keep only recent data
        if len(self.metrics[metric_name]) > self.window_size:
            self.metrics[metric_name] = self.metrics[metric_name][-self.window_size:]
            self.timestamps[metric_name] = self.timestamps[metric_name][-self.window_size:]
    
    def get_average(self, metric_name: str, minutes: int = 5) -> Optional[float]:
        """Get average value for a metric over time period."""
        if metric_name not in self.metrics:
            return None
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        values = []
        
        for i, timestamp in enumerate(self.timestamps[metric_name]):
            if timestamp >= cutoff_time:
                values.append(self.metrics[metric_name][i])
        
        return sum(values) / len(values) if values else None
    
    def get_latest(self, metric_name: str) -> Optional[float]:
        """Get latest value for a metric."""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return None
        return self.metrics[metric_name][-1]


class SystemMonitor:
    """Comprehensive system monitoring."""
    
    def __init__(self):
        self.health_metrics: Dict[str, HealthMetric] = {}
        self.performance_tracker = PerformanceTracker()
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.last_check_time = None
        self.check_interval = 30  # seconds
        
        # Component health tracking
        self.component_health = {
            "coinglass_api": HealthStatus.OFFLINE,
            "bybit_exchange": HealthStatus.OFFLINE,
            "telegram_bot": HealthStatus.OFFLINE,
            "strategy_engine": HealthStatus.OFFLINE,
            "risk_manager": HealthStatus.OFFLINE
        }
        
        # Initialize health metrics
        self._initialize_metrics()
        
        logger.info("System monitor initialized")
    
    def _initialize_metrics(self):
        """Initialize health metrics with thresholds."""
        self.health_metrics = {
            "cpu_usage": HealthMetric("CPU Usage", 0, HealthStatus.HEALTHY, 70, 90, "%"),
            "memory_usage": HealthMetric("Memory Usage", 0, HealthStatus.HEALTHY, 80, 95, "%"),
            "disk_usage": HealthMetric("Disk Usage", 0, HealthStatus.HEALTHY, 85, 95, "%"),
            "api_response_time": HealthMetric("API Response Time", 0, HealthStatus.HEALTHY, 2000, 5000, "ms"),
            "error_rate": HealthMetric("Error Rate", 0, HealthStatus.HEALTHY, 5, 15, "%"),
            "trade_latency": HealthMetric("Trade Latency", 0, HealthStatus.HEALTHY, 1000, 3000, "ms"),
            "account_balance": HealthMetric("Account Balance", 0, HealthStatus.HEALTHY, 200, 100, "USDT"),
            "daily_pnl": HealthMetric("Daily P&L", 0, HealthStatus.HEALTHY, -5, -10, "%")
        }
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts."""
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start continuous monitoring."""
        self.monitoring_active = True
        logger.info("System monitoring started")
        
        while self.monitoring_active:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False
        logger.info("System monitoring stopped")
    
    async def _perform_health_check(self):
        """Perform comprehensive health check."""
        try:
            # System resource metrics
            await self._check_system_resources()
            
            # API health checks
            await self._check_api_health()
            
            # Trading system health
            await self._check_trading_health()
            
            # Check for anomalies
            self._detect_anomalies()
            
            self.last_check_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _check_system_resources(self):
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.health_metrics["cpu_usage"].update(cpu_percent)
            self.performance_tracker.record("cpu_usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.health_metrics["memory_usage"].update(memory_percent)
            self.performance_tracker.record("memory_usage", memory_percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.health_metrics["disk_usage"].update(disk_percent)
            self.performance_tracker.record("disk_usage", disk_percent)
            
            # Check for critical resource usage
            if cpu_percent > 95:
                await self._create_alert(
                    AlertSeverity.CRITICAL,
                    "system",
                    f"Critical CPU usage: {cpu_percent:.1f}%"
                )
            
            if memory_percent > 95:
                await self._create_alert(
                    AlertSeverity.CRITICAL,
                    "system", 
                    f"Critical memory usage: {memory_percent:.1f}%"
                )
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
    
    async def _check_api_health(self):
        """Check API health and response times."""
        try:
            # Import here to avoid circular imports
            from infra.coinglass_client import coinglass_client
            from infra.exchange_gateway import bybit_gateway
            
            # CoinGlass API health
            start_time = time.time()
            try:
                if await coinglass_client.health_check():
                    self.component_health["coinglass_api"] = HealthStatus.HEALTHY
                    response_time = (time.time() - start_time) * 1000
                    self.performance_tracker.record("coinglass_response_time", response_time)
                else:
                    self.component_health["coinglass_api"] = HealthStatus.CRITICAL
                    await self._create_alert(
                        AlertSeverity.ERROR,
                        "coinglass_api",
                        "CoinGlass API health check failed"
                    )
            except Exception as e:
                self.component_health["coinglass_api"] = HealthStatus.OFFLINE
                logger.error(f"CoinGlass health check error: {e}")
            
            # Bybit API health
            start_time = time.time()
            try:
                if await bybit_gateway.health_check():
                    self.component_health["bybit_exchange"] = HealthStatus.HEALTHY
                    response_time = (time.time() - start_time) * 1000
                    self.performance_tracker.record("bybit_response_time", response_time)
                else:
                    self.component_health["bybit_exchange"] = HealthStatus.CRITICAL
                    await self._create_alert(
                        AlertSeverity.ERROR,
                        "bybit_exchange",
                        "Bybit API health check failed"
                    )
            except Exception as e:
                self.component_health["bybit_exchange"] = HealthStatus.OFFLINE
                logger.error(f"Bybit health check error: {e}")
                
        except Exception as e:
            logger.error(f"API health check failed: {e}")
    
    async def _check_trading_health(self):
        """Check trading system health."""
        try:
            # Import here to avoid circular imports
            from strategy.risk_manager import risk_manager
            
            # Risk manager health
            if risk_manager.emergency_stop:
                self.component_health["risk_manager"] = HealthStatus.CRITICAL
                await self._create_alert(
                    AlertSeverity.CRITICAL,
                    "risk_manager",
                    "Emergency stop activated"
                )
            else:
                self.component_health["risk_manager"] = HealthStatus.HEALTHY
            
            # Check account balance
            if risk_manager.account_balance > 0:
                balance_metric = self.health_metrics["account_balance"]
                balance_metric.update(risk_manager.account_balance)
                
                if risk_manager.account_balance < balance_metric.threshold_critical:
                    await self._create_alert(
                        AlertSeverity.CRITICAL,
                        "trading",
                        f"Account balance critically low: ${risk_manager.account_balance:.2f}"
                    )
            
            # Check daily P&L
            if risk_manager.daily_pnl != 0:
                daily_pnl_percent = (risk_manager.daily_pnl / risk_manager.daily_starting_balance) * 100
                self.health_metrics["daily_pnl"].update(abs(daily_pnl_percent))
                
                if daily_pnl_percent < -10:  # More than 10% daily loss
                    await self._create_alert(
                        AlertSeverity.ERROR,
                        "trading",
                        f"High daily loss: {daily_pnl_percent:.2f}%"
                    )
            
        except Exception as e:
            logger.error(f"Trading health check failed: {e}")
    
    def _detect_anomalies(self):
        """Detect performance anomalies."""
        try:
            # Check for unusual API response times
            avg_response_time = self.performance_tracker.get_average("coinglass_response_time", 5)
            if avg_response_time and avg_response_time > 3000:  # 3 seconds
                asyncio.create_task(self._create_alert(
                    AlertSeverity.WARNING,
                    "performance",
                    f"High API response time: {avg_response_time:.0f}ms"
                ))
            
            # Check error rate trends
            error_count = len([alert for alert in self.alerts[-20:] 
                             if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]])
            error_rate = (error_count / 20) * 100 if len(self.alerts) >= 20 else 0
            
            self.health_metrics["error_rate"].update(error_rate)
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
    
    async def _create_alert(self, severity: AlertSeverity, component: str, message: str, **details):
        """Create and process an alert."""
        try:
            alert = Alert(
                id=f"{component}_{int(time.time())}",
                timestamp=datetime.now(),
                severity=severity,
                component=component,
                message=message,
                details=details
            )
            
            self.alerts.append(alert)
            
            # Keep only recent alerts
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-500:]
            
            # Log alert
            log_level = {
                AlertSeverity.INFO: logger.info,
                AlertSeverity.WARNING: logger.warning,
                AlertSeverity.ERROR: logger.error,
                AlertSeverity.CRITICAL: logger.critical
            }.get(severity, logger.info)
            
            log_level(f"ALERT [{severity.value.upper()}] {component}: {message}")
            
            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        overall_health = HealthStatus.HEALTHY
        
        # Determine overall health from components
        health_priorities = {
            HealthStatus.OFFLINE: 4,
            HealthStatus.CRITICAL: 3,
            HealthStatus.WARNING: 2,
            HealthStatus.HEALTHY: 1
        }
        
        worst_health = max(
            self.component_health.values(),
            key=lambda h: health_priorities.get(h, 0)
        )
        
        # Recent alerts
        recent_alerts = [
            alert for alert in self.alerts
            if alert.timestamp > datetime.now() - timedelta(minutes=30)
        ]
        
        critical_alerts = [
            alert for alert in recent_alerts
            if alert.severity == AlertSeverity.CRITICAL and not alert.resolved
        ]
        
        return {
            "overall_health": worst_health.value,
            "timestamp": datetime.now().isoformat(),
            "components": {name: status.value for name, status in self.component_health.items()},
            "metrics": {
                name: {
                    "value": metric.value,
                    "status": metric.status.value,
                    "unit": metric.unit
                }
                for name, metric in self.health_metrics.items()
            },
            "recent_alerts": len(recent_alerts),
            "critical_alerts": len(critical_alerts),
            "monitoring_active": self.monitoring_active,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            "system_resources": {
                "cpu_avg_5min": self.performance_tracker.get_average("cpu_usage", 5),
                "memory_avg_5min": self.performance_tracker.get_average("memory_usage", 5),
                "disk_usage": self.performance_tracker.get_latest("disk_usage")
            },
            "api_performance": {
                "coinglass_avg_response": self.performance_tracker.get_average("coinglass_response_time", 5),
                "bybit_avg_response": self.performance_tracker.get_average("bybit_response_time", 5)
            },
            "alerts_summary": {
                "total_alerts": len(self.alerts),
                "critical_unresolved": len([a for a in self.alerts 
                                          if a.severity == AlertSeverity.CRITICAL and not a.resolved]),
                "recent_errors": len([a for a in self.alerts 
                                    if a.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]
                                    and a.timestamp > datetime.now() - timedelta(hours=1)])
            }
        }
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert by ID."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert {alert_id} resolved")
                return True
        return False


# Global monitor instance
system_monitor = SystemMonitor() 