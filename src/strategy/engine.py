"""
Trading Strategy Engine.

Main decision-making component that combines CoinGlass market data
with technical analysis to generate trading signals with risk management.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd

from core.config import settings
from core.logger import get_logger, trading_logger
from infra.coinglass_client import coinglass_client
from infra.exchange_gateway import bybit_gateway
from infra.telegram_bot import telegram_bot
from strategy.indicators import technical_indicators
from strategy.risk_manager import risk_manager, PositionSide, TradeSignal
from strategy.portfolio_manager import portfolio_manager

logger = get_logger("strategy_engine")


class MarketCondition:
    """Represents current market conditions."""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.price_data: Optional[pd.DataFrame] = None
        self.coinglass_data: Dict[str, Any] = {}
        self.indicators: Dict[str, pd.Series] = {}
        self.sentiment: str = "neutral"  # bullish, bearish, neutral
        self.volatility: float = 0.0
        
    def is_valid(self) -> bool:
        """Check if market condition data is valid."""
        return (
            self.price_data is not None and 
            not self.price_data.empty and
            bool(self.coinglass_data) and
            bool(self.indicators)
        )


class TradingStrategy:
    """
    Main trading strategy implementation.
    
    Combines CoinGlass derivatives data with technical analysis
    to generate high-probability trading signals.
    """
    
    def __init__(self):
        """Initialize the trading strategy."""
        self.symbol = settings.default_symbol
        self.enabled = settings.strategy_enabled
        
        # Market data storage
        self.current_market: Optional[MarketCondition] = None
        self.last_update: Optional[datetime] = None
        
        # Signal tracking
        self.last_signal: Optional[TradeSignal] = None
        self.signal_history: List[TradeSignal] = []
        
        # Performance tracking
        self.total_signals = 0
        self.successful_signals = 0
        
        logger.info(f"Trading strategy initialized for {self.symbol}")
    
    async def update_market_data(self) -> bool:
        """
        Update market data from all sources.
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            market = MarketCondition()
            
            # Get price data from exchange
            price_df = await bybit_gateway.get_ohlcv(
                self.symbol, 
                timeframe='1h', 
                limit=200
            )
            
            if price_df.empty:
                logger.warning("Failed to get price data")
                return False
            
            market.price_data = price_df
            
            # Get CoinGlass data
            symbol_clean = self.symbol.split('/')[0]  # BTC from BTC/USDT:USDT
            coinglass_data = await coinglass_client.get_latest_metrics(symbol_clean)
            
            if 'error' in coinglass_data:
                logger.warning(f"CoinGlass data error: {coinglass_data['error']}")
            else:
                market.coinglass_data = coinglass_data
            
            # Calculate technical indicators
            indicators = technical_indicators.calculate_all_indicators(price_df)
            
            if not indicators:
                logger.warning("Failed to calculate indicators")
                return False
            
            market.indicators = indicators
            
            # Calculate volatility (ATR-based)
            if 'atr' in indicators and not indicators['atr'].empty:
                current_price = price_df['close'].iloc[-1]
                market.volatility = indicators['atr'].iloc[-1] / current_price
            
            # Store updated market condition
            self.current_market = market
            self.last_update = datetime.now()
            
            trading_logger.log_data_update(
                "strategy_engine", 
                self.symbol,
                price_points=len(price_df),
                indicators=len(indicators),
                coinglass_valid=bool(market.coinglass_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update market data: {e}")
            return False
    
    def analyze_coinglass_sentiment(self, cg_data: Dict[str, Any]) -> Tuple[str, float]:
        """
        Analyze CoinGlass data for market sentiment.
        
        Args:
            cg_data: CoinGlass metrics data
            
        Returns:
            Tuple of (sentiment, confidence)
        """
        try:
            sentiment_score = 0.0
            factors = 0
            
            # Analyze funding rate
            funding_data = cg_data.get('funding_rate', {})
            funding_value = funding_data.get('value', 0)
            
            if abs(funding_value) > settings.coinglass_funding_threshold:
                if funding_value > settings.coinglass_funding_threshold:
                    # Very positive funding - too many longs (bearish signal)
                    sentiment_score -= 2
                    logger.debug(f"High positive funding rate: {funding_value:.4f} (bearish)")
                elif funding_value < -settings.coinglass_funding_threshold:
                    # Very negative funding - too many shorts (bullish signal)
                    sentiment_score += 2
                    logger.debug(f"High negative funding rate: {funding_value:.4f} (bullish)")
                factors += 1
            
            # Analyze long/short ratio
            ls_data = cg_data.get('long_short_ratio', {})
            ls_value = ls_data.get('value', 0.5)
            
            if ls_value > settings.coinglass_ls_ratio_threshold:
                # Too many longs - contrarian bearish
                sentiment_score -= 1
                logger.debug(f"High long ratio: {ls_value:.2f} (bearish)")
                factors += 1
            elif ls_value < (1 - settings.coinglass_ls_ratio_threshold):
                # Too many shorts - contrarian bullish
                sentiment_score += 1
                logger.debug(f"High short ratio: {ls_value:.2f} (bullish)")
                factors += 1
            
            # Analyze Open Interest changes
            oi_data = cg_data.get('open_interest', {})
            oi_change = oi_data.get('change_24h', 0)
            
            # Get price change for OI analysis
            if self.current_market and self.current_market.price_data is not None:
                price_change = (
                    self.current_market.price_data['close'].iloc[-1] - 
                    self.current_market.price_data['close'].iloc[-24]
                ) / self.current_market.price_data['close'].iloc[-24] * 100
                
                # OI increasing with price = trend confirmation
                if abs(oi_change) > settings.coinglass_oi_change_threshold:
                    if oi_change > 0 and price_change > 0:
                        sentiment_score += 1  # Bullish confirmation
                        logger.debug(f"OI up with price up: {oi_change:.1f}% (bullish)")
                    elif oi_change > 0 and price_change < 0:
                        sentiment_score -= 1  # Bearish confirmation
                        logger.debug(f"OI up with price down: {oi_change:.1f}% (bearish)")
                    factors += 1
            
            # Calculate final sentiment
            if factors == 0:
                return "neutral", 0.0
            
            avg_score = sentiment_score / factors
            confidence = min(abs(avg_score) / 2.0, 1.0)  # Normalize to 0-1
            
            if avg_score > 0.5:
                sentiment = "bullish"
            elif avg_score < -0.5:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            logger.info(f"CoinGlass sentiment: {sentiment} (confidence: {confidence:.2f})")
            
            return sentiment, confidence
            
        except Exception as e:
            logger.error(f"Failed to analyze CoinGlass sentiment: {e}")
            return "neutral", 0.0
    
    def analyze_technical_signals(self, indicators: Dict[str, pd.Series]) -> Tuple[str, float]:
        """
        Analyze technical indicators for trading signals.
        
        Args:
            indicators: Dictionary of technical indicators
            
        Returns:
            Tuple of (signal, confidence)
        """
        try:
            signal_score = 0.0
            signals_count = 0
            
            # RSI analysis
            if 'rsi' in indicators and not indicators['rsi'].empty:
                rsi_signal = technical_indicators.get_rsi_signal(indicators['rsi'])
                if rsi_signal == 'buy':
                    signal_score += 1
                    signals_count += 1
                elif rsi_signal == 'sell':
                    signal_score -= 1
                    signals_count += 1
            
            # EMA crossover analysis
            if 'ema_fast' in indicators and 'ema_slow' in indicators:
                ema_crossover = technical_indicators.detect_ema_crossover(
                    indicators['ema_fast'], 
                    indicators['ema_slow']
                )
                if ema_crossover == 'bullish':
                    signal_score += 2  # EMA crossovers are strong signals
                    signals_count += 1
                elif ema_crossover == 'bearish':
                    signal_score -= 2
                    signals_count += 1
            
            # MACD analysis
            if 'macd_line' in indicators and 'macd_signal' in indicators:
                macd_crossover = technical_indicators.detect_macd_crossover(
                    indicators['macd_line'], 
                    indicators['macd_signal']
                )
                if macd_crossover == 'bullish':
                    signal_score += 1.5
                    signals_count += 1
                elif macd_crossover == 'bearish':
                    signal_score -= 1.5
                    signals_count += 1
            
            # Price vs EMA trend analysis
            if 'ema_slow' in indicators and self.current_market.price_data is not None:
                current_price = self.current_market.price_data['close'].iloc[-1]
                ema_slow_current = indicators['ema_slow'].iloc[-1]
                
                if current_price > ema_slow_current * 1.02:  # 2% above EMA
                    signal_score += 0.5  # Mild bullish
                    signals_count += 1
                elif current_price < ema_slow_current * 0.98:  # 2% below EMA
                    signal_score -= 0.5  # Mild bearish
                    signals_count += 1
            
            if signals_count == 0:
                return "neutral", 0.0
            
            # Calculate average signal
            avg_score = signal_score / signals_count
            confidence = min(abs(avg_score) / 2.0, 1.0)
            
            if avg_score > 0.3:
                signal = "bullish"
            elif avg_score < -0.3:
                signal = "bearish"
            else:
                signal = "neutral"
            
            logger.info(f"Technical signals: {signal} (confidence: {confidence:.2f}, score: {avg_score:.2f})")
            
            return signal, confidence
            
        except Exception as e:
            logger.error(f"Failed to analyze technical signals: {e}")
            return "neutral", 0.0
    
    def generate_trading_signal(self) -> Optional[TradeSignal]:
        """
        Generate trading signal by combining all analysis.
        
        Returns:
            TradeSignal if conditions are met, None otherwise
        """
        try:
            if not self.current_market or not self.current_market.is_valid():
                logger.warning("Invalid market data for signal generation")
                return None

            # Analyze CoinGlass sentiment
            cg_sentiment, cg_confidence = self.analyze_coinglass_sentiment(
                self.current_market.coinglass_data
            )

            # Analyze technical signals
            tech_signal, tech_confidence = self.analyze_technical_signals(
                self.current_market.indicators
            )

            # Combine signals - require confluence for action
            combined_signal = None
            combined_confidence = 0.0

            # Strong bullish: both agree on bullish OR one is bullish and other neutral
            if ((cg_sentiment == "bullish" and tech_signal == "bullish") or
                (cg_sentiment == "bullish" and tech_signal == "neutral" and cg_confidence > 0.7) or
                (tech_signal == "bullish" and cg_sentiment == "neutral" and tech_confidence > 0.7)):
                combined_signal = "bullish"
                combined_confidence = (cg_confidence + tech_confidence) / 2

            # Strong bearish: both agree on bearish OR one is bearish and other neutral
            elif ((cg_sentiment == "bearish" and tech_signal == "bearish") or
                  (cg_sentiment == "bearish" and tech_signal == "neutral" and cg_confidence > 0.7) or
                  (tech_signal == "bearish" and cg_sentiment == "neutral" and tech_confidence > 0.7)):
                combined_signal = "bearish"
                combined_confidence = (cg_confidence + tech_confidence) / 2

            if not combined_signal or combined_confidence < 0.6:
                logger.debug("No strong signal generated - waiting for better setup")
                return None

            # Get current price for signal
            current_price = self.current_market.price_data['close'].iloc[-1]

            # Get ATR for stop loss calculation
            atr_value = None
            if 'atr' in self.current_market.indicators:
                atr_value = self.current_market.indicators['atr'].iloc[-1]

            # Determine position side
            side = PositionSide.LONG if combined_signal == "bullish" else PositionSide.SHORT

            # Create detailed reason
            reason = f"CoinGlass: {cg_sentiment} ({cg_confidence:.2f}), Technical: {tech_signal} ({tech_confidence:.2f})"

            # Generate trade signal
            signal = risk_manager.create_trade_signal(
                symbol=self.symbol,
                side=side,
                entry_price=current_price,
                confidence=combined_confidence,
                reason=reason,
                atr=atr_value
            )

            logger.info(f"Generated {side.value} signal for {self.symbol} @ {current_price:.2f}")

            return signal

        except Exception as e:
            logger.error(f"Failed to generate trading signal: {e}")
            return None

    async def evaluate_strategy(self) -> None:
        """
        Enhanced strategy evaluation with portfolio management.
        """
        try:
            if not self.enabled:
                logger.debug("Strategy evaluation skipped - strategy disabled")
                return

            logger.info("Evaluating enhanced portfolio strategy...")

            # Use portfolio manager for multi-symbol evaluation
            portfolio_signals = await portfolio_manager.evaluate_all_symbols()
            
            if not portfolio_signals:
                logger.debug("No portfolio signals generated")
                return

            # Get account balance
            balance = await bybit_gateway.get_balance()
            account_balance = balance.get('free', 0)
            
            # Execute up to 3 best signals simultaneously
            executed_signals = 0
            for signal in portfolio_signals[:3]:  # Maximum 3 concurrent positions
                
                # Validate signal
                current_positions = await bybit_gateway.get_positions()
                is_valid, reason = risk_manager.validate_signal(
                    signal, 
                    account_balance, 
                    len(current_positions)
                )

                if not is_valid:
                    logger.warning(f"Signal validation failed for {signal.symbol}: {reason}")
                    continue

                # Execute signal
                await self._execute_signal(signal, account_balance)
                executed_signals += 1
                
                self.total_signals += 1
                self.last_signal = signal
                self.signal_history.append(signal)

            # Portfolio rebalancing
            await portfolio_manager.rebalance_portfolio()
            
            logger.info(f"Executed {executed_signals} portfolio signals")

            # Keep only last 100 signals
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]

        except Exception as e:
            logger.error(f"Enhanced strategy evaluation failed: {e}")
    
    async def _execute_signal(self, signal: TradeSignal, account_balance: float) -> None:
        """Execute a trading signal."""
        try:
            # Calculate position size
            position_size, risk_amount, notional_value = risk_manager.calculate_position_size(
                account_balance,
                signal.entry_price,
                signal.stop_loss,
                signal.side
            )
            
            if position_size <= 0:
                logger.warning("Invalid position size calculated")
                return
            
            # Place entry order
            side = "buy" if signal.side == PositionSide.LONG else "sell"
            
            order = await bybit_gateway.create_market_order(
                self.symbol,
                side,
                position_size
            )
            
            if not order:
                logger.error("Failed to place entry order")
                return
            
            # Place stop loss order
            stop_side = "sell" if signal.side == PositionSide.LONG else "buy"
            
            stop_order = await bybit_gateway.create_stop_order(
                self.symbol,
                stop_side,
                position_size,
                signal.stop_loss
            )
            
            # Place take profit order (optional)
            tp_order = None
            if signal.take_profit:
                tp_order = await bybit_gateway.create_limit_order(
                    self.symbol,
                    stop_side,
                    position_size,
                    signal.take_profit,
                    reduce_only=True
                )
            
            # Set up trailing stop
            risk_manager.create_trailing_stop(
                self.symbol,
                signal.side,
                signal.entry_price,
                signal.stop_loss
            )
            
            # Send Telegram alert
            await telegram_bot.send_signal_alert(
                self.symbol,
                signal.side.value.upper(),
                signal.reason,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                settings.max_risk_percent
            )
            
            logger.info(f"Signal executed successfully: {signal.side.value} {self.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
    
    async def _manage_existing_positions(self, positions: List) -> None:
        """Manage existing positions with trailing stops."""
        try:
            for position in positions:
                symbol = position.symbol
                current_price = position.mark_price
                
                # Update trailing stop
                update_result = risk_manager.update_trailing_stop(symbol, current_price)
                
                if update_result:
                    updated, new_stop = update_result
                    if updated:
                        # Update stop loss order on exchange
                        # This would require canceling old stop and placing new one
                        logger.info(f"Trailing stop updated for {symbol}: {new_stop:.2f}")
                
        except Exception as e:
            logger.error(f"Failed to manage positions: {e}")
    
    def enable_strategy(self) -> None:
        """Enable the trading strategy."""
        self.enabled = True
        logger.info("Trading strategy enabled")
    
    def disable_strategy(self) -> None:
        """Disable the trading strategy."""
        self.enabled = False
        logger.info("Trading strategy disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get strategy status information."""
        return {
            "enabled": self.enabled,
            "symbol": self.symbol,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "market_data_valid": self.current_market.is_valid() if self.current_market else False,
            "total_signals": self.total_signals,
            "success_rate": (self.successful_signals / self.total_signals * 100) if self.total_signals > 0 else 0,
            "last_signal": {
                "side": self.last_signal.side.value,
                "price": self.last_signal.entry_price,
                "confidence": self.last_signal.confidence,
                "timestamp": self.last_signal.timestamp.isoformat()
            } if self.last_signal else None
        }


# Global strategy instance
trading_strategy = TradingStrategy() 