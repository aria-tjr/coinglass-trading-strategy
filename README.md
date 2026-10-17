# 🚀 Telegram CoinGlass Trader

An experimental, asynchronous Python 3.11 crypto trading bot designed for Bybit USDT perpetual futures. Combines CoinGlass market data with technical analysis for low-risk, high-stability trading with Telegram control interface.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 Key Features

- **Advanced Market Analysis**: Combines CoinGlass derivatives data (Open Interest, Funding Rates, Long/Short ratios) with technical indicators
- **Risk Management**: Strict position sizing, automated stop-loss, take-profit, and trailing stops
- **Async Architecture**: Built with uvloop for 2-4x performance improvement over standard asyncio
- **Telegram Control**: Complete bot management through Telegram with multi-language support
- **Production Ready**: Comprehensive logging, error handling, health checks, and Docker deployment

## 📊 Trading Strategy

The design goal (a target, **not** a measured result — see [Backtest status](#backtest-status)) is 20-30% annual compound returns with low risk by:

1. **Signal Generation**: Requiring confluence of multiple factors:
   - CoinGlass sentiment analysis (funding rates, OI changes, long/short ratios)
   - Technical indicators (RSI, EMA crossovers, MACD)
   - Volume and volatility confirmation

2. **Risk Management**: 
   - Maximum 2% risk per trade
   - Dynamic position sizing based on volatility
   - Automated stop-loss and take-profit levels
   - Trailing stops for profit maximization

3. **Market Focus**: Bybit USDT-margined perpetual futures with high liquidity

## 🏗️ Architecture

```
src/
├── core/                 # Core system components
│   ├── config.py        # Pydantic configuration management
│   ├── logger.py        # Loguru-based logging system
│   └── scheduler.py     # APScheduler task management
├── infra/               # Infrastructure layer
│   ├── coinglass_client.py  # CoinGlass API client
│   ├── exchange_gateway.py  # Bybit/CCXT integration
│   └── telegram_bot.py      # Aiogram v3 Telegram bot
├── strategy/            # Trading strategy implementation
│   ├── engine.py        # Main strategy engine
│   ├── indicators.py    # Technical analysis (pandas-ta)
│   └── risk_manager.py  # Risk management system
└── main.py             # Application entry point
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Bybit account with API access
- CoinGlass API key
- Telegram Bot Token

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aria-tjr/coinglass-trading-strategy.git
   cd coinglass-trading-strategy
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Set up environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

4. **Configure your settings** in `.env`:
   ```env
   # Required API credentials
   BYBIT_API_KEY=your_bybit_api_key
   BYBIT_SECRET=your_bybit_secret
   COINGLASS_API_KEY=your_coinglass_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   
   # Start with testnet and paper trading
   BYBIT_TESTNET=true
   STRATEGY_ENABLED=false
   ```

5. **Run the bot**:
   ```bash
   poetry run python src/main.py
   ```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Build and start all services**:
   ```bash
   docker-compose up -d
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f trader
   ```

3. **Stop services**:
   ```bash
   docker-compose down
   ```

### Docker Build Only

```bash
docker build -t telegram_coinglass_trader .
docker run -d --name trader --env-file .env telegram_coinglass_trader
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `BYBIT_API_KEY` | Bybit API key | Required |
| `BYBIT_SECRET` | Bybit API secret | Required |
| `BYBIT_TESTNET` | Use testnet (true/false) | true |
| `STRATEGY_ENABLED` | Enable live trading | false |
| `DEFAULT_SYMBOL` | Trading symbol | BTC/USDT:USDT |
| `LEVERAGE` | Trading leverage | 10 |
| `MAX_RISK_PERCENT` | Max risk per trade (%) | 2.0 |
| `COINGLASS_FUNDING_THRESHOLD` | Funding rate threshold | 0.01 |
| `RSI_OVERSOLD` | RSI oversold level | 30 |
| `RSI_OVERBOUGHT` | RSI overbought level | 70 |

### Trading Parameters

- **Risk Management**: Maximum 2% risk per trade, with dynamic sizing based on ATR
- **Signal Thresholds**: Configurable thresholds for all CoinGlass and technical indicators
- **Update Intervals**: Market data (30s), strategy evaluation (60s), position management (5min)

## 🤖 Telegram Commands

Once the bot is running, use these Telegram commands:

- `/start` - Initialize bot and show welcome message
- `/status` - Get current bot status and market data
- `/enable` - Enable trading strategy
- `/disable` - Disable trading strategy  
- `/positions` - Show current positions
- `/balance` - Show account balance
- `/help` - Show all available commands

## 📊 Monitoring & Alerts

The bot provides comprehensive monitoring through:

- **Real-time Logs**: Structured logging with rotation and retention
- **Telegram Alerts**: Signal notifications, order executions, errors
- **Health Checks**: Automated system health monitoring
- **Performance Metrics**: Trade statistics and success rates

### Alert Types

- 🎯 **Signal Alerts**: New trading opportunities
- 📈 **Order Execution**: Entry/exit confirmations  
- ⚠️ **Risk Alerts**: Stop-loss triggers, position updates
- 🚨 **System Alerts**: Errors, connection issues
- 📊 **Daily Summary**: Performance report

## 🧪 Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black src/
poetry run flake8 src/
```

### Type Checking

```bash
poetry run mypy src/
```

## 📈 Performance Optimization

- **uvloop**: 2-4x asyncio performance improvement
- **Connection Pooling**: Efficient HTTP/WebSocket connections
- **Caching**: Redis for data caching and session storage
- **Database**: PostgreSQL for historical data storage
- **Async Design**: Non-blocking I/O throughout the system

## 🔒 Security

- **API Key Management**: Environment-based configuration
- **Non-root Docker User**: Security best practices
- **Rate Limiting**: Built-in API rate limiting
- **Input Validation**: Pydantic model validation
- **Error Handling**: Comprehensive exception management

## ⚠️ Risk Disclaimer

**IMPORTANT**: This trading bot is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose.

- Start with testnet and paper trading
- Thoroughly test your configuration
- Monitor the bot continuously
- Understand the risks involved
- Use proper position sizing

## 🛠️ Troubleshooting

### Common Issues

1. **API Connection Errors**:
   - Verify API keys and permissions
   - Check network connectivity
   - Ensure testnet/mainnet consistency

2. **Telegram Bot Not Responding**:
   - Verify bot token and chat ID
   - Check Telegram bot permissions
   - Review logs for error messages

3. **Strategy Not Executing**:
   - Ensure `STRATEGY_ENABLED=true`
   - Check account balance
   - Verify market data reception

### Log Locations

- **Local**: `logs/` directory
- **Docker**: Container logs via `docker-compose logs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [CoinGlass](https://coinglass.com/) for derivatives market data
- [Bybit](https://bybit.com/) for trading infrastructure
- [CCXT](https://github.com/ccxt/ccxt) for exchange integration
- [pandas-ta](https://github.com/twopirllc/pandas-ta) for technical analysis


## Backtest status

There is **no backtest of the live strategy (`src/strategy/engine.py`) on real CoinGlass data** in this repo yet. What the existing scripts and reports actually test:

- `working_backtest.py` (source of the figures in `BACKTEST_VALIDATION_REPORT.md`) runs on the `GOOG` stock sample data bundled with the `backtesting` library, and its "CoinGlass sentiment" is **simulated** (a sine wave plus a momentum term). It says nothing about crypto or CoinGlass.
- `working_20_percent_strategy.py` (source of the "27.2% annual return on AVAX" in `OPTIMAL_20_PERCENT_STRATEGY.md`) is a separate SMA/RSI strategy on daily Yahoo Finance prices. It uses no CoinGlass data, and the best of four parameter sets was picked on the same 2-year window it reports (in-sample), so the figure is optimistic.
- `quick_backtest.py` generates random price data.
- The 20%+ figures in `PERFORMANCE_OPTIMIZATION_20PLUS.md` and `COMPREHENSIVE_NEXT_STEPS.md` are targets or extrapolations, not results.

## ⚠️ Disclaimer

This software is provided **for educational and research purposes only**. It is **not** financial advice. Trading cryptocurrencies carries substantial risk, including total loss of capital. Past backtest or live performance does **not** guarantee future results. Use testnet mode (`BYBIT_TESTNET=true`) for exploration, and only operate on mainnet with capital you can afford to lose. The author assumes no liability for losses arising from use of this software.
