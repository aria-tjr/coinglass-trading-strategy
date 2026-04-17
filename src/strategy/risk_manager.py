"""
Enhanced Risk Management System.

Provides comprehensive risk controls, position sizing, stop losses,
circuit breakers, and emergency shutdown mechanisms.
"""

import asyncio
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from core.config import settings
from core.logger import get_logger, trading_logger

logger = get_logger("risk_manager")


class PositionSide(Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"


@dataclass
class TradeSignal:
    """Trading signal with risk parameters."""
    symbol: str
    side: PositionSide
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    confidence: float
    reason: str
    risk_reward_ratio: float
    timestamp: datetime
    risk_amount: float = 0.0
    position_size: float = 0.0


@dataclass
class TradeRecord:
    """Historical trade record for tracking performance."""
    symbol: str
    side: PositionSide
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float
    timestamp: datetime
    hold_time: timedelta
    exit_reason: str


@dataclass
class PositionRisk:
    """Risk parameters for a position."""
    symbol: str
    size: float
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    trailing_stop_distance: float
    risk_amount: float  # Amount at risk in USDT
    notional_value: float  # Position value in USDT


@dataclass
class TrailingStop:
    """Trailing stop configuration and state."""
    symbol: str
    side: PositionSide
    initial_stop: float
    current_stop: float
    trail_distance: float  # Percentage or absolute
    highest_price: float  # For long positions
    lowest_price: float   # For short positions
    is_percentage: bool = True
    last_update: datetime = None


class RiskManager:
    """
    Enhanced risk management system with comprehensive safety features.
    """
    
    def __init__(self):
        """Initialize risk manager with safety defaults."""
        # Account tracking
        self.account_balance = 0.0
        self.initial_balance = 0.0
        self.daily_starting_balance = 0.0
        
        # Enhanced position limits for 20%+ annual returns
        self.max_risk_percent = min(settings.max_risk_percent * 1.5, 4.0)  # Increased to 3-4%
        self.max_open_positions = min(settings.max_open_positions * 2, 5)  # Allow up to 5 positions
        self.stop_loss_percent = max(settings.stop_loss_percent * 0.8, 1.5)  # Tighter stops 1.5%
        self.take_profit_percent = settings.take_profit_percent * 2.0  # Higher targets 8%
        
        # Safety limits
        self.max_daily_loss = settings.max_daily_loss_percent
        self.max_consecutive_losses = settings.max_consecutive_losses
        self.min_account_balance = settings.min_account_balance
        
        # Tracking variables
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.trade_history: List[TradeRecord] = []
        self.daily_trades = 0
        self.max_daily_trades = 35  # Increased for higher frequency trading
        
        # Emergency states
        self.emergency_stop = False
        self.daily_loss_exceeded = False
        self.balance_too_low = False
        
        # Trailing stops
        self.trailing_stops: Dict[str, Dict] = {}
        
        logger.info("Enhanced risk manager initialized with safety controls")
    
    def set_account_balance(self, balance: float) -> None:
        """Update account balance and check safety thresholds."""
        self.account_balance = balance
        
        # Set initial balance if not set
        if self.initial_balance == 0:
            self.initial_balance = balance
        
        # Reset daily tracking if new day
        today = datetime.now().date()
        if today != self.last_reset_date:
            self._reset_daily_tracking()
            self.last_reset_date = today
        
        # Check safety thresholds
        self._check_safety_thresholds()
        
        logger.info(f"Account balance updated: ${balance:.2f}")
    
    def _reset_daily_tracking(self):
        """Reset daily tracking variables."""
        self.daily_starting_balance = self.account_balance
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_loss_exceeded = False
        
        logger.info("Daily tracking reset")
    
    def _check_safety_thresholds(self):
        """Check all safety thresholds and set flags."""
        # Check minimum balance
        if self.account_balance < self.min_account_balance:
            self.balance_too_low = True
            logger.warning(f"Account balance too low: ${self.account_balance:.2f}")
        else:
            self.balance_too_low = False
        
        # Check daily loss limit
        if self.daily_starting_balance > 0:
            daily_loss_percent = ((self.daily_starting_balance - self.account_balance) / 
                                self.daily_starting_balance) * 100
            
            if daily_loss_percent > self.max_daily_loss:
                self.daily_loss_exceeded = True
                logger.error(f"Daily loss limit exceeded: {daily_loss_percent:.2f}%")
            else:
                self.daily_loss_exceeded = False
        
        # Set emergency stop if any safety condition is violated
        self.emergency_stop = (
            self.balance_too_low or 
            self.daily_loss_exceeded or 
            self.consecutive_losses >= self.max_consecutive_losses
        )
        
        if self.emergency_stop:
            logger.critical("EMERGENCY STOP ACTIVATED - Trading halted for safety")
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk conditions.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        if self.emergency_stop:
            return False, "Emergency stop activated"
        
        if self.balance_too_low:
            return False, f"Account balance too low: ${self.account_balance:.2f}"
        
        if self.daily_loss_exceeded:
            return False, "Daily loss limit exceeded"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Too many consecutive losses: {self.consecutive_losses}"
        
        if self.daily_trades >= self.max_daily_trades:
            return False, "Daily trade limit reached"
        
        return True, "Trading allowed"
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        side: PositionSide,
        risk_percentage: float = None,
        max_leverage: float = None
    ) -> Tuple[float, float, float]:
        """
        Calculate position size with enhanced risk controls.
        
        Returns:
            Tuple of (position_size, risk_amount, notional_value)
        """
        try:
            # Use provided risk percentage or default
            risk_pct = (risk_percentage or self.max_risk_percent) / 100
            
            # Apply dynamic risk adjustment based on recent performance
            risk_pct = self._adjust_risk_for_performance(risk_pct)
            
            # Calculate risk amount
            risk_amount = account_balance * risk_pct
            
            # Calculate price difference for stop loss
            if side == PositionSide.LONG:
                price_diff = entry_price - stop_loss_price
            else:  # SHORT
                price_diff = stop_loss_price - entry_price
            
            if price_diff <= 0:
                logger.warning("Invalid stop loss price")
                return 0.0, 0.0, 0.0
            
            # Calculate position size
            position_size = risk_amount / price_diff
            notional_value = position_size * entry_price
            
            # Apply leverage limits
            max_leverage = max_leverage or settings.bybit_leverage
            max_notional = account_balance * max_leverage
            
            if notional_value > max_notional:
                # Scale down position to fit leverage limits
                position_size = max_notional / entry_price
                notional_value = max_notional
                # Recalculate actual risk
                risk_amount = position_size * price_diff
            
            # Additional safety checks
            if notional_value > account_balance * 0.5:  # Max 50% of balance per trade
                logger.warning("Position size too large, reducing")
                position_size = (account_balance * 0.5) / entry_price
                notional_value = position_size * entry_price
                risk_amount = position_size * price_diff
            
            logger.info(
                f"Position size calculated: {position_size:.6f}, "
                f"Risk: ${risk_amount:.2f}, Notional: ${notional_value:.2f}"
            )
            
            return position_size, risk_amount, notional_value
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0.0, 0.0, 0.0
    
    def _adjust_risk_for_performance(self, base_risk: float) -> float:
        """Adjust risk based on recent performance."""
        if len(self.trade_history) < 5:
            return base_risk
        
        # Look at last 10 trades
        recent_trades = self.trade_history[-10:]
        win_rate = sum(1 for trade in recent_trades if trade.pnl > 0) / len(recent_trades)
        
        # Reduce risk if win rate is low
        if win_rate < 0.3:
            adjusted_risk = base_risk * 0.5
            logger.info(f"Risk reduced due to low win rate: {win_rate:.2f}")
            return adjusted_risk
        elif win_rate > 0.7:
            adjusted_risk = min(base_risk * 1.2, 0.05)  # Max 5% risk
            logger.info(f"Risk increased due to high win rate: {win_rate:.2f}")
            return adjusted_risk
        
        return base_risk
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: PositionSide,
        atr: float = None,
        custom_distance: float = None
    ) -> float:
        """
        Calculate stop loss price with multiple methods.
        """
        try:
            # Use custom distance, ATR-based, or default percentage
            if custom_distance:
                distance_pct = custom_distance
            elif atr:
                # Use 2x ATR as stop distance
                distance_pct = (2 * atr) / entry_price
            else:
                distance_pct = self.stop_loss_percent / 100
            
            # Ensure minimum stop distance
            min_stop_distance = 0.005  # 0.5%
            distance_pct = max(distance_pct, min_stop_distance)
            
            if side == PositionSide.LONG:
                stop_loss = entry_price * (1 - distance_pct)
            else:  # SHORT
                stop_loss = entry_price * (1 + distance_pct)
            
            logger.debug(f"Stop loss calculated: {stop_loss:.2f} ({distance_pct*100:.1f}% from entry)")
            
            return stop_loss
            
        except Exception as e:
            logger.error(f"Failed to calculate stop loss: {e}")
            return entry_price
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        side: PositionSide,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit based on risk-reward ratio.
        """
        try:
            if side == PositionSide.LONG:
                risk_distance = entry_price - stop_loss_price
                take_profit = entry_price + (risk_distance * risk_reward_ratio)
            else:  # SHORT
                risk_distance = stop_loss_price - entry_price
                take_profit = entry_price - (risk_distance * risk_reward_ratio)
            
            logger.debug(
                f"Take profit calculated: {take_profit:.2f} "
                f"(R:R {risk_reward_ratio}:1)"
            )
            
            return take_profit
            
        except Exception as e:
            logger.error(f"Failed to calculate take profit: {e}")
            return entry_price
    
    def record_trade(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        exit_price: float,
        size: float,
        entry_time: datetime,
        exit_reason: str = "unknown"
    ):
        """Record completed trade for performance tracking."""
        try:
            # Calculate P&L
            if side == PositionSide.LONG:
                pnl = (exit_price - entry_price) * size
            else:  # SHORT
                pnl = (entry_price - exit_price) * size
            
            pnl_percent = (pnl / (entry_price * size)) * 100
            hold_time = datetime.now() - entry_time
            
            trade_record = TradeRecord(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                size=size,
                pnl=pnl,
                pnl_percent=pnl_percent,
                timestamp=datetime.now(),
                hold_time=hold_time,
                exit_reason=exit_reason
            )
            
            self.trade_history.append(trade_record)
            self.daily_trades += 1
            self.daily_pnl += pnl
            
            # Update consecutive losses/wins
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            
            # Log trade
            logger.info(
                f"Trade recorded: {symbol} {side.value} "
                f"P&L: ${pnl:.2f} ({pnl_percent:.2f}%)"
            )
            
            # Check safety thresholds after trade
            self._check_safety_thresholds()
            
        except Exception as e:
            logger.error(f"Failed to record trade: {e}")
    
    def create_trade_signal(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        confidence: float,
        reason: str,
        atr: float = None,
        custom_stop_distance: float = None,
        risk_reward_ratio: float = 2.0
    ) -> TradeSignal:
        """Create a validated trade signal with risk parameters."""
        try:
            # Calculate stop loss
            stop_loss = self.calculate_stop_loss(
                entry_price, side, atr, custom_stop_distance
            )
            
            # Calculate take profit
            take_profit = self.calculate_take_profit(
                entry_price, stop_loss, side, risk_reward_ratio
            )
            
            # Calculate position size
            position_size, risk_amount, _ = self.calculate_position_size(
                self.account_balance, entry_price, stop_loss, side
            )
            
            signal = TradeSignal(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                reason=reason,
                risk_reward_ratio=risk_reward_ratio,
                timestamp=datetime.now(),
                risk_amount=risk_amount,
                position_size=position_size
            )
            
            logger.info(f"Trade signal created: {symbol} {side.value} @ {entry_price}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to create trade signal: {e}")
            raise
    
    def validate_signal(
        self,
        signal: TradeSignal,
        account_balance: float,
        open_positions: int
    ) -> Tuple[bool, str]:
        """
        Validate trade signal against all risk rules.
        """
        try:
            # Check if trading is allowed
            can_trade, reason = self.can_trade()
            if not can_trade:
                return False, reason
            
            # Check position limit
            if open_positions >= self.max_open_positions:
                return False, f"Maximum positions limit reached ({self.max_open_positions})"
            
            # Check minimum balance
            if account_balance <= self.min_account_balance:
                return False, f"Account balance below minimum: ${account_balance:.2f}"
            
            # Check confidence threshold
            if signal.confidence < 0.5:
                return False, f"Signal confidence too low: {signal.confidence:.2f}"
            
            # Check risk-reward ratio
            if signal.risk_reward_ratio < 1.0:
                return False, f"Poor risk-reward ratio: {signal.risk_reward_ratio:.2f}"
            
            # Validate prices
            if signal.side == PositionSide.LONG:
                if signal.stop_loss >= signal.entry_price:
                    return False, "Invalid stop loss for long position"
                if signal.take_profit and signal.take_profit <= signal.entry_price:
                    return False, "Invalid take profit for long position"
            else:  # SHORT
                if signal.stop_loss <= signal.entry_price:
                    return False, "Invalid stop loss for short position"
                if signal.take_profit and signal.take_profit >= signal.entry_price:
                    return False, "Invalid take profit for short position"
            
            # Check position size
            if signal.position_size <= 0:
                return False, "Invalid position size"
            
            return True, "Signal validated"
            
        except Exception as e:
            logger.error(f"Failed to validate signal: {e}")
            return False, f"Validation error: {str(e)}"
    
    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics."""
        if not self.trade_history:
            return {"total_trades": 0}
        
        total_pnl = sum(trade.pnl for trade in self.trade_history)
        winning_trades = [trade for trade in self.trade_history if trade.pnl > 0]
        losing_trades = [trade for trade in self.trade_history if trade.pnl < 0]
        
        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.trade_history) * 100,
            "total_pnl": total_pnl,
            "average_win": sum(trade.pnl for trade in winning_trades) / len(winning_trades) if winning_trades else 0,
            "average_loss": sum(trade.pnl for trade in losing_trades) / len(losing_trades) if losing_trades else 0,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "emergency_stop": self.emergency_stop
        }
    
    def reset_emergency_stop(self) -> bool:
        """Reset emergency stop if conditions are safe."""
        if not self.emergency_stop:
            return True
        
        # Check if conditions have improved
        self._check_safety_thresholds()
        
        if not self.emergency_stop:
            logger.info("Emergency stop reset - trading can resume")
            return True
        
        return False
    
    def create_trailing_stop(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        initial_stop: float,
        trail_distance: float = None
    ) -> TrailingStop:
        """
        Create trailing stop for a position.
        
        Args:
            symbol: Trading symbol
            side: Position side
            entry_price: Entry price
            initial_stop: Initial stop loss price
            trail_distance: Trailing distance (default from settings)
            
        Returns:
            TrailingStop object
        """
        trail_distance = trail_distance or self.trailing_stop_percent
        
        trailing_stop = TrailingStop(
            symbol=symbol,
            side=side,
            initial_stop=initial_stop,
            current_stop=initial_stop,
            trail_distance=trail_distance,
            highest_price=entry_price if side == PositionSide.LONG else 0,
            lowest_price=entry_price if side == PositionSide.SHORT else float('inf'),
            is_percentage=True,
            last_update=datetime.now()
        )
        
        self.active_trailing_stops[symbol] = trailing_stop
        
        logger.info(f"Created trailing stop for {symbol}: {initial_stop:.2f}")
        
        return trailing_stop
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[Tuple[bool, float]]:
        """
        Update trailing stop based on current price.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Tuple of (stop_updated, new_stop_price) or None if no update
        """
        if symbol not in self.active_trailing_stops:
            return None
        
        try:
            trail_stop = self.active_trailing_stops[symbol]
            updated = False
            new_stop = trail_stop.current_stop
            
            if trail_stop.side == PositionSide.LONG:
                # Update highest price seen
                if current_price > trail_stop.highest_price:
                    trail_stop.highest_price = current_price
                    
                    # Calculate new stop based on trail distance
                    if trail_stop.is_percentage:
                        new_stop = current_price * (1 - trail_stop.trail_distance)
                    else:
                        new_stop = current_price - trail_stop.trail_distance
                    
                    # Only update if new stop is higher (better for long)
                    if new_stop > trail_stop.current_stop:
                        trail_stop.current_stop = new_stop
                        trail_stop.last_update = datetime.now()
                        updated = True
                        
            else:  # SHORT position
                # Update lowest price seen
                if current_price < trail_stop.lowest_price:
                    trail_stop.lowest_price = current_price
                    
                    # Calculate new stop based on trail distance
                    if trail_stop.is_percentage:
                        new_stop = current_price * (1 + trail_stop.trail_distance)
                    else:
                        new_stop = current_price + trail_stop.trail_distance
                    
                    # Only update if new stop is lower (better for short)
                    if new_stop < trail_stop.current_stop:
                        trail_stop.current_stop = new_stop
                        trail_stop.last_update = datetime.now()
                        updated = True
            
            if updated:
                trading_logger.log_position_update(
                    symbol,
                    "trailing_stop_updated",
                    new_stop=new_stop,
                    current_price=current_price
                )
                
                logger.info(
                    f"Trailing stop updated for {symbol}: {new_stop:.2f} "
                    f"(price: {current_price:.2f})"
                )
            
            return (updated, new_stop) if updated else None
            
        except Exception as e:
            logger.error(f"Failed to update trailing stop for {symbol}: {e}")
            return None
    
    def remove_trailing_stop(self, symbol: str) -> None:
        """Remove trailing stop for symbol."""
        if symbol in self.active_trailing_stops:
            del self.active_trailing_stops[symbol]
            logger.info(f"Removed trailing stop for {symbol}")
    
    def get_position_risk(self, symbol: str) -> Optional[PositionRisk]:
        """Get position risk information."""
        return self.position_risks.get(symbol)
    
    def set_position_risk(self, position_risk: PositionRisk) -> None:
        """Set position risk information."""
        self.position_risks[position_risk.symbol] = position_risk
        
        logger.info(
            f"Position risk set for {position_risk.symbol}: "
            f"Size={position_risk.size}, Risk=${position_risk.risk_amount:.2f}"
        )
    
    def remove_position_risk(self, symbol: str) -> None:
        """Remove position risk tracking."""
        if symbol in self.position_risks:
            del self.position_risks[symbol]
            logger.info(f"Removed position risk tracking for {symbol}")
    
    def get_total_risk(self) -> float:
        """Calculate total risk across all positions."""
        return sum(risk.risk_amount for risk in self.position_risks.values())
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk management summary."""
        total_risk = self.get_total_risk()
        
        return {
            "total_risk_amount": total_risk,
            "max_risk_per_trade": self.max_risk_per_trade * 100,
            "active_positions": len(self.position_risks),
            "max_positions": self.max_open_positions,
            "trailing_stops_active": len(self.active_trailing_stops),
            "position_risks": {
                symbol: {
                    "size": risk.size,
                    "risk_amount": risk.risk_amount,
                    "notional_value": risk.notional_value
                }
                for symbol, risk in self.position_risks.items()
            }
        }


# Global risk manager instance
risk_manager = RiskManager() 