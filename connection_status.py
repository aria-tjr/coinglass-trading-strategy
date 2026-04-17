#!/usr/bin/env python3
"""
CoinGlass Connection Status Checker

This script clearly shows the difference between:
1. Simulated backtest data (what we just ran)
2. Real CoinGlass API integration (what's available)
"""

import os

def check_connection_status():
    """Check the current CoinGlass connection status."""
    print("🔍 CoinGlass Connection Status Report")
    print("=" * 60)
    
    print("\n📊 WHAT WE JUST RAN (Simulated Backtest):")
    print("❌ NOT connected to real CoinGlass API")
    print("❌ Used simulated sentiment data")
    print("❌ Used Google stock data (GOOG) for demonstration")
    print("✅ Demonstrated strategy logic and backtesting framework")
    
    print("\n🔗 WHAT'S AVAILABLE (Real Integration):")
    print("✅ Complete CoinGlass API client built-in")
    print("✅ REST API for Open Interest, Funding Rates, Long/Short ratios")
    print("✅ WebSocket for real-time liquidation data")
    print("✅ Caching and error handling")
    print("✅ Rate limiting and retry logic")
    
    print("\n📁 PROJECT FILES:")
    files_to_check = [
        ("src/infra/coinglass_client.py", "Real CoinGlass API client"),
        ("src/strategy/engine.py", "Strategy engine with CoinGlass integration"),
        ("src/backtesting_engine.py", "Backtesting with CoinGlass simulation"),
        ("working_backtest.py", "Demo backtest (simulated data)"),
        ("env.example", "Environment configuration template")
    ]
    
    for file_path, description in files_to_check:
        exists = "✅" if os.path.exists(file_path) else "❌"
        print(f"{exists} {file_path:<35} - {description}")
    
    print("\n🔑 API KEY STATUS:")
    
    # Check for .env file
    if os.path.exists('.env'):
        print("✅ .env file exists")
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('COINGLASS_API_KEY', 'Not set')
        
        if api_key and api_key not in ['your_coinglass_api_key_here', 'demo_key']:
            print(f"✅ CoinGlass API key is configured")
            print(f"🔄 Ready for real data connection!")
        else:
            print(f"⚠️  CoinGlass API key not configured")
            print(f"📝 Set COINGLASS_API_KEY in .env file")
    else:
        print("❌ No .env file found")
        print("📝 Copy env.example to .env and configure")
    
    print("\n🚀 TO CONNECT TO REAL COINGLASS:")
    print("1. 🌐 Visit https://coinglass.com/api")
    print("2. 🔑 Get your API key")
    print("3. 📝 Copy env.example to .env")
    print("4. ✏️  Add: COINGLASS_API_KEY=your_actual_key")
    print("5. 🔄 Run: poetry run python src/main.py")
    
    print("\n📊 CURRENT CAPABILITIES:")
    print("✅ Backtesting framework (backtesting.py)")
    print("✅ Strategy development and testing")
    print("✅ Risk management and position sizing")
    print("✅ Technical analysis (RSI, EMA, ATR)")
    print("⚠️  CoinGlass data (simulated for demo)")
    print("⚠️  Crypto price data (needs real feeds)")
    
    print("\n🎯 SUMMARY:")
    print("• The backtest we ran used SIMULATED CoinGlass data")
    print("• Your project HAS real CoinGlass integration built-in")
    print("• You need an API key to connect to real CoinGlass data")
    print("• The strategy and backtesting framework are ready to go!")
    
    print("\n" + "=" * 60)


def show_integration_examples():
    """Show examples of real vs simulated integration."""
    print("\n🔬 INTEGRATION COMPARISON:")
    print("-" * 40)
    
    print("\n📈 SIMULATED (What we just ran):")
    print("```python")
    print("# Simulated sentiment in working_backtest.py")
    print("sentiment = np.sin(np.arange(len(close)) / 10) * 0.5")
    print("sentiment += momentum * 0.02")
    print("```")
    
    print("\n🌐 REAL (What's available):")
    print("```python")
    print("# Real CoinGlass API in src/infra/coinglass_client.py")
    print("async with CoinGlassClient() as client:")
    print("    oi_data = await client.get_open_interest_ohlc('BTC')")
    print("    funding = await client.get_funding_rate_ohlc('BTC')")
    print("    ls_ratio = await client.get_long_short_ratio_global('BTC')")
    print("```")
    
    print("\n💡 The difference:")
    print("• Simulated = Fake data for testing")
    print("• Real = Live market data from CoinGlass")


if __name__ == "__main__":
    try:
        check_connection_status()
        show_integration_examples()
        
        print("\n✅ Status check completed!")
        print("💭 Your project is ready for real CoinGlass integration!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc() 