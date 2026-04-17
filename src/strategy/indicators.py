"""
Technical Indicators Calculation Module.

Provides calculation of technical indicators like RSI, EMA, MACD
using pandas-ta library for trading signal generation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import pandas_ta as ta

from core.config import settings
from core.logger import get_logger

logger = get_logger("indicators")


class TechnicalIndicators:
    """
    Technical indicators calculator using pandas-ta.
    
    Provides methods to calculate various technical indicators
    on price data for trading strategy analysis.
    """
    
    def __init__(self):
        """Initialize the indicators calculator."""
        self.logger = logger
        
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required OHLCV columns.
        
        Args:
            df: Price DataFrame
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_columns)
    
    def calculate_rsi(
        self, 
        df: pd.DataFrame, 
        period: int = None
    ) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            df: Price DataFrame with OHLCV data
            period: RSI period (default from settings)
            
        Returns:
            Series with RSI values
        """
        if not self.validate_dataframe(df):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        period = period or settings.rsi_period
        
        try:
            # Calculate RSI using pandas-ta
            rsi = ta.rsi(df['close'], length=period)
            
            logger.debug(f"Calculated RSI with period {period}, latest value: {rsi.iloc[-1]:.2f}")
            
            return rsi
            
        except Exception as e:
            logger.error(f"Failed to calculate RSI: {e}")
            return pd.Series(dtype=float)
    
    def calculate_ema(
        self, 
        df: pd.DataFrame, 
        fast_period: int = None,
        slow_period: int = None
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Exponential Moving Averages (Fast and Slow).
        
        Args:
            df: Price DataFrame with OHLCV data
            fast_period: Fast EMA period (default from settings)
            slow_period: Slow EMA period (default from settings)
            
        Returns:
            Tuple of (fast_ema, slow_ema) Series
        """
        if not self.validate_dataframe(df):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        fast_period = fast_period or settings.ema_fast
        slow_period = slow_period or settings.ema_slow
        
        try:
            # Calculate EMAs using pandas-ta
            fast_ema = ta.ema(df['close'], length=fast_period)
            slow_ema = ta.ema(df['close'], length=slow_period)
            
            logger.debug(
                f"Calculated EMAs - Fast({fast_period}): {fast_ema.iloc[-1]:.2f}, "
                f"Slow({slow_period}): {slow_ema.iloc[-1]:.2f}"
            )
            
            return fast_ema, slow_ema
            
        except Exception as e:
            logger.error(f"Failed to calculate EMAs: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float)
    
    def calculate_macd(
        self, 
        df: pd.DataFrame,
        fast_period: int = None,
        slow_period: int = None,
        signal_period: int = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            df: Price DataFrame with OHLCV data
            fast_period: Fast EMA period for MACD
            slow_period: Slow EMA period for MACD
            signal_period: Signal line EMA period
            
        Returns:
            Tuple of (macd_line, signal_line, histogram) Series
        """
        if not self.validate_dataframe(df):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        fast_period = fast_period or settings.macd_fast
        slow_period = slow_period or settings.macd_slow
        signal_period = signal_period or settings.macd_signal
        
        try:
            # Calculate MACD using pandas-ta
            macd_data = ta.macd(
                df['close'], 
                fast=fast_period, 
                slow=slow_period, 
                signal=signal_period
            )
            
            if macd_data is None or macd_data.empty:
                logger.warning("MACD calculation returned empty result")
                return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
            
            # Extract MACD components
            macd_line = macd_data[f'MACD_{fast_period}_{slow_period}_{signal_period}']
            signal_line = macd_data[f'MACDs_{fast_period}_{slow_period}_{signal_period}']
            histogram = macd_data[f'MACDh_{fast_period}_{slow_period}_{signal_period}']
            
            logger.debug(
                f"Calculated MACD - Line: {macd_line.iloc[-1]:.4f}, "
                f"Signal: {signal_line.iloc[-1]:.4f}, "
                f"Histogram: {histogram.iloc[-1]:.4f}"
            )
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            logger.error(f"Failed to calculate MACD: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    def calculate_atr(
        self, 
        df: pd.DataFrame, 
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR) for volatility measurement.
        
        Args:
            df: Price DataFrame with OHLCV data
            period: ATR period
            
        Returns:
            Series with ATR values
        """
        if not self.validate_dataframe(df):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        try:
            # Calculate ATR using pandas-ta
            atr = ta.atr(df['high'], df['low'], df['close'], length=period)
            
            logger.debug(f"Calculated ATR with period {period}, latest value: {atr.iloc[-1]:.4f}")
            
            return atr
            
        except Exception as e:
            logger.error(f"Failed to calculate ATR: {e}")
            return pd.Series(dtype=float)
    
    def calculate_bollinger_bands(
        self, 
        df: pd.DataFrame, 
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            df: Price DataFrame with OHLCV data
            period: Moving average period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band) Series
        """
        if not self.validate_dataframe(df):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        try:
            # Calculate Bollinger Bands using pandas-ta
            bb_data = ta.bbands(df['close'], length=period, std=std_dev)
            
            if bb_data is None or bb_data.empty:
                logger.warning("Bollinger Bands calculation returned empty result")
                return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
            
            # Extract bands
            upper_band = bb_data[f'BBU_{period}_{std_dev}']
            middle_band = bb_data[f'BBM_{period}_{std_dev}']
            lower_band = bb_data[f'BBL_{period}_{std_dev}']
            
            logger.debug(
                f"Calculated Bollinger Bands - Upper: {upper_band.iloc[-1]:.2f}, "
                f"Middle: {middle_band.iloc[-1]:.2f}, Lower: {lower_band.iloc[-1]:.2f}"
            )
            
            return upper_band, middle_band, lower_band
            
        except Exception as e:
            logger.error(f"Failed to calculate Bollinger Bands: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    def detect_ema_crossover(
        self, 
        fast_ema: pd.Series, 
        slow_ema: pd.Series,
        lookback: int = 2
    ) -> Optional[str]:
        """
        Detect EMA crossover signals.
        
        Args:
            fast_ema: Fast EMA series
            slow_ema: Slow EMA series
            lookback: Number of periods to look back for confirmation
            
        Returns:
            'bullish' for golden cross, 'bearish' for death cross, None for no signal
        """
        try:
            if len(fast_ema) < lookback + 1 or len(slow_ema) < lookback + 1:
                return None
            
            # Check current and previous values
            current_fast = fast_ema.iloc[-1]
            current_slow = slow_ema.iloc[-1]
            prev_fast = fast_ema.iloc[-lookback]
            prev_slow = slow_ema.iloc[-lookback]
            
            # Bullish crossover: fast was below slow, now above
            if prev_fast <= prev_slow and current_fast > current_slow:
                logger.info("EMA bullish crossover detected")
                return 'bullish'
            
            # Bearish crossover: fast was above slow, now below
            elif prev_fast >= prev_slow and current_fast < current_slow:
                logger.info("EMA bearish crossover detected")
                return 'bearish'
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect EMA crossover: {e}")
            return None
    
    def detect_macd_crossover(
        self, 
        macd_line: pd.Series, 
        signal_line: pd.Series,
        lookback: int = 2
    ) -> Optional[str]:
        """
        Detect MACD line and signal line crossover.
        
        Args:
            macd_line: MACD line series
            signal_line: Signal line series
            lookback: Number of periods to look back for confirmation
            
        Returns:
            'bullish' for bullish crossover, 'bearish' for bearish crossover, None for no signal
        """
        try:
            if len(macd_line) < lookback + 1 or len(signal_line) < lookback + 1:
                return None
            
            # Check current and previous values
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            prev_macd = macd_line.iloc[-lookback]
            prev_signal = signal_line.iloc[-lookback]
            
            # Bullish crossover: MACD was below signal, now above
            if prev_macd <= prev_signal and current_macd > current_signal:
                logger.info("MACD bullish crossover detected")
                return 'bullish'
            
            # Bearish crossover: MACD was above signal, now below
            elif prev_macd >= prev_signal and current_macd < current_signal:
                logger.info("MACD bearish crossover detected")
                return 'bearish'
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect MACD crossover: {e}")
            return None
    
    def get_rsi_signal(self, rsi: pd.Series, oversold: float = 30, overbought: float = 70) -> Optional[str]:
        """
        Get RSI-based trading signal.
        
        Args:
            rsi: RSI series
            oversold: Oversold threshold
            overbought: Overbought threshold
            
        Returns:
            'buy' for oversold, 'sell' for overbought, None for neutral
        """
        try:
            if len(rsi) < 2:
                return None
            
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            
            # RSI moving out of oversold (potential buy)
            if prev_rsi <= oversold and current_rsi > oversold:
                logger.info(f"RSI buy signal: {current_rsi:.2f} (was {prev_rsi:.2f})")
                return 'buy'
            
            # RSI moving out of overbought (potential sell)
            elif prev_rsi >= overbought and current_rsi < overbought:
                logger.info(f"RSI sell signal: {current_rsi:.2f} (was {prev_rsi:.2f})")
                return 'sell'
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get RSI signal: {e}")
            return None
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate all supported indicators for given price data.
        
        Args:
            df: Price DataFrame with OHLCV data
            
        Returns:
            Dictionary with all calculated indicators
        """
        indicators = {}
        
        try:
            # RSI
            indicators['rsi'] = self.calculate_rsi(df)
            
            # EMAs
            fast_ema, slow_ema = self.calculate_ema(df)
            indicators['ema_fast'] = fast_ema
            indicators['ema_slow'] = slow_ema
            
            # MACD
            macd_line, signal_line, histogram = self.calculate_macd(df)
            indicators['macd_line'] = macd_line
            indicators['macd_signal'] = signal_line
            indicators['macd_histogram'] = histogram
            
            # ATR
            indicators['atr'] = self.calculate_atr(df)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            
            logger.info(f"Calculated {len(indicators)} indicators for {len(df)} data points")
            
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}")
            return {}
    
    def get_latest_values(self, indicators: Dict[str, pd.Series]) -> Dict[str, float]:
        """
        Get latest values from all indicators.
        
        Args:
            indicators: Dictionary of indicator series
            
        Returns:
            Dictionary with latest indicator values
        """
        latest_values = {}
        
        for name, series in indicators.items():
            if not series.empty and not pd.isna(series.iloc[-1]):
                latest_values[name] = float(series.iloc[-1])
            else:
                latest_values[name] = None
        
        return latest_values


# Global indicators instance
technical_indicators = TechnicalIndicators() 