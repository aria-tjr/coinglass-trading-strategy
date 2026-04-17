"""
Exchange Gateway for Bybit integration via CCXT.

Handles trade execution, position management, and market data
for USDT perpetual futures trading on Bybit.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import ccxt
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import settings
from core.logger import get_logger, trading_logger

logger = get_logger("exchange")


class ExchangeError(Exception):
    """Custom exception for exchange-related errors."""
    pass


class Position:
    """Represents a trading position."""
    
    def __init__(self, data: Dict):
        """Initialize position from exchange data."""
        self.symbol = data.get('symbol', '')
        self.side = data.get('side', '')  # 'long' or 'short'
        self.size = float(data.get('size', 0))
        self.entry_price = float(data.get('entryPrice', 0))
        self.mark_price = float(data.get('markPrice', 0))
        self.unrealized_pnl = float(data.get('unrealizedPnl', 0))
        self.realized_pnl = float(data.get('realizedPnl', 0))
        self.timestamp = data.get('timestamp', datetime.now().timestamp())
        
    @property
    def value(self) -> float:
        """Get position notional value."""
        return self.size * self.mark_price
    
    @property
    def pnl_percent(self) -> float:
        """Get P&L as percentage of entry value."""
        if self.entry_price == 0:
            return 0.0
        entry_value = self.size * self.entry_price
        return (self.unrealized_pnl / entry_value) * 100 if entry_value else 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'value': self.value,
            'pnl_percent': self.pnl_percent,
            'timestamp': self.timestamp
        }


class BybitGateway:
    """
    Gateway for Bybit exchange operations.
    
    Provides async interface for trading, position management,
    and market data via CCXT.
    """
    
    def __init__(self):
        """Initialize the Bybit gateway."""
        self.exchange: Optional[ccxt.bybit] = None
        self.connected = False
        self.account_info: Dict = {}
        
        # Position cache
        self.positions: Dict[str, Position] = {}
        self.last_position_update = 0
        
        logger.info("Bybit gateway initialized")
    
    async def connect(self) -> None:
        """Initialize connection to Bybit exchange."""
        if self.connected:
            logger.warning("Already connected to Bybit")
            return
        
        try:
            # Initialize CCXT Bybit client
            self.exchange = ccxt.bybit({
                'apiKey': settings.bybit_api_key,
                'secret': settings.bybit_api_secret,
                'sandbox': settings.bybit_testnet,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'linear',  # USDT perpetual futures
                }
            })
            
            # Test connection and get account info
            await self._test_connection()
            
            # Set position mode to one-way (hedge mode off)
            await self._ensure_position_mode()
            
            self.connected = True
            logger.info(f"Connected to Bybit ({'testnet' if settings.bybit_testnet else 'mainnet'})")
            
        except Exception as e:
            logger.error(f"Failed to connect to Bybit: {e}")
            raise ExchangeError(f"Connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from exchange."""
        if self.exchange:
            try:
                # CCXT doesn't require explicit disconnection for REST
                pass
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
        
        self.connected = False
        self.exchange = None
        logger.info("Disconnected from Bybit")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def _make_request(self, method: str, *args, **kwargs) -> Any:
        """Make exchange request with retry logic."""
        if not self.connected or not self.exchange:
            raise ExchangeError("Not connected to exchange")
        
        try:
            # Run in thread pool to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(
                None, getattr(self.exchange, method), *args, **kwargs
            )
        except ccxt.NetworkError as e:
            logger.warning(f"Network error in {method}: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error in {method}: {e}")
            raise ExchangeError(f"Exchange error: {e}") from e
    
    async def _test_connection(self) -> None:
        """Test connection by fetching account balance."""
        try:
            balance = await self._make_request('fetch_balance')
            self.account_info = balance.get('info', {})
            logger.info("Connection test successful")
        except Exception as e:
            raise ExchangeError(f"Connection test failed: {e}") from e
    
    async def _ensure_position_mode(self) -> None:
        """Ensure account is in one-way position mode."""
        try:
            # Note: This is a simplified approach
            # In production, you might need to check current mode first
            logger.info("Position mode configuration handled by Bybit account settings")
        except Exception as e:
            logger.warning(f"Could not verify position mode: {e}")
    
    async def get_balance(self) -> Dict[str, float]:
        """
        Get account balance information.
        
        Returns:
            Dictionary with balance details
        """
        try:
            balance = await self._make_request('fetch_balance')
            
            return {
                'total': float(balance.get('total', {}).get('USDT', 0)),
                'free': float(balance.get('free', {}).get('USDT', 0)),
                'used': float(balance.get('used', {}).get('USDT', 0)),
                'timestamp': datetime.now().timestamp()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return {'total': 0, 'free': 0, 'used': 0, 'timestamp': 0}
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            leverage: Leverage value (1-100)
            
        Returns:
            True if successful
        """
        try:
            # CCXT may have a unified method or we need to use private API
            await self._make_request('set_leverage', leverage, symbol)
            
            logger.info(f"Set leverage to {leverage}x for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return False
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get current ticker data for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data or None if failed
        """
        try:
            ticker = await self._make_request('fetch_ticker', symbol)
            return {
                'symbol': ticker['symbol'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            return None
    
    async def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = '1h', 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get OHLCV candle data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            limit: Number of candles
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ohlcv = await self._make_request('fetch_ohlcv', symbol, timeframe, None, limit)
            
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            trading_logger.log_data_update(
                "bybit", 
                symbol,
                candles=len(df),
                timeframe=timeframe
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """
        Create market order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            reduce_only: Whether this is a reduce-only order
            
        Returns:
            Order info or None if failed
        """
        try:
            params = {}
            if reduce_only:
                params['reduceOnly'] = True
            
            order = await self._make_request(
                'create_market_order',
                symbol,
                side,
                amount,
                None,  # price (None for market orders)
                None,  # tag
                params
            )
            
            trading_logger.log_order(
                "create",
                symbol,
                side,
                amount,
                order_type="market",
                order_id=order.get('id')
            )
            
            return order
            
        except Exception as e:
            trading_logger.log_error("create_market_order", e, symbol=symbol, side=side, amount=amount)
            return None
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """
        Create limit order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Limit price
            reduce_only: Whether this is a reduce-only order
            
        Returns:
            Order info or None if failed
        """
        try:
            params = {}
            if reduce_only:
                params['reduceOnly'] = True
            
            order = await self._make_request(
                'create_limit_order',
                symbol,
                side,
                amount,
                price,
                None,  # tag
                params
            )
            
            trading_logger.log_order(
                "create",
                symbol,
                side,
                amount,
                price=price,
                order_type="limit",
                order_id=order.get('id')
            )
            
            return order
            
        except Exception as e:
            trading_logger.log_error("create_limit_order", e, symbol=symbol, side=side, amount=amount, price=price)
            return None
    
    async def create_stop_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        order_type: str = 'market'
    ) -> Optional[Dict]:
        """
        Create stop-loss order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            stop_price: Stop trigger price
            order_type: 'market' or 'limit'
            
        Returns:
            Order info or None if failed
        """
        try:
            params = {
                'stopPrice': stop_price,
                'type': f'stop_{order_type}',
                'reduceOnly': True
            }
            
            order = await self._make_request(
                'create_order',
                symbol,
                f'stop_{order_type}',
                side,
                amount,
                stop_price if order_type == 'limit' else None,
                None,
                params
            )
            
            trading_logger.log_order(
                "create_stop",
                symbol,
                side,
                amount,
                price=stop_price,
                order_type=f"stop_{order_type}",
                order_id=order.get('id')
            )
            
            return order
            
        except Exception as e:
            trading_logger.log_error("create_stop_order", e, symbol=symbol, side=side, stop_price=stop_price)
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            
        Returns:
            True if successful
        """
        try:
            await self._make_request('cancel_order', order_id, symbol)
            
            trading_logger.log_order(
                "cancel",
                symbol,
                "N/A",
                0,
                order_id=order_id
            )
            
            return True
            
        except Exception as e:
            trading_logger.log_error("cancel_order", e, order_id=order_id, symbol=symbol)
            return False
    
    async def get_positions(self, symbol: str = None) -> List[Position]:
        """
        Get current positions.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of Position objects
        """
        try:
            positions_data = await self._make_request('fetch_positions', symbol)
            
            positions = []
            for pos_data in positions_data:
                if float(pos_data.get('size', 0)) > 0:  # Only active positions
                    position = Position(pos_data)
                    positions.append(position)
                    self.positions[position.symbol] = position
            
            self.last_position_update = datetime.now().timestamp()
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []
    
    async def close_position(self, symbol: str) -> bool:
        """
        Close entire position for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if successful
        """
        try:
            positions = await self.get_positions(symbol)
            
            for position in positions:
                if position.size > 0:
                    # Determine close side (opposite of position side)
                    close_side = 'sell' if position.side == 'long' else 'buy'
                    
                    # Create market order to close
                    order = await self.create_market_order(
                        symbol,
                        close_side,
                        position.size,
                        reduce_only=True
                    )
                    
                    if order:
                        trading_logger.log_position_update(
                            symbol,
                            "closed",
                            size=position.size,
                            pnl=position.unrealized_pnl
                        )
                        return True
            
            return False
            
        except Exception as e:
            trading_logger.log_error("close_position", e, symbol=symbol)
            return False
    
    async def get_order_history(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get order history.
        
        Args:
            symbol: Trading symbol
            limit: Number of orders to fetch
            
        Returns:
            List of order data
        """
        try:
            orders = await self._make_request('fetch_orders', symbol, None, limit)
            return orders
        except Exception as e:
            logger.error(f"Failed to fetch order history: {e}")
            return []
    
    def calculate_position_size(
        self,
        symbol: str,
        side: str,
        risk_amount: float,
        stop_loss_price: float,
        current_price: float
    ) -> Tuple[float, float]:
        """
        Calculate position size based on risk amount and stop loss.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            risk_amount: Amount willing to risk (in USDT)
            stop_loss_price: Stop loss price
            current_price: Current market price
            
        Returns:
            Tuple of (position_size, notional_value)
        """
        try:
            # Calculate price difference (risk per unit)
            if side == 'buy':
                price_diff = abs(current_price - stop_loss_price)
            else:  # sell/short
                price_diff = abs(stop_loss_price - current_price)
            
            if price_diff == 0:
                return 0.0, 0.0
            
            # Position size = risk_amount / price_diff
            position_size = risk_amount / price_diff
            
            # Notional value
            notional_value = position_size * current_price
            
            logger.debug(f"Calculated position size: {position_size}, notional: {notional_value}")
            
            return position_size, notional_value
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0.0, 0.0
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Get current funding rate for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Funding rate or None if failed
        """
        try:
            funding = await self._make_request('fetch_funding_rate', symbol)
            return funding.get('fundingRate', 0.0)
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on exchange connection.
        
        Returns:
            Health status information
        """
        try:
            start_time = datetime.now()
            
            # Test basic connectivity
            balance = await self.get_balance()
            ticker = await self.get_ticker(settings.default_symbol)
            positions = await self.get_positions()
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                'connected': True,
                'response_time': response_time,
                'balance_available': balance['free'] > 0,
                'positions_count': len(positions),
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }


# Global gateway instance
bybit_gateway = BybitGateway() 