"""
Telegram Bot Interface using Aiogram v3.

Provides user control and monitoring capabilities via Telegram chat.
Supports interactive commands for trading bot management.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import settings
from core.logger import get_logger, trading_logger

logger = get_logger("telegram")


class TradingTelegramBot:
    """
    Telegram bot for trading control and monitoring.
    
    Provides interactive interface for managing the trading bot
    with command handlers and callback functions.
    """
    
    def __init__(self):
        """Initialize the Telegram bot."""
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Bot state
        self.running = False
        
        # External callback handlers
        self.strategy_callbacks: Dict[str, Callable] = {}
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info("Telegram bot initialized")
    
    def _setup_handlers(self) -> None:
        """Setup message and callback handlers."""
        
        # Command handlers
        self.dp.message(Command("start", "help"))(self.cmd_help)
        self.dp.message(Command("status"))(self.cmd_status)
        self.dp.message(Command("enable"))(self.cmd_enable)
        self.dp.message(Command("disable"))(self.cmd_disable)
        self.dp.message(Command("positions"))(self.cmd_positions)
        self.dp.message(Command("balance"))(self.cmd_balance)
        
        # Callback query handlers
        self.dp.callback_query(F.data == "enable")(self.callback_enable)
        self.dp.callback_query(F.data == "disable")(self.callback_disable)
        self.dp.callback_query(F.data == "positions")(self.callback_positions)
        self.dp.callback_query(F.data == "balance")(self.callback_balance)
        self.dp.callback_query(F.data == "refresh")(self.callback_refresh)
        
        logger.info("Telegram handlers setup complete")
    
    def _check_authorization(self, user_id: int) -> bool:
        """Check if user is authorized."""
        if not settings.telegram_allowed_users:
            return True  # Allow all if no restrictions
        return user_id in settings.telegram_allowed_users
    
    def _create_main_keyboard(self) -> InlineKeyboardMarkup:
        """Create main inline keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="🟢 Enable", callback_data="enable"),
                InlineKeyboardButton(text="🔴 Disable", callback_data="disable")
            ],
            [
                InlineKeyboardButton(text="📊 Positions", callback_data="positions"),
                InlineKeyboardButton(text="💰 Balance", callback_data="balance")
            ],
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh")
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    async def cmd_help(self, message: Message) -> None:
        """Handle /start and /help commands."""
        if not self._check_authorization(message.from_user.id):
            await message.answer("❌ You are not authorized to use this bot.")
            return
        
        help_text = """🤖 *CoinGlass Trader Bot*

Welcome to your professional crypto trading assistant!

*Available Commands:*
/status - View bot status and positions
/enable - Enable trading signals
/disable - Disable trading signals
/positions - Show current positions
/balance - Show account balance
/help - Show this help message

*Quick Actions:* Use the buttons below for common tasks."""
        
        keyboard = self._create_main_keyboard()
        
        await message.answer(
            help_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def cmd_status(self, message: Message) -> None:
        """Handle /status command."""
        if not self._check_authorization(message.from_user.id):
            return
        
        try:
            # Get status from callbacks
            status_data = await self._get_bot_status()
            
            status_text = f"""📊 *Bot Status*

Strategy: {'🟢 Active' if status_data.get('strategy_enabled') else '🔴 Inactive'}
Balance: ${status_data.get('balance', 0):.2f} USDT
Open Positions: {status_data.get('positions_count', 0)}
Risk per Trade: {status_data.get('risk_percent', 0)}%
Leverage: {status_data.get('leverage', 1)}x

Last Update: {datetime.now().strftime("%H:%M:%S")}"""
            
            keyboard = self._create_main_keyboard()
            
            await message.answer(
                status_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")
    
    async def cmd_enable(self, message: Message) -> None:
        """Handle /enable command."""
        if not self._check_authorization(message.from_user.id):
            return
        
        try:
            if 'enable_strategy' in self.strategy_callbacks:
                await self.strategy_callbacks['enable_strategy']()
            
            await message.answer("✅ Trading strategy enabled")
            
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")
    
    async def cmd_disable(self, message: Message) -> None:
        """Handle /disable command."""
        if not self._check_authorization(message.from_user.id):
            return
        
        try:
            if 'disable_strategy' in self.strategy_callbacks:
                await self.strategy_callbacks['disable_strategy']()
            
            await message.answer("❌ Trading strategy disabled")
            
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")
    
    async def cmd_positions(self, message: Message) -> None:
        """Handle /positions command."""
        if not self._check_authorization(message.from_user.id):
            return
        
        try:
            if 'get_positions' in self.strategy_callbacks:
                positions = await self.strategy_callbacks['get_positions']()
                
                if not positions:
                    await message.answer("📋 No open positions")
                    return
                
                for position in positions:
                    position_text = f"""📈 *Position: {position.get('symbol', 'N/A')}*

Side: {position.get('side', 'N/A')}
Size: {position.get('size', 0)}
Entry Price: ${position.get('entry_price', 0):.2f}
Current Price: ${position.get('mark_price', 0):.2f}
P&L: ${position.get('unrealized_pnl', 0):.2f} ({position.get('pnl_percent', 0):.2f}%)
Value: ${position.get('value', 0):.2f}"""
                    
                    await message.answer(position_text, parse_mode='Markdown')
            else:
                await message.answer("📋 No open positions")
                
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")
    
    async def cmd_balance(self, message: Message) -> None:
        """Handle /balance command."""
        if not self._check_authorization(message.from_user.id):
            return
        
        try:
            if 'get_balance' in self.strategy_callbacks:
                balance = await self.strategy_callbacks['get_balance']()
                
                balance_text = f"""💰 *Account Balance*

Total: ${balance.get('total', 0):.2f} USDT
Available: ${balance.get('free', 0):.2f} USDT
Used: ${balance.get('used', 0):.2f} USDT"""
                
                await message.answer(balance_text, parse_mode='Markdown')
            
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")
    
    # Callback query handlers
    async def callback_enable(self, callback: CallbackQuery) -> None:
        """Handle enable callback."""
        await self.cmd_enable(callback.message)
        await callback.answer()
    
    async def callback_disable(self, callback: CallbackQuery) -> None:
        """Handle disable callback."""
        await self.cmd_disable(callback.message)
        await callback.answer()
    
    async def callback_positions(self, callback: CallbackQuery) -> None:
        """Handle positions callback."""
        await self.cmd_positions(callback.message)
        await callback.answer()
    
    async def callback_balance(self, callback: CallbackQuery) -> None:
        """Handle balance callback."""
        await self.cmd_balance(callback.message)
        await callback.answer()
    
    async def callback_refresh(self, callback: CallbackQuery) -> None:
        """Handle refresh callback."""
        # Simulate status command
        fake_message = type('obj', (object,), {
            'from_user': callback.from_user,
            'answer': callback.message.edit_text
        })
        
        await self.cmd_status(fake_message)
        await callback.answer()
    
    async def _get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status from callbacks."""
        status = {
            'strategy_enabled': False,
            'balance': 0,
            'positions_count': 0,
            'risk_percent': settings.max_risk_percent,
            'leverage': settings.bybit_leverage
        }
        
        try:
            if 'get_status' in self.strategy_callbacks:
                callback_status = await self.strategy_callbacks['get_status']()
                status.update(callback_status)
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
        
        return status
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callback for strategy events."""
        self.strategy_callbacks[event] = callback
        logger.info(f"Registered callback for {event}")
    
    async def send_alert(self, message: str, user_ids: List[int] = None) -> None:
        """Send alert message to users."""
        if not settings.enable_telegram_alerts:
            return
        
        target_users = user_ids or settings.telegram_allowed_users or []
        
        if not target_users:
            logger.warning("No target users for alert")
            return
        
        for user_id in target_users:
            try:
                await self.bot.send_message(user_id, message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to send alert to {user_id}: {e}")
    
    async def send_signal_alert(
        self,
        symbol: str,
        direction: str,
        reason: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_percent: float
    ) -> None:
        """Send trading signal alert."""
        alert_text = f"""🚨 *Trading Signal*

Symbol: {symbol}
Direction: {direction}
Reason: {reason}
Entry Price: ${entry_price:.2f}
Stop Loss: ${stop_loss:.2f}
Take Profit: ${take_profit:.2f}

Risk: {risk_percent}% of capital"""
        
        await self.send_alert(alert_text)
        
        trading_logger.log_signal(
            "telegram_alert",
            symbol,
            direction=direction,
            reason=reason
        )
    
    async def send_order_alert(
        self,
        action: str,
        side: str,
        symbol: str,
        size: float,
        price: float,
        order_id: str
    ) -> None:
        """Send order execution alert."""
        alert_text = f"""✅ *Order Executed*

{action} {side} {symbol}
Size: {size}
Price: ${price:.2f}
Order ID: {order_id}"""
        
        await self.send_alert(alert_text)
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        if self.running:
            logger.warning("Telegram bot already running")
            return
        
        try:
            # Start polling
            self.running = True
            logger.info("Starting Telegram bot polling...")
            
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            self.running = False
            raise
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if not self.running:
            return
        
        try:
            await self.dp.stop_polling()
            await self.bot.session.close()
            self.running = False
            logger.info("Telegram bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")


# Global bot instance
telegram_bot = TradingTelegramBot() 