"""
Configuration management using Pydantic Settings.

Handles loading settings from environment variables and .env files
for API keys, trading parameters, and runtime configuration.
"""

from typing import Optional, List
import os
from pathlib import Path
from pydantic import Field, validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    # CoinGlass API Configuration
    coinglass_api_key: str = Field(..., description="CoinGlass API key", min_length=10)
    coinglass_base_url: str = Field(
        default="https://open-api.coinglass.com/public",
        description="CoinGlass API base URL"
    )
    
    # Bybit Exchange Configuration
    bybit_api_key: str = Field(..., description="Bybit API key", min_length=10)
    bybit_api_secret: str = Field(..., description="Bybit API secret", min_length=10)
    bybit_testnet: bool = Field(default=True, description="Use Bybit testnet (default: True for safety)")
    bybit_leverage: int = Field(default=5, description="Default leverage for trades", ge=1, le=100)
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token", min_length=10)
    telegram_allowed_users: List[int] = Field(
        default_factory=list,
        description="List of allowed Telegram user IDs (empty = allow all)"
    )
    telegram_language: str = Field(default="en", description="Default language (en/fa)")
    
    # Trading Parameters
    default_symbol: str = Field(default="BTC/USDT:USDT", description="Default trading symbol")
    max_risk_percent: float = Field(
        default=2.0,
        description="Maximum risk per trade as percentage of equity",
        ge=0.1,
        le=10.0
    )
    trailing_stop_percent: float = Field(
        default=1.5,
        description="Trailing stop distance as percentage",
        ge=0.1,
        le=10.0
    )
    
    # Strategy Settings
    strategy_enabled: bool = Field(default=False, description="Enable trading signals (default: False for safety)")
    rsi_period: int = Field(default=14, description="RSI calculation period", ge=5, le=50)
    ema_fast: int = Field(default=50, description="Fast EMA period", ge=5, le=200)
    ema_slow: int = Field(default=200, description="Slow EMA period", ge=20, le=500)
    macd_fast: int = Field(default=12, description="MACD fast period", ge=5, le=50)
    macd_slow: int = Field(default=26, description="MACD slow period", ge=10, le=100)
    macd_signal: int = Field(default=9, description="MACD signal period", ge=3, le=30)
    
    # Data Update Intervals (seconds)
    data_update_interval: int = Field(default=30, description="Data update interval", ge=10, le=300)
    strategy_eval_interval: int = Field(default=60, description="Strategy evaluation interval", ge=30, le=600)
    position_management_interval: int = Field(default=300, description="Position management interval", ge=60, le=1800)
    
    # Database Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/trader",
        description="PostgreSQL connection URL"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_file_path: str = Field(default="logs/trader.log", description="Log file path")
    
    # Performance Settings
    enable_uvloop: bool = Field(default=True, description="Use uvloop for better performance")
    
    # Alert Settings
    enable_telegram_alerts: bool = Field(default=True, description="Send trading alerts via Telegram")
    
    # Enhanced Risk Management for 20%+ Annual Returns
    max_open_positions: int = Field(default=5, description="Maximum concurrent open positions", ge=1, le=10)
    stop_loss_percent: float = Field(default=1.5, description="Tighter stop loss percentage", ge=0.5, le=10.0)
    take_profit_percent: float = Field(default=8.0, description="Higher take profit percentage", ge=1.0, le=20.0)
    
    # CoinGlass Specific Settings
    coinglass_funding_threshold: float = Field(
        default=0.1,
        description="Funding rate threshold for extreme readings (%)",
        ge=0.01,
        le=1.0
    )
    coinglass_oi_change_threshold: float = Field(
        default=5.0,
        description="OI change threshold for signals (%)",
        ge=1.0,
        le=50.0
    )
    coinglass_ls_ratio_threshold: float = Field(
        default=0.7,
        description="Long/Short ratio threshold for extreme sentiment",
        ge=0.5,
        le=0.9
    )
    
    # Safety & Circuit Breakers
    max_daily_loss_percent: float = Field(
        default=10.0,
        description="Maximum daily loss before trading stops (%)",
        ge=5.0,
        le=50.0
    )
    max_consecutive_losses: int = Field(
        default=5,
        description="Maximum consecutive losses before pause",
        ge=3,
        le=20
    )
    min_account_balance: float = Field(
        default=100.0,
        description="Minimum account balance to continue trading",
        ge=10.0
    )
    
    @validator('ema_fast', 'ema_slow')
    def validate_ema_periods(cls, v, values):
        """Ensure fast EMA is less than slow EMA."""
        if 'ema_fast' in values and v == values['ema_fast']:
            return v  # Skip validation for fast EMA
        if 'ema_fast' in values and v <= values['ema_fast']:
            raise ValueError('Slow EMA period must be greater than fast EMA period')
        return v
    
    @validator('macd_slow')
    def validate_macd_periods(cls, v, values):
        """Ensure MACD fast is less than slow."""
        if 'macd_fast' in values and v <= values['macd_fast']:
            raise ValueError('MACD slow period must be greater than fast period')
        return v
    
    @validator('telegram_bot_token')
    def validate_telegram_token(cls, v):
        """Validate Telegram bot token format."""
        if not v.count(':') == 1:
            raise ValueError('Invalid Telegram bot token format')
        parts = v.split(':')
        if not (parts[0].isdigit() and len(parts[1]) >= 35):
            raise ValueError('Invalid Telegram bot token format')
        return v
    
    @validator('default_symbol')
    def validate_symbol_format(cls, v):
        """Validate trading symbol format."""
        if not ('/' in v and ':' in v):
            raise ValueError('Symbol must be in format BASE/QUOTE:SETTLE (e.g., BTC/USDT:USDT)')
        return v.upper()
    
    @validator('log_file_path')
    def validate_log_path(cls, v):
        """Ensure log directory exists."""
        log_dir = Path(v).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        return v
    
    def validate_api_keys(self) -> List[str]:
        """Validate all API keys are properly set."""
        errors = []
        
        if not self.coinglass_api_key or len(self.coinglass_api_key) < 20:
            errors.append("Invalid CoinGlass API key")
        
        if not self.bybit_api_key or len(self.bybit_api_key) < 10:
            errors.append("Invalid Bybit API key")
            
        if not self.bybit_api_secret or len(self.bybit_api_secret) < 20:
            errors.append("Invalid Bybit API secret")
            
        if not self.telegram_bot_token or ':' not in self.telegram_bot_token:
            errors.append("Invalid Telegram bot token")
        
        return errors
    
    def get_safety_status(self) -> dict:
        """Get current safety configuration status."""
        return {
            "testnet_enabled": self.bybit_testnet,
            "strategy_enabled": self.strategy_enabled,
            "max_risk_per_trade": self.max_risk_percent,
            "max_daily_loss": self.max_daily_loss_percent,
            "max_positions": self.max_open_positions,
            "safety_score": self._calculate_safety_score()
        }
    
    def _calculate_safety_score(self) -> int:
        """Calculate safety score (0-100)."""
        score = 100
        
        # Deduct points for risky settings
        if not self.bybit_testnet:
            score -= 30  # Live trading is risky
        if self.strategy_enabled:
            score -= 20  # Auto trading is risky
        if self.max_risk_percent > 5:
            score -= 20  # High risk per trade
        if self.max_open_positions > 3:
            score -= 10  # Too many positions
        if self.bybit_leverage > 10:
            score -= 20  # High leverage
            
        return max(0, score)


# Enhanced settings loader with validation
def load_settings() -> Settings:
    """Load and validate settings with comprehensive error handling."""
    try:
        settings = Settings()
        
        # Validate API keys
        api_errors = settings.validate_api_keys()
        if api_errors:
            raise ValidationError(f"API Key validation failed: {', '.join(api_errors)}")
        
        # Check safety score
        safety = settings.get_safety_status()
        if safety["safety_score"] < 50:
            print(f"⚠️  WARNING: Low safety score ({safety['safety_score']}/100)")
            print("Consider reviewing your configuration settings.")
        
        return settings
        
    except ValidationError as e:
        print(f"❌ Configuration validation failed: {e}")
        raise
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        raise


# Global settings instance with validation
try:
    settings = load_settings()
    print(f"✅ Configuration loaded successfully (Safety Score: {settings.get_safety_status()['safety_score']}/100)")
except Exception as e:
    print(f"❌ CRITICAL: Configuration failed to load: {e}")
    raise 